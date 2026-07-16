"""Async page fetching with timeouts, retry/backoff, and bounded concurrency (S1.1).

One failed page never aborts a batch (CLAUDE.md §3.5): ``fetch_many`` records
per-URL failures in its report and continues.
"""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from app.core.constants import (
    RETRYABLE_STATUS_CODES,
    SCRAPER_BACKOFF_BASE_SECONDS,
    SCRAPER_MAX_RETRIES,
)
from app.core.errors import ScrapeError

logger = logging.getLogger(__name__)


def create_http_client(user_agent: str, timeout_seconds: float) -> httpx.AsyncClient:
    """Build the shared scraper HTTP client with timeout and identity headers."""
    return httpx.AsyncClient(
        headers={"User-Agent": user_agent},
        timeout=timeout_seconds,
        follow_redirects=True,
    )


async def get_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, str] | None = None,
    max_retries: int = SCRAPER_MAX_RETRIES,
    backoff_base_seconds: float = SCRAPER_BACKOFF_BASE_SECONDS,
) -> httpx.Response:
    """GET ``url``, retrying transient failures with exponential backoff.

    Raises:
        ScrapeError: on a non-retryable HTTP status, or once retries are exhausted.
    """
    last_reason = "no attempts made"
    for attempt in range(1, max_retries + 1):
        try:
            response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            last_reason = f"{type(exc).__name__}: {exc}"
        else:
            if response.is_success:
                return response
            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise ScrapeError(
                    f"Non-retryable HTTP {response.status_code} for {url}",
                    details={"url": url, "status_code": response.status_code},
                )
            last_reason = f"HTTP {response.status_code}"

        if attempt < max_retries:
            delay = backoff_base_seconds * 2 ** (attempt - 1)
            logger.warning(
                "Fetch attempt %d/%d for %s failed (%s); retrying in %.1fs",
                attempt,
                max_retries,
                url,
                last_reason,
                delay,
            )
            await asyncio.sleep(delay)

    raise ScrapeError(
        f"{last_reason} after {max_retries} attempts for {url}",
        details={"url": url, "attempts": max_retries},
    )


@dataclass(frozen=True)
class FetchedPage:
    """A successfully downloaded page."""

    url: str
    html: str


@dataclass(frozen=True)
class FetchFailure:
    """A page that could not be fetched; recorded, never fatal."""

    url: str
    reason: str


@dataclass(frozen=True)
class FetchReport:
    """Outcome of a multi-page fetch: successes plus recorded failures."""

    pages: list[FetchedPage]
    failures: list[FetchFailure]


class PageFetcher:
    """Downloads pages politely: bounded concurrency, retries, recorded failures."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        max_concurrency: int,
        max_retries: int = SCRAPER_MAX_RETRIES,
        backoff_base_seconds: float = SCRAPER_BACKOFF_BASE_SECONDS,
    ) -> None:
        self._client = client
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_retries = max_retries
        self._backoff_base_seconds = backoff_base_seconds

    async def fetch_page(self, url: str) -> FetchedPage:
        """Fetch a single page, raising ``ScrapeError`` if it ultimately fails."""
        response = await get_with_retries(
            self._client,
            url,
            max_retries=self._max_retries,
            backoff_base_seconds=self._backoff_base_seconds,
        )
        return FetchedPage(url=url, html=response.text)

    async def fetch_many(self, urls: Sequence[str]) -> FetchReport:
        """Fetch all ``urls`` concurrently; failures are collected, not raised."""

        async def fetch_bounded(url: str) -> FetchedPage | FetchFailure:
            async with self._semaphore:
                try:
                    return await self.fetch_page(url)
                except ScrapeError as exc:
                    logger.warning("Giving up on %s: %s", url, exc.message)
                    return FetchFailure(url=url, reason=exc.message)

        results = await asyncio.gather(*(fetch_bounded(url) for url in urls))
        pages = [result for result in results if isinstance(result, FetchedPage)]
        failures = [result for result in results if isinstance(result, FetchFailure)]
        return FetchReport(pages=pages, failures=failures)
