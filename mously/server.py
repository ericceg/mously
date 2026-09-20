from __future__ import annotations

import argparse
import asyncio
import json
import socket
from importlib.resources import files

from aiohttp import WSMsgType, web

from .macos import MacController
from .protocol import ProtocolError, parse_command


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def create_app(controller: MacController) -> web.Application:
    app = web.Application(client_max_size=16_384)
    index = files("mously.static").joinpath("index.html")

    async def home(_: web.Request) -> web.Response:
        return web.Response(
            text=index.read_text(encoding="utf-8"),
            content_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    async def websocket(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=16_384)
        await ws.prepare(request)
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
                else:
                    dispatch(controller, command.action, command.payload)
            except (json.JSONDecodeError, ProtocolError, KeyError) as exc:
                await ws.send_json({"ok": False, "error": str(exc)})
        return ws

    app.router.add_get("/", home)
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
    elif action == "zoom":
        controller.zoom(payload["direction"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Use an iPhone as a local trackpad for this Mac")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    controller = MacController()
    trusted = controller.request_accessibility()
    address = f"http://{local_ip()}:{args.port}"
    print(f"\n  Mously is ready: {address}\n")
    if not trusted:
        print("  macOS permission needed: enable your terminal under")
        print("  System Settings → Privacy & Security → Accessibility, then restart Mously.\n")
    web.run_app(create_app(controller), host="0.0.0.0", port=args.port, print=None)


if __name__ == "__main__":
    main()
