"""Scrape orchestration service (CLAUDE.md §3.1, §3.5).

Business logic only: decides when a job may start, drives the pipeline, and
records the job's lifecycle and stats. Depends on repository protocols and a
``ScrapePipeline`` protocol, so it is unit-testable without HTTP or MongoDB.
"""

import logging
from datetime import UTC, datetime

from app.core.errors import ConflictError
from app.models.architecture import Architecture, ParsedArchitecture
from app.models.enums import ScrapeJobStatus, TriggerSource
from app.models.scrape_job import ScrapeJob, ScrapeJobError, ScrapeJobStats
from app.repositories.protocols import ArchitectureWriter, ScrapeJobRecorder
from app.scraper.pipeline import PipelineResult, ScrapePipeline

logger = logging.getLogger(__name__)


class ScrapeService:
    """Coordinates job records, the scrape pipeline, and persistence."""

    def __init__(
        self,
        job_recorder: ScrapeJobRecorder,
        architecture_writer: ArchitectureWriter,
        pipeline: ScrapePipeline,
    ) -> None:
        self._job_recorder = job_recorder
        self._architecture_writer = architecture_writer
        self._pipeline = pipeline

    async def start_job(self, trigger_source: TriggerSource) -> ScrapeJob:
        """Create a pending job, rejecting a concurrent run with a 409.

        Raises:
            ConflictError: if a pending or running job already exists.
        """
        if await self._job_recorder.has_active_job():
            raise ConflictError("A scrape job is already in progress")
        return await self._job_recorder.create(trigger_source)

    async def run_job(self, job_id: str, limit: int) -> None:
        """Execute the pipeline for ``job_id`` and record its outcome.

        Runs as a background task. A fatal pipeline failure marks the job
        ``failed``; per-page failures are recorded but still ``completed`` —
        the API process must never crash because a scrape failed (§3.5).
        """
        await self._job_recorder.mark_status(job_id, ScrapeJobStatus.RUNNING)
        try:
            result = await self._pipeline.run(limit)
        except Exception as exc:  # noqa: BLE001 - top-level job boundary; must not propagate
            logger.exception("Scrape job %s failed fatally", job_id)
            await self._job_recorder.finish(
                job_id,
                ScrapeJobStatus.FAILED,
                ScrapeJobStats(),
                [ScrapeJobError(url="", reason=f"{type(exc).__name__}: {exc}")],
            )
            return

        persisted, errors = await self._persist(result)
        stats = ScrapeJobStats(
            pages_found=result.pages_found,
            parsed_ok=persisted,
            failed=len(errors),
        )
        await self._job_recorder.finish(job_id, ScrapeJobStatus.COMPLETED, stats, errors)
        logger.info(
            "Scrape job %s completed: %d persisted, %d failed", job_id, persisted, stats.failed
        )

    async def _persist(self, result: PipelineResult) -> tuple[int, list[ScrapeJobError]]:
        """Upsert parsed architectures; return (persisted count, all recorded errors).

        Errors combine pipeline failures (fetch/parse) with write failures — a
        page that parses but fails to persist is not counted as ``parsed_ok``.
        """
        now = datetime.now(UTC)
        errors = list(result.errors)
        persisted = 0
        for parsed in result.parsed:
            try:
                await self._architecture_writer.upsert(self._to_architecture(parsed, now))
            except Exception as exc:  # noqa: BLE001 - one bad write must not abort the job
                logger.warning("Failed to persist %s: %s", parsed.source_url, exc)
                errors.append(ScrapeJobError(url=parsed.source_url, reason=str(exc)))
            else:
                persisted += 1
        return persisted, errors

    @staticmethod
    def _to_architecture(parsed: ParsedArchitecture, timestamp: datetime) -> Architecture:
        return Architecture(**parsed.model_dump(), scraped_at=timestamp, parsed_at=timestamp)
