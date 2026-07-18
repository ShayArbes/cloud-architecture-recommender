"""In-memory fakes implementing the repository/pipeline protocols (S2.3 tests)."""

from datetime import UTC, datetime, timedelta

from app.models.architecture import Architecture
from app.models.enums import ScrapeJobStatus, TriggerSource
from app.models.scrape_job import ScrapeJob, ScrapeJobError, ScrapeJobStats
from app.scraper.pipeline import PipelineResult


class FakeScrapeJobRecorder:
    """Ordered in-memory ScrapeJobRecorder."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScrapeJob] = {}
        self._counter = 0

    async def create(self, trigger_source: TriggerSource) -> ScrapeJob:
        self._counter += 1
        job = ScrapeJob(
            id=f"job-{self._counter}",
            status=ScrapeJobStatus.PENDING,
            trigger_source=trigger_source,
            stats=ScrapeJobStats(),
            errors=[],
            # Distinct, increasing timestamps so history ordering is deterministic.
            started_at=datetime.now(UTC) + timedelta(seconds=self._counter),
            finished_at=None,
        )
        self._jobs[job.id] = job
        return job

    async def mark_status(self, job_id: str, status: ScrapeJobStatus) -> None:
        self._jobs[job_id] = self._jobs[job_id].model_copy(update={"status": status})

    async def finish(
        self,
        job_id: str,
        status: ScrapeJobStatus,
        stats: ScrapeJobStats,
        errors: list[ScrapeJobError],
    ) -> None:
        self._jobs[job_id] = self._jobs[job_id].model_copy(
            update={
                "status": status,
                "stats": stats,
                "errors": errors,
                "finished_at": datetime.now(UTC),
            }
        )

    async def get(self, job_id: str) -> ScrapeJob | None:
        return self._jobs.get(job_id)

    async def list_recent(self, limit: int) -> list[ScrapeJob]:
        ordered = sorted(self._jobs.values(), key=lambda job: job.started_at, reverse=True)
        return ordered[:limit]

    async def has_active_job(self) -> bool:
        return any(
            job.status in (ScrapeJobStatus.PENDING, ScrapeJobStatus.RUNNING)
            for job in self._jobs.values()
        )


class FakeArchitectureWriter:
    """Records upserts; can be told to fail for a given source_url."""

    def __init__(self, *, fail_on: str | None = None) -> None:
        self.upserted: list[Architecture] = []
        self._fail_on = fail_on

    async def upsert(self, architecture: Architecture) -> None:
        if architecture.source_url == self._fail_on:
            raise RuntimeError("simulated write failure")
        self.upserted.append(architecture)


class FakePipeline:
    """Returns a preset result, or raises to simulate a fatal failure."""

    def __init__(
        self, result: PipelineResult | None = None, error: Exception | None = None
    ) -> None:
        self._result = result or PipelineResult()
        self._error = error
        self.calls: list[int] = []

    async def run(self, limit: int) -> PipelineResult:
        self.calls.append(limit)
        if self._error is not None:
            raise self._error
        return self._result
