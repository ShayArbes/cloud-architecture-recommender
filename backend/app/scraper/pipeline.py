"""Scrape pipeline: discover → fetch → parse (CLAUDE.md §3.1, §3.5).

The ``ScrapePipeline`` protocol lets ``ScrapeService`` stay unit-testable with
an in-memory fake. The concrete implementation owns the network stack: it
opens one polite HTTP client per run, respects robots.txt, and turns per-page
failures into recorded errors rather than aborting the whole run.
"""

import logging
from dataclasses import dataclass, field
from typing import Protocol

from app.core.config import Settings
from app.core.errors import ScrapeError
from app.models.architecture import ParsedArchitecture
from app.models.scrape_job import ScrapeJobError
from app.scraper.discovery import ArchitectureUrlDiscoverer
from app.scraper.factory import create_parser
from app.scraper.fetcher import PageFetcher, create_http_client
from app.scraper.parser import ArchitectureParser
from app.scraper.robots import RobotsChecker

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Outcome of one pipeline run: parsed architectures plus recorded failures."""

    parsed: list[ParsedArchitecture] = field(default_factory=list)
    errors: list[ScrapeJobError] = field(default_factory=list)
    pages_found: int = 0


class ScrapePipeline(Protocol):
    """Discovers, fetches, and parses architectures up to ``limit`` pages."""

    async def run(self, limit: int) -> PipelineResult:
        """Run discovery→fetch→parse.

        Raises:
            ScrapeError: only on a fatal failure (e.g. discovery unreachable);
                per-page failures are collected into the result, not raised.
        """
        ...


class HttpScrapePipeline:
    """Concrete pipeline over httpx + the configured parser."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run(self, limit: int) -> PipelineResult:
        """Discover up to ``limit`` allowed pages, fetch, and parse them."""
        settings = self._settings
        parser: ArchitectureParser = create_parser(settings)
        result = PipelineResult()
        async with create_http_client(
            settings.scraper_user_agent, settings.scraper_timeout_seconds
        ) as client:
            discovered = await ArchitectureUrlDiscoverer(client).discover(limit)
            robots = RobotsChecker(client, settings.scraper_user_agent)
            allowed = [item.url for item in discovered if await robots.is_allowed(item.url)]
            result.pages_found = len(allowed)

            fetcher = PageFetcher(client, max_concurrency=settings.scraper_max_concurrency)
            report = await fetcher.fetch_many(allowed)
            result.errors.extend(
                ScrapeJobError(url=failure.url, reason=failure.reason)
                for failure in report.failures
            )
            for page in report.pages:
                try:
                    result.parsed.append(await parser.parse(page.html, page.url))
                except ScrapeError as exc:
                    logger.warning("Parse failed for %s: %s", page.url, exc.message)
                    result.errors.append(ScrapeJobError(url=page.url, reason=exc.message))
        return result
