import asyncio
import errno
import stat

import pytest
from aiohttp import WSCloseCode, WSMsgType
from aiohttp.test_utils import TestClient, TestServer

from mously import server
from mously.server import create_app, dispatch, load_or_create_pairing_token

PAIRING_TOKEN = "test-pairing-token"


class FakeController:
    pass


def test_pairing_token_is_reused_across_restarts(tmp_path):
    token_path = tmp_path / "Mously" / "pairing-token"

    first_token = load_or_create_pairing_token(token_path)
    second_token = load_or_create_pairing_token(token_path)

    assert second_token == first_token
    assert token_path.read_text(encoding="utf-8") == first_token
    assert stat.S_IMODE(token_path.stat().st_mode) == 0o600


def test_pairing_token_can_be_reset(tmp_path):
    token_path = tmp_path / "Mously" / "pairing-token"
    original_token = load_or_create_pairing_token(token_path)

    replacement_token = load_or_create_pairing_token(token_path, reset=True)

    assert replacement_token != original_token
    assert load_or_create_pairing_token(token_path) == replacement_token


def test_main_explains_how_to_resolve_an_occupied_port(monkeypatch, capsys):
    class FakeMacController:
        @staticmethod
        def request_accessibility():
            return True

    def port_is_occupied(*args, **kwargs):
        raise OSError(errno.EADDRINUSE, "Address already in use")

    monkeypatch.setattr(server, "MacController", FakeMacController)
    monkeypatch.setattr(
        server, "load_or_create_pairing_token", lambda **kwargs: PAIRING_TOKEN
    )
    monkeypatch.setattr(server.web, "run_app", port_is_occupied)
    monkeypatch.setattr(server.sys, "argv", ["mously"])

    with pytest.raises(SystemExit) as exc_info:
        server.main()

    assert exc_info.value.code == 1
    error = capsys.readouterr().err
    assert "port 8765 is already in use" in error
    assert "Press Ctrl+C" in error
    assert "lsof -nP -iTCP:8765 -sTCP:LISTEN" in error
    assert "kill $(lsof -tiTCP:8765 -sTCP:LISTEN)" in error
    assert "mously --port 8766" in error


def test_main_does_not_hide_other_startup_errors(monkeypatch):
    class FakeMacController:
        @staticmethod
        def request_accessibility():
            return True

    def fail_to_start(*args, **kwargs):
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(server, "MacController", FakeMacController)
    monkeypatch.setattr(
        server, "load_or_create_pairing_token", lambda **kwargs: PAIRING_TOKEN
    )
    monkeypatch.setattr(server.web, "run_app", fail_to_start)
    monkeypatch.setattr(server.sys, "argv", ["mously"])

    with pytest.raises(OSError, match="Permission denied"):
        server.main()


def test_remote_page_is_never_cached():
    async def check():
        async with TestClient(TestServer(create_app(FakeController(), PAIRING_TOKEN))) as client:
            response = await client.get("/")
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            page = await response.text()
            assert "Touch to position pointer" in page
            assert 'id="zoomHold"' in page
            assert 'id="zoomSwipe"' in page
            assert "send('magnify', {phase: 'began', delta: 0})" in page
            assert "function startZoomSwipeMomentum()" in page
            assert "requestAnimationFrame(continueZoomSwipeMomentum)" in page
            assert "stopZoomSwipeMomentum();" in page
            assert 'data-key="left" aria-label="Skip back 5 seconds"' in page
            assert 'data-key="right" aria-label="Skip forward 5 seconds"' in page
            assert "mously-token.${pairingToken}" in page
            assert "localStorage.setItem(pairingTokenKey, fragmentToken)" in page
            assert "sessionStorage" not in page
            assert "history.replaceState" not in page
            assert "=== 'absolute' ? 'absolute' : 'relative'" in page
            assert 'id="settingsDialog"' in page
            assert 'data-theme-choice="default"' in page
            assert 'data-theme-choice="light"' in page
            assert 'data-theme-choice="oled"' in page
            assert "--page: #000000" in page
            assert "localStorage.setItem('mouslyAppearance', appearance)" in page
            assert 'id="modeChoices"' in page
            assert 'id="pinchZoom"' in page
            assert 'rel="apple-touch-icon"' in page
            assert 'href="/mously-touch-icon.png"' in page

    asyncio.run(check())


def test_apple_touch_icon_is_served():
    async def check():
        async with TestClient(
            TestServer(create_app(FakeController(), PAIRING_TOKEN))
        ) as client:
            response = await client.get("/mously-touch-icon.png")
            assert response.status == 200
            assert response.content_type == "image/png"
            assert response.headers["Cache-Control"] == "no-store"
            assert (await response.read()).startswith(b"\x89PNG\r\n\x1a\n")

    asyncio.run(check())


def test_websocket_rejects_a_client_without_the_pairing_token():
    async def check():
        async with TestClient(
            TestServer(create_app(FakeController(), PAIRING_TOKEN))
        ) as client:
            websocket = await client.ws_connect("/ws", protocols=("mously",))
            message = await websocket.receive()
            assert message.type is WSMsgType.CLOSE
            assert websocket.close_code == WSCloseCode.POLICY_VIOLATION

    asyncio.run(check())


def test_websocket_accepts_a_client_with_the_pairing_token():
    class AppController:
        @staticmethod
        def applications():
            return []

    async def check():
        async with TestClient(
            TestServer(create_app(AppController(), PAIRING_TOKEN))
        ) as client:
            websocket = await client.ws_connect(
                "/ws", protocols=("mously", f"mously-token.{PAIRING_TOKEN}")
            )
            await websocket.send_json({"action": "list_apps"})
            message = await websocket.receive()
            assert message.type is WSMsgType.TEXT
            assert message.json() == {"type": "apps", "apps": []}

    asyncio.run(check())


def test_magnify_is_dispatched_to_controller():
    class RecordingController:
        def __init__(self):
            self.events = []

        def magnify(self, delta, phase):
            self.events.append((delta, phase))

    controller = RecordingController()
    dispatch(controller, "magnify", {"delta": 0.08, "phase": "changed"})

    assert controller.events == [(0.08, "changed")]


def test_volume_is_dispatched_to_controller():
    class RecordingController:
        def __init__(self):
            self.values = []

        def set_volume(self, value):
            self.values.append(value)

    controller = RecordingController()
    dispatch(controller, "set_volume", {"value": 0.72})

    assert controller.values == [0.72]
