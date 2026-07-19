"""Parser abstraction — strategy pattern for architecture extraction (CLAUDE.md §3.2).

Any implementation (rule-based, LLM-backed) must be swappable without callers
knowing which one they hold (Liskov). New sources or strategies mean a new
class, never edits to existing parsers (Open/Closed).
"""

from dataclasses import dataclass
from typing import Protocol

from app.models.architecture import ParsedArchitecture


@dataclass(frozen=True)
class SourceHints:
    """Authoritative metadata supplied by discovery, preferred over page scraping.

    AWS article pages are client-rendered, so their fetched HTML often exposes
    only generic site chrome (a shared ``<title>``, the global service nav). The
    directory API, by contrast, gives each item its real headline and summary —
    passing them here lets the parser use them instead of mis-extracting from the
    page. Any field left ``None`` falls back to HTML extraction.
    """

    title: str | None = None
    description: str | None = None


class ArchitectureParser(Protocol):
    """Extracts a structured architecture from one scraped page.

    ``parse`` is async because implementations may call external services
    (the Claude API); pure-rules implementations simply never await.
    """

    parser_version: str

    async def parse(
        self, raw_html: str, source_url: str, *, hints: SourceHints | None = None
    ) -> ParsedArchitecture:
        """Parse ``raw_html`` fetched from ``source_url``.

        ``hints`` carries authoritative metadata from discovery; when a field is
        provided it is preferred over extracting that field from the HTML.

        Raises:
            ScrapeError: if the page cannot yield a usable architecture.
        """
        ...
