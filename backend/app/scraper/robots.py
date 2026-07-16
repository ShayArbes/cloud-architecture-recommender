"""robots.txt compliance for the scraper (CLAUDE.md §2 — respect robots.txt)."""

import asyncio
import logging
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Checks URLs against each host's robots.txt, cached per host.

    An unreachable or missing robots.txt fails open (fetching is allowed) —
    the polite default for public documentation sites; an explicit Disallow
    is always honored.
    """

    def __init__(self, client: httpx.AsyncClient, user_agent: str) -> None:
        self._client = client
        self._user_agent = user_agent
        self._parsers: dict[str, RobotFileParser | None] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, url: str) -> bool:
        """Return whether ``url`` may be fetched under its host's robots.txt."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        # Lock so concurrent checks on a new host fetch robots.txt only once.
        async with self._lock:
            if origin not in self._parsers:
                self._parsers[origin] = await self._load(origin)
        parser = self._parsers[origin]
        return parser is None or parser.can_fetch(self._user_agent, url)

    async def _load(self, origin: str) -> RobotFileParser | None:
        """Fetch and parse ``origin``'s robots.txt; ``None`` means fail open."""
        robots_url = f"{origin}/robots.txt"
        try:
            response = await self._client.get(robots_url)
        except httpx.HTTPError as exc:
            logger.warning("Could not fetch %s (%s); failing open", robots_url, exc)
            return None
        if not response.is_success:
            logger.info("No robots.txt at %s (HTTP %d)", robots_url, response.status_code)
            return None
        parser = RobotFileParser(robots_url)
        parser.parse(response.text.splitlines())
        return parser
