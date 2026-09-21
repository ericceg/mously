import asyncio

from aiohttp import WSCloseCode, WSMsgType
from aiohttp.test_utils import TestClient, TestServer

from mously.server import create_app, dispatch

PAIRING_TOKEN = "test-pairing-token"


class FakeController:
    pass


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
            assert 'data-key="left" aria-label="Skip back 5 seconds"' in page
            assert 'data-key="right" aria-label="Skip forward 5 seconds"' in page
            assert "mously-token.${pairingToken}" in page

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
