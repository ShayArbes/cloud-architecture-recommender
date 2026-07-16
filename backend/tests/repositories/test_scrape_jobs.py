"""Integration tests for the scrape job repository (S1.4) — lifecycle records."""

from app.db.client import MongoDatabase
from app.models.enums import ScrapeJobStatus, TriggerSource
from app.models.scrape_job import ScrapeJobError, ScrapeJobStats
from app.repositories.protocols import ScrapeJobRecorder
from app.repositories.scrape_jobs import MongoScrapeJobRepository


def test_repository_satisfies_recorder_protocol(mongo_database: MongoDatabase) -> None:
    checked: ScrapeJobRecorder = MongoScrapeJobRepository(mongo_database)

    assert checked is not None


async def test_created_job_is_pending_with_zeroed_stats(mongo_database: MongoDatabase) -> None:
    repository = MongoScrapeJobRepository(mongo_database)

    job = await repository.create(TriggerSource.API)

    assert job.status is ScrapeJobStatus.PENDING
    assert job.trigger_source is TriggerSource.API
    assert job.stats == ScrapeJobStats()
    assert job.errors == []
    assert job.finished_at is None


async def test_full_lifecycle_records_stats_and_errors(mongo_database: MongoDatabase) -> None:
    """S1.4 AC: job stats accurate; per-page failures recorded, run completes."""
    repository = MongoScrapeJobRepository(mongo_database)
    job = await repository.create(TriggerSource.MANUAL)

    await repository.mark_status(job.id, ScrapeJobStatus.RUNNING)
    running = await repository.get(job.id)
    assert running is not None
    assert running.status is ScrapeJobStatus.RUNNING

    stats = ScrapeJobStats(pages_found=25, parsed_ok=23, failed=2)
    errors = [ScrapeJobError(url="https://aws.amazon.com/x", reason="timeout after 3 retries")]
    await repository.finish(job.id, ScrapeJobStatus.COMPLETED, stats, errors)

    finished = await repository.get(job.id)
    assert finished is not None
    assert finished.status is ScrapeJobStatus.COMPLETED
    assert finished.stats == stats
    assert finished.errors == errors
    assert finished.finished_at is not None
    assert finished.finished_at >= finished.started_at


async def test_get_with_malformed_id_returns_none(mongo_database: MongoDatabase) -> None:
    repository = MongoScrapeJobRepository(mongo_database)

    assert await repository.get("not-an-object-id") is None
