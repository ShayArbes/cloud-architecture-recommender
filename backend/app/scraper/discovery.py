"""Discovery of AWS architecture page URLs via the public directory API (S1.1).

The Architecture Center listing page is client-rendered, so its HTML contains
no article links. The JSON directory API that powers that UI is public and
paginated; it yields each item's title and canonical page URL.
"""

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.core.constants import (
    AWS_DIRECTORY_API_URL,
    AWS_DIRECTORY_ID,
    AWS_DIRECTORY_LOCALE,
    AWS_DIRECTORY_PAGE_SIZE,
)
from app.core.errors import ScrapeError
from app.scraper.fetcher import get_with_retries

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveredArchitecture:
    """A candidate architecture page found in the directory listing."""

    title: str
    url: str


def _normalize_url(raw_url: str) -> str:
    """Strip tracking query params and fragments so URLs are stable identifiers.

    Idempotent scraping upserts by ``source_url`` (CLAUDE.md §5.1); AWS decorates
    listing links with ``?did=...&trk=...`` which would break deduplication.
    """
    parts = urlsplit(raw_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


class ArchitectureUrlDiscoverer:
    """Pages through the AWS directory API collecting architecture page URLs."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        page_size: int = AWS_DIRECTORY_PAGE_SIZE,
        api_url: str = AWS_DIRECTORY_API_URL,
    ) -> None:
        self._client = client
        self._page_size = page_size
        self._api_url = api_url

    async def discover(self, limit: int) -> list[DiscoveredArchitecture]:
        """Return up to ``limit`` unique architecture pages, newest first.

        Raises:
            ScrapeError: if the directory API is unreachable or returns
                an unparseable payload — without it there is nothing to scrape.
        """
        discovered: list[DiscoveredArchitecture] = []
        seen_urls: set[str] = set()
        page = 0
        while len(discovered) < limit:
            items = await self._fetch_page(page)
            if not items:
                break
            for item in items:
                candidate = self._extract(item)
                if candidate is None or candidate.url in seen_urls:
                    continue
                seen_urls.add(candidate.url)
                discovered.append(candidate)
                if len(discovered) >= limit:
                    break
            page += 1
        logger.info("Discovered %d architecture pages (limit %d)", len(discovered), limit)
        return discovered

    async def _fetch_page(self, page: int) -> list[dict[str, Any]]:
        """Fetch one page of directory items."""
        response = await get_with_retries(
            self._client,
            self._api_url,
            params={
                "item.directoryId": AWS_DIRECTORY_ID,
                "item.locale": AWS_DIRECTORY_LOCALE,
                "sort_by": "item.additionalFields.sortDate",
                "sort_order": "desc",
                "size": str(self._page_size),
                "page": str(page),
            },
        )
        try:
            payload = response.json()
            items = payload["items"]
        except (ValueError, KeyError) as exc:
            raise ScrapeError(
                "Unexpected directory API response shape",
                details={"api_url": self._api_url, "page": page},
            ) from exc
        if not isinstance(items, list):
            raise ScrapeError(
                "Directory API 'items' is not a list",
                details={"api_url": self._api_url, "page": page},
            )
        return items

    def _extract(self, item: dict[str, Any]) -> DiscoveredArchitecture | None:
        """Map one raw directory item to a candidate, or ``None`` if unusable."""
        fields = item.get("item", {}).get("additionalFields", {})
        if not isinstance(fields, dict):
            return None
        title = fields.get("headline") or fields.get("title")
        raw_url = fields.get("headlineUrl") or fields.get("primaryURL")
        if not isinstance(title, str) or not isinstance(raw_url, str):
            logger.debug("Skipping directory item without title/url: %r", item.get("item"))
            return None
        url = _normalize_url(raw_url)
        if not url.startswith("https://"):
            logger.debug("Skipping non-https directory link: %s", raw_url)
            return None
        return DiscoveredArchitecture(title=title.strip(), url=url)
