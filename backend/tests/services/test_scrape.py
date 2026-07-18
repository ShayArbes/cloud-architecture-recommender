"""Unit tests for ScrapeService (S2.3) — no HTTP, no DB, protocol fakes only."""

import pytest

from app.core.errors import ConflictError
from app.models.architecture import (
    ArchitectureCharacteristics,
    AwsService,
    ParsedArchitecture,
)
from app.models.enums import (
    Availability,
    CostProfile,
    DataIntensity,
    LatencySensitivity,
    OpsModel,
    ProcessingStyle,
    Scale,
    ScrapeJobStatus,
    ServiceCategory,
    TrafficPattern,
    TriggerSource,
    UseCase,
)
from app.models.scrape_job import ScrapeJobError
from app.scraper.pipeline import PipelineResult
from app.services.scrape import ScrapeService
from tests.services.fakes import (
    FakeArchitectureWriter,
    FakePipeline,
    FakeScrapeJobRecorder,
)

_CHARACTERISTICS = ArchitectureCharacteristics(
    use_cases=[UseCase.WEB_APPLICATION],
    scale=[Scale.SMALL],
    traffic_patterns=[TrafficPattern.STEADY],
    latency_sensitivity=LatencySensitivity.MEDIUM,
    processing_styles=[ProcessingStyle.REQUEST_RESPONSE],
    data_intensity=DataIntensity.LOW,
    availability=Availability.STANDARD,
    ops_model=OpsModel.MANAGED_SERVICES,
    cost_profile=CostProfile.LOW,
)


def parsed(slug: str) -> ParsedArchitecture:
    return ParsedArchitecture(
        slug=slug,
        title=slug.title(),
        source_url=f"https://aws.amazon.com/solutions/{slug}",
        description="desc",
        use_cases=_CHARACTERISTICS.use_cases,
        aws_services=[
            AwsService(name="AWS Lambda", category=ServiceCategory.COMPUTE, purpose="compute")
        ],
        characteristics=_CHARACTERISTICS,
        diagram_url=None,
        tags=["lambda"],
        parser_version="rules-v1",
    )


def make_service(
    recorder: FakeScrapeJobRecorder,
    writer: FakeArchitectureWriter,
    pipeline: FakePipeline,
) -> ScrapeService:
    return ScrapeService(recorder, writer, pipeline)


async def test_start_job_creates_pending_job() -> None:
    recorder = FakeScrapeJobRecorder()
    service = make_service(recorder, FakeArchitectureWriter(), FakePipeline())

    job = await service.start_job(TriggerSource.API)

    assert job.status is ScrapeJobStatus.PENDING
    assert job.trigger_source is TriggerSource.API


async def test_start_job_rejects_concurrent_run_with_conflict() -> None:
    recorder = FakeScrapeJobRecorder()
    service = make_service(recorder, FakeArchitectureWriter(), FakePipeline())
    await service.start_job(TriggerSource.API)  # leaves a pending (active) job

    with pytest.raises(ConflictError):
        await service.start_job(TriggerSource.API)


async def test_run_job_persists_and_records_accurate_stats() -> None:
    recorder = FakeScrapeJobRecorder()
    writer = FakeArchitectureWriter()
    result = PipelineResult(
        parsed=[parsed("web-a"), parsed("web-b")],
        errors=[ScrapeJobError(url="https://aws.amazon.com/x", reason="timeout")],
        pages_found=3,
    )
    service = make_service(recorder, writer, FakePipeline(result))
    job = await service.start_job(TriggerSource.API)

    await service.run_job(job.id, limit=3)

    stored = await recorder.get(job.id)
    assert stored is not None
    assert stored.status is ScrapeJobStatus.COMPLETED
    assert stored.stats.pages_found == 3
    assert stored.stats.parsed_ok == 2
    assert stored.stats.failed == 1  # the one fetch failure
    assert {a.slug for a in writer.upserted} == {"web-a", "web-b"}


async def test_run_job_records_write_failures_without_aborting() -> None:
    recorder = FakeScrapeJobRecorder()
    writer = FakeArchitectureWriter(fail_on="https://aws.amazon.com/solutions/web-a")
    result = PipelineResult(parsed=[parsed("web-a"), parsed("web-b")], pages_found=2)
    service = make_service(recorder, writer, FakePipeline(result))
    job = await service.start_job(TriggerSource.API)

    await service.run_job(job.id, limit=2)

    stored = await recorder.get(job.id)
    assert stored is not None
    assert stored.status is ScrapeJobStatus.COMPLETED  # one bad write is not fatal
    assert stored.stats.parsed_ok == 1
    assert stored.stats.failed == 1
    assert [a.slug for a in writer.upserted] == ["web-b"]  # good one still persisted


async def test_run_job_marks_failed_on_fatal_pipeline_error() -> None:
    recorder = FakeScrapeJobRecorder()
    service = make_service(
        recorder,
        FakeArchitectureWriter(),
        FakePipeline(error=RuntimeError("discovery unreachable")),
    )
    job = await service.start_job(TriggerSource.API)

    # Must not propagate — the API process must survive a failed scrape (§3.5).
    await service.run_job(job.id, limit=5)

    stored = await recorder.get(job.id)
    assert stored is not None
    assert stored.status is ScrapeJobStatus.FAILED
    assert stored.errors
    assert stored.finished_at is not None


async def test_run_job_transitions_through_running() -> None:
    recorder = FakeScrapeJobRecorder()
    service = make_service(recorder, FakeArchitectureWriter(), FakePipeline())
    job = await service.start_job(TriggerSource.API)

    # After a completed run, a fresh job may start again (no active job remains).
    await service.run_job(job.id, limit=1)
    assert not await recorder.has_active_job()
    await service.start_job(TriggerSource.API)  # should not raise
