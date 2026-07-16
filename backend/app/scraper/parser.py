"""Parser abstraction — strategy pattern for architecture extraction (CLAUDE.md §3.2).

Any implementation (rule-based, LLM-backed) must be swappable without callers
knowing which one they hold (Liskov). New sources or strategies mean a new
class, never edits to existing parsers (Open/Closed).
"""

from typing import Protocol

from app.models.architecture import ParsedArchitecture


class ArchitectureParser(Protocol):
    """Extracts a structured architecture from one scraped page."""

    parser_version: str

    def parse(self, raw_html: str, source_url: str) -> ParsedArchitecture:
        """Parse ``raw_html`` fetched from ``source_url``.

        Raises:
            ScrapeError: if the page cannot yield a usable architecture.
        """
        ...
