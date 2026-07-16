"""Tests for robots.txt compliance (S1.1)."""

import httpx

from app.scraper.robots import RobotsChecker

USER_AGENT = "CloudArchRecommenderBot/0.1"

ROBOTS_TXT = """\
User-agent: *
Disallow: /private/
Allow: /
"""


def make_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


async def test_disallowed_path_is_blocked_and_allowed_path_passes() -> None:
    def serve(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_TXT)
        return httpx.Response(200, text="page")

    async with make_client(httpx.MockTransport(serve)) as client:
        checker = RobotsChecker(client, USER_AGENT)
        assert await checker.is_allowed("https://example.com/public/page") is True
        assert await checker.is_allowed("https://example.com/private/secret") is False


async def test_missing_robots_fails_open() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    async with make_client(transport) as client:
        checker = RobotsChecker(client, USER_AGENT)
        assert await checker.is_allowed("https://example.com/anything") is True


async def test_unreachable_robots_fails_open() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    async with make_client(httpx.MockTransport(broken)) as client:
        checker = RobotsChecker(client, USER_AGENT)
        assert await checker.is_allowed("https://example.com/anything") is True


async def test_robots_is_fetched_once_per_host() -> None:
    robots_fetches = 0

    def serve(request: httpx.Request) -> httpx.Response:
        nonlocal robots_fetches
        if request.url.path == "/robots.txt":
            robots_fetches += 1
            return httpx.Response(200, text=ROBOTS_TXT)
        return httpx.Response(200, text="page")

    async with make_client(httpx.MockTransport(serve)) as client:
        checker = RobotsChecker(client, USER_AGENT)
        await checker.is_allowed("https://example.com/one")
        await checker.is_allowed("https://example.com/two")
        await checker.is_allowed("https://example.com/three")

    assert robots_fetches == 1
