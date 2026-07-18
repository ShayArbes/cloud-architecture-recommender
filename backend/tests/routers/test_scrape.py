"""Tests for the scrape endpoints (S2.3) — fakes via dependency overrides."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ConflictError
from app.dependencies import get_scrape_job_recorder, get_scrape_service
from app.main import app
from app.models.enums import ScrapeJobStatus, TriggerSource
from app.models.scrape_job import ScrapeJob
from tests.services.fakes import FakeScrapeJobRecorder


class RecordingScrapeService:
    """Fake ScrapeService that records start/run calls against a shared recorder."""

    def __init__(self, recorder: FakeScrapeJobRecorder, *, active: bool = False) -> None:
        self._recorder = recorder
        self._active = active
        self.run_calls: list[tuple[str, int]] = []

    async def start_job(self, trigger_source: TriggerSource) -> ScrapeJob:
        if self._active:
            raise ConflictError("A scrape job is already in progress")
        return await self._recorder.create(trigger_source)

    async def run_job(self, job_id: str, limit: int) -> None:
        self.run_calls.append((job_id, limit))
        await self._recorder.mark_status(job_id, ScrapeJobStatus.RUNNING)


@pytest.fixture
def recorder() -> FakeScrapeJobRecorder:
    return FakeScrapeJobRecorder()


def override(service: RecordingScrapeService, recorder: FakeScrapeJobRecorder) -> None:
    app.dependency_overrides[get_scrape_service] = lambda: service
    app.dependency_overrides[get_scrape_job_recorder] = lambda: recorder


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_trigger_returns_202_with_job_id_and_schedules_run(
    recorder: FakeScrapeJobRecorder,
) -> None:
    service = RecordingScrapeService(recorder)
    override(service, recorder)

    with TestClient(app) as client:
        response = client.post("/api/v1/scrape?limit=5")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["job_id"]
    # Background task ran after the response was returned.
    assert service.run_calls == [(body["job_id"], 5)]


def test_trigger_uses_default_limit(recorder: FakeScrapeJobRecorder) -> None:
    service = RecordingScrapeService(recorder)
    override(service, recorder)

    with TestClient(app) as client:
        client.post("/api/v1/scrape")

    assert service.run_calls[0][1] == 20


def test_trigger_rejects_concurrent_job_with_409(recorder: FakeScrapeJobRecorder) -> None:
    service = RecordingScrapeService(recorder, active=True)
    override(service, recorder)

    with TestClient(app) as client:
        response = client.post("/api/v1/scrape")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert service.run_calls == []  # nothing scheduled


def test_trigger_over_max_limit_returns_422(recorder: FakeScrapeJobRecorder) -> None:
    override(RecordingScrapeService(recorder), recorder)

    with TestClient(app) as client:
        assert client.post("/api/v1/scrape?limit=101").status_code == 422


async def test_get_job_status(recorder: FakeScrapeJobRecorder) -> None:
    job = await recorder.create(TriggerSource.API)
    override(RecordingScrapeService(recorder), recorder)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/scrape/jobs/{job.id}")

    assert response.status_code == 200
    assert response.json()["job_id"] == job.id
    assert response.json()["status"] == "pending"


def test_get_unknown_job_returns_404_envelope(recorder: FakeScrapeJobRecorder) -> None:
    override(RecordingScrapeService(recorder), recorder)

    with TestClient(app) as client:
        response = client.get("/api/v1/scrape/jobs/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCRAPE_JOB_NOT_FOUND"


async def test_job_history_lists_newest_first(recorder: FakeScrapeJobRecorder) -> None:
    first = await recorder.create(TriggerSource.SEED)
    second = await recorder.create(TriggerSource.API)
    override(RecordingScrapeService(recorder), recorder)

    with TestClient(app) as client:
        body = client.get("/api/v1/scrape/jobs").json()

    assert [item["job_id"] for item in body["items"]] == [second.id, first.id]
