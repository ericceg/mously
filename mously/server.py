from __future__ import annotations

import argparse
import errno
import hmac
import json
import os
import secrets
import socket
import sys
from importlib.resources import files
from pathlib import Path

from aiohttp import WSCloseCode, WSMsgType, web

from .macos import MacController
from .protocol import ProtocolError, parse_command

CONTROL_PROTOCOL = "mously"
TOKEN_PROTOCOL_PREFIX = "mously-token."
PAIRING_TOKEN_PATH = Path.home() / "Library" / "Application Support" / "Mously" / "pairing-token"


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def load_or_create_pairing_token(
    path: Path = PAIRING_TOKEN_PATH, *, reset: bool = False
) -> str:
    if not reset:
        try:
            token = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            pass
        else:
            if token:
                path.chmod(0o600)
                return token

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = secrets.token_urlsafe(24)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as token_file:
            descriptor = -1
            token_file.write(token)
    finally:
        if descriptor != -1:
            os.close(descriptor)
    return token


def _has_pairing_token(request: web.Request, pairing_token: str) -> bool:
    offered_protocols = request.headers.get("Sec-WebSocket-Protocol", "")
    expected = f"{TOKEN_PROTOCOL_PREFIX}{pairing_token}"
    return any(
        hmac.compare_digest(protocol.strip(), expected)
        for protocol in offered_protocols.split(",")
    )


def create_app(controller: MacController, pairing_token: str) -> web.Application:
    app = web.Application(client_max_size=16_384)
    index = files("mously.static").joinpath("index.html")
    touch_icon = files("mously.static").joinpath("mously-touch-icon.png")

    async def home(_: web.Request) -> web.Response:
        return web.Response(
            text=index.read_text(encoding="utf-8"),
            content_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    async def apple_touch_icon(_: web.Request) -> web.Response:
        return web.Response(
            body=touch_icon.read_bytes(),
            content_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    async def websocket(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(
            protocols=(CONTROL_PROTOCOL,), heartbeat=20, max_msg_size=16_384
        )
        await ws.prepare(request)
        if not _has_pairing_token(request, pairing_token):
            await ws.close(code=WSCloseCode.POLICY_VIOLATION, message=b"Pairing required")
            return ws
        async for message in ws:
            if message.type != WSMsgType.TEXT:
                continue
            try:
                command = parse_command(json.loads(message.data))
                if command.action == "list_apps":
                    await ws.send_json({"type": "apps", "apps": controller.applications()})
                elif command.action == "activate_app":
                    activated = controller.activate_application(command.payload["pid"])
                    await ws.send_json({"type": "activated", "ok": activated})
                elif command.action == "list_displays":
                    await ws.send_json({"type": "displays", "displays": controller.displays()})
                elif command.action == "select_display":
                    selected = controller.select_display(command.payload["display_id"])
                    await ws.send_json({"type": "display_selected", "ok": selected, "displays": controller.displays()})
                elif command.action == "get_volume":
                    await ws.send_json({"type": "volume", "value": controller.volume()})
                else:
                    dispatch(controller, command.action, command.payload)
            except (json.JSONDecodeError, ProtocolError, KeyError) as exc:
                await ws.send_json({"ok": False, "error": str(exc)})
        return ws

    app.router.add_get("/", home)
    app.router.add_get("/mously-touch-icon.png", apple_touch_icon)
    app.router.add_get("/ws", websocket)
    return app


def dispatch(controller: MacController, action: str, payload: dict) -> None:
    if action == "move":
        controller.move(payload["dx"], payload["dy"])
    elif action == "point":
        controller.point(payload["x"], payload["y"])
    elif action == "scroll":
        controller.scroll(payload["dx"], payload["dy"])
    elif action == "click":
        controller.click(payload["button"], payload["count"])
    elif action == "key":
        controller.key(payload["key"])
    elif action == "text":
        controller.text(payload["text"])
    elif action == "media":
        controller.media(payload["key"])
    elif action == "set_volume":
        controller.set_volume(payload["value"])
    elif action == "magnify":
        controller.magnify(payload["delta"], payload["phase"])


def _port_in_use_message(port: int) -> str:
    return (
        f"\nMously could not start because port {port} is already in use.\n"
        "Another Mously instance may already be running. Press Ctrl+C in its "
        "terminal to stop it.\n\n"
        "To find the process using the port:\n"
        f"  lsof -nP -iTCP:{port} -sTCP:LISTEN\n\n"
        "To stop that process:\n"
        f"  kill $(lsof -tiTCP:{port} -sTCP:LISTEN)\n\n"
        "Or start Mously on a different port:\n"
        f"  mously --port {port + 1}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Use an iPhone as a local trackpad for this Mac")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--reset-pairing",
        action="store_true",
        help="create a new pairing token and invalidate the previous paired address",
    )
    args = parser.parse_args()

    controller = MacController()
    trusted = controller.request_accessibility()
    pairing_token = load_or_create_pairing_token(reset=args.reset_pairing)
    address = f"http://{local_ip()}:{args.port}/#token={pairing_token}"

    def print_ready(*_: object) -> None:
        print(f"\n  Mously is ready: {address}\n")
        if not trusted:
            print("  macOS permission needed: enable your terminal under")
            print("  System Settings → Privacy & Security → Accessibility, then restart Mously.\n")

    try:
        web.run_app(
            create_app(controller, pairing_token),
            host="0.0.0.0",
            port=args.port,
            print=print_ready,
        )
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        print(_port_in_use_message(args.port), file=sys.stderr, end="")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
