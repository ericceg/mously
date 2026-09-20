import asyncio

from aiohttp.test_utils import TestClient, TestServer

from mously.server import create_app, dispatch


class FakeController:
    pass


def test_remote_page_is_never_cached():
    async def check():
        async with TestClient(TestServer(create_app(FakeController()))) as client:
            response = await client.get("/")
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert "Touch to position pointer" in await response.text()

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
