"""API DTOs for the scrape endpoints (CLAUDE.md §6)."""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ScrapeJobStatus, TriggerSource
from app.models.scrape_job import ScrapeJob, ScrapeJobError, ScrapeJobStats


class TriggerScrapeResponse(BaseModel):
    """Returned by ``POST /scrape`` — the accepted job's id and initial status."""

    job_id: str
    status: ScrapeJobStatus


class ScrapeJobResponse(BaseModel):
    """Full job record for status polling and history."""

    job_id: str
    status: ScrapeJobStatus
    trigger_source: TriggerSource
    stats: ScrapeJobStats
    errors: list[ScrapeJobError]
    started_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_domain(cls, job: ScrapeJob) -> "ScrapeJobResponse":
        return cls(
            job_id=job.id,
            status=job.status,
            trigger_source=job.trigger_source,
            stats=job.stats,
            errors=job.errors,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )


class ScrapeJobListResponse(BaseModel):
    """Recent scrape-job history."""

    items: list[ScrapeJobResponse]
