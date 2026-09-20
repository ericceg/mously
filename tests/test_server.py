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
            page = await response.text()
            assert "Touch to position pointer" in page
            assert 'data-key="left" aria-label="Skip back 5 seconds"' in page
            assert 'data-key="right" aria-label="Skip forward 5 seconds"' in page

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
