"""Tests for the async page fetcher (S1.1) — no network, MockTransport only."""

import asyncio

import httpx
import pytest

from app.core.errors import ScrapeError
from app.scraper.fetcher import FetchedPage, FetchFailure, PageFetcher, get_with_retries


def make_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Disable real backoff sleeps and record the requested delays."""
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.scraper.fetcher.asyncio.sleep", record_sleep)
    return delays


async def test_fetch_page_returns_html(no_sleep: list[float]) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text="<html>ok</html>"))
    async with make_client(transport) as client:
        page = await PageFetcher(client, max_concurrency=2).fetch_page("https://example.com/a")

    assert page == FetchedPage(url="https://example.com/a", html="<html>ok</html>")
    assert no_sleep == []


async def test_retries_transient_errors_with_exponential_backoff(no_sleep: list[float]) -> None:
    attempts = 0

    def flaky(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503) if attempts < 3 else httpx.Response(200, text="recovered")

    async with make_client(httpx.MockTransport(flaky)) as client:
        page = await PageFetcher(client, max_concurrency=1).fetch_page("https://example.com/flaky")

    assert page.html == "recovered"
    assert attempts == 3
    assert no_sleep == [1.0, 2.0]  # base * 2^(attempt-1)


async def test_non_retryable_status_fails_fast(no_sleep: list[float]) -> None:
    attempts = 0

    def not_found(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404)

    async with make_client(httpx.MockTransport(not_found)) as client:
        with pytest.raises(ScrapeError) as exc_info:
            await PageFetcher(client, max_concurrency=1).fetch_page("https://example.com/missing")

    assert attempts == 1
    assert no_sleep == []
    assert exc_info.value.details["status_code"] == 404


async def test_network_errors_exhaust_retries(no_sleep: list[float]) -> None:
    attempts = 0

    def broken(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("connection refused")

    async with make_client(httpx.MockTransport(broken)) as client:
        with pytest.raises(ScrapeError) as exc_info:
            await get_with_retries(client, "https://example.com/down")

    assert attempts == 3
    assert len(no_sleep) == 2
    assert exc_info.value.details["attempts"] == 3


async def test_fetch_many_records_failures_without_aborting(no_sleep: list[float]) -> None:
    def mixed(request: httpx.Request) -> httpx.Response:
        if "bad" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(200, text=f"page:{request.url.path}")

    urls = ["https://example.com/ok1", "https://example.com/bad", "https://example.com/ok2"]
    async with make_client(httpx.MockTransport(mixed)) as client:
        report = await PageFetcher(client, max_concurrency=2).fetch_many(urls)

    assert [page.url for page in report.pages] == [
        "https://example.com/ok1",
        "https://example.com/ok2",
    ]
    assert report.failures == [
        FetchFailure(url="https://example.com/bad", reason=report.failures[0].reason)
    ]
    assert "404" in report.failures[0].reason


async def test_fetch_many_respects_concurrency_bound() -> None:
    active = 0
    peak = 0

    async def slow(request: httpx.Request) -> httpx.Response:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, text="ok")

    urls = [f"https://example.com/{i}" for i in range(6)]
    async with make_client(httpx.MockTransport(slow)) as client:
        report = await PageFetcher(client, max_concurrency=2).fetch_many(urls)

    assert len(report.pages) == 6
    assert peak <= 2
