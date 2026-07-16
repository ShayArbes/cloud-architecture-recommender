"""Domain models for scrape job records (CLAUDE.md §5.2)."""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ScrapeJobStatus, TriggerSource


class ScrapeJobStats(BaseModel):
    """Aggregate counters for one scrape run."""

    pages_found: int = 0
    parsed_ok: int = 0
    failed: int = 0


class ScrapeJobError(BaseModel):
    """A per-page failure recorded on the job; never aborts the run."""

    url: str
    reason: str


class ScrapeJob(BaseModel):
    """One triggered scrape run — audit trail and status-polling document."""

    id: str
    status: ScrapeJobStatus
    trigger_source: TriggerSource
    stats: ScrapeJobStats
    errors: list[ScrapeJobError]
    started_at: datetime
    finished_at: datetime | None
