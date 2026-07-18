"""Role-specific repository protocols (CLAUDE.md §3.2 — I/D).

Services depend on these protocols, never on Motor or concrete Mongo classes,
so business logic stays unit-testable with in-memory fakes.
"""

from typing import Protocol

from app.models.architecture import Architecture
from app.models.enums import ScrapeJobStatus, TriggerSource, UseCase
from app.models.scrape_job import ScrapeJob, ScrapeJobError, ScrapeJobStats


class ArchitectureWriter(Protocol):
    """Write access to the architecture inventory."""

    async def upsert(self, architecture: Architecture) -> None:
        """Insert or update by ``source_url`` — scraping is idempotent (§5.1)."""
        ...


class ArchitectureReader(Protocol):
    """Read access to the architecture inventory."""

    async def list_page(
        self,
        *,
        limit: int,
        offset: int,
        use_case: UseCase | None = None,
        tag: str | None = None,
    ) -> tuple[list[Architecture], int]:
        """Return a page of architectures (newest first) and the total match count.

        Filters are ANDed; ``None`` means unfiltered on that dimension.
        """
        ...

    async def get_by_slug(self, slug: str) -> Architecture | None:
        """Fetch one architecture by its public slug, or ``None`` if unknown."""
        ...


class ScrapeJobRecorder(Protocol):
    """Lifecycle recording for scrape job documents."""

    async def create(self, trigger_source: TriggerSource) -> ScrapeJob:
        """Create a job in ``pending`` state and return it."""
        ...

    async def mark_status(self, job_id: str, status: ScrapeJobStatus) -> None:
        """Transition a job's status (e.g. pending → running)."""
        ...

    async def finish(
        self,
        job_id: str,
        status: ScrapeJobStatus,
        stats: ScrapeJobStats,
        errors: list[ScrapeJobError],
    ) -> None:
        """Record final stats/errors and stamp ``finished_at``."""
        ...

    async def get(self, job_id: str) -> ScrapeJob | None:
        """Fetch one job by id, or ``None`` if unknown."""
        ...
