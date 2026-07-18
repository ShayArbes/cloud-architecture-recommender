"""Scrape trigger and job-status endpoints — HTTP layer only (CLAUDE.md §3.1)."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core.constants import DEFAULT_SCRAPE_LIMIT, JOB_HISTORY_LIMIT, MAX_SCRAPE_LIMIT
from app.core.errors import NotFoundError
from app.dependencies import ScrapeJobRecorderDep, ScrapeServiceDep
from app.models.enums import TriggerSource
from app.schemas.scrape import (
    ScrapeJobListResponse,
    ScrapeJobResponse,
    TriggerScrapeResponse,
)

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=TriggerScrapeResponse)
async def trigger_scrape(
    service: ScrapeServiceDep,
    background_tasks: BackgroundTasks,
    limit: Annotated[int, Query(ge=1, le=MAX_SCRAPE_LIMIT)] = DEFAULT_SCRAPE_LIMIT,
) -> TriggerScrapeResponse:
    """Start a scrape job as a background task; 202 with the job id, 409 if one is running."""
    job = await service.start_job(TriggerSource.API)
    background_tasks.add_task(service.run_job, job.id, limit)
    return TriggerScrapeResponse(job_id=job.id, status=job.status)


@router.get("/jobs", response_model=ScrapeJobListResponse)
async def list_scrape_jobs(recorder: ScrapeJobRecorderDep) -> ScrapeJobListResponse:
    """Return recent scrape-job history, newest first."""
    jobs = await recorder.list_recent(JOB_HISTORY_LIMIT)
    return ScrapeJobListResponse(items=[ScrapeJobResponse.from_domain(job) for job in jobs])


@router.get("/jobs/{job_id}", response_model=ScrapeJobResponse)
async def get_scrape_job(job_id: str, recorder: ScrapeJobRecorderDep) -> ScrapeJobResponse:
    """Return one job's status and stats, or a 404 envelope for unknown ids."""
    job = await recorder.get(job_id)
    if job is None:
        raise NotFoundError(
            f"No scrape job with id '{job_id}'",
            details={"job_id": job_id},
            code="SCRAPE_JOB_NOT_FOUND",
        )
    return ScrapeJobResponse.from_domain(job)
