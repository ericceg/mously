import asyncio

from aiohttp.test_utils import TestClient, TestServer

from mously.server import create_app


class FakeController:
    pass


def test_remote_page_is_never_cached():
    async def check():
        async with TestClient(TestServer(create_app(FakeController()))) as client:
            response = await client.get("/")
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert "tap to click" in await response.text()

    asyncio.run(check())
