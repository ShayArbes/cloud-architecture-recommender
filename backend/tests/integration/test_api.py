"""End-to-end API integration tests (S2.4) — real Mongo, faked scrape pipeline.

Covers a happy path and an error path for every endpoint, exercising the full
router → service → repository → MongoDB stack.
"""

import asyncio

import httpx

from app.db.client import MongoDatabase
from app.db.indexes import SCRAPE_JOBS_COLLECTION
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
    ServiceCategory,
    TrafficPattern,
    UseCase,
)
from app.models.scrape_job import ScrapeJobError
from app.scraper.pipeline import PipelineResult
from tests.integration.conftest import ConfigurablePipeline

_CHARACTERISTICS = ArchitectureCharacteristics(
    use_cases=[UseCase.WEB_APPLICATION],
    scale=[Scale.SMALL, Scale.MEDIUM],
    traffic_patterns=[TrafficPattern.STEADY],
    latency_sensitivity=LatencySensitivity.MEDIUM,
    processing_styles=[ProcessingStyle.REQUEST_RESPONSE],
    data_intensity=DataIntensity.MEDIUM,
    availability=Availability.HIGH,
    ops_model=OpsModel.MANAGED_SERVICES,
    cost_profile=CostProfile.LOW,
)


def parsed(slug: str, use_case: UseCase = UseCase.WEB_APPLICATION) -> ParsedArchitecture:
    characteristics = _CHARACTERISTICS.model_copy(update={"use_cases": [use_case]})
    return ParsedArchitecture(
        slug=slug,
        title=slug.replace("-", " ").title(),
        source_url=f"https://aws.amazon.com/solutions/{slug}",
        description="An integration-test architecture.",
        use_cases=[use_case],
        aws_services=[
            AwsService(name="AWS Lambda", category=ServiceCategory.COMPUTE, purpose="compute"),
            AwsService(name="Amazon S3", category=ServiceCategory.STORAGE, purpose="storage"),
        ],
        characteristics=characteristics,
        diagram_url=None,
        tags=["lambda", "s3"],
        parser_version="rules-v1",
    )


async def _run_scrape(
    api_client: httpx.AsyncClient, pipeline: ConfigurablePipeline, result: PipelineResult
) -> dict[str, object]:
    """Trigger a scrape with a preset pipeline result and poll to a terminal state."""
    pipeline.result = result
    response = await api_client.post("/api/v1/scrape?limit=5")
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(50):
        job: dict[str, object] = (await api_client.get(f"/api/v1/scrape/jobs/{job_id}")).json()
        if job["status"] in ("completed", "failed"):
            return job
        await asyncio.sleep(0.05)
    raise AssertionError("scrape job did not reach a terminal state")


# --- /health ----------------------------------------------------------------


async def test_health_reports_connected(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mongodb": "connected"}


# --- POST /scrape → persistence → GET /architectures ------------------------


async def test_scrape_persists_and_lists_architectures(
    api_client: httpx.AsyncClient, pipeline: ConfigurablePipeline
) -> None:
    result = PipelineResult(
        parsed=[parsed("web-a"), parsed("shop-b", UseCase.ECOMMERCE)],
        errors=[ScrapeJobError(url="https://aws.amazon.com/failed", reason="timeout")],
        pages_found=3,
    )

    job = await _run_scrape(api_client, pipeline, result)

    assert job["status"] == "completed"
    assert job["stats"] == {"pages_found": 3, "parsed_ok": 2, "failed": 1}

    listing = (await api_client.get("/api/v1/architectures")).json()
    assert listing["page"]["total"] == 2
    assert {item["slug"] for item in listing["items"]} == {"web-a", "shop-b"}

    filtered = (await api_client.get("/api/v1/architectures?use_case=ecommerce")).json()
    assert [item["slug"] for item in filtered["items"]] == ["shop-b"]


async def test_list_empty_inventory(api_client: httpx.AsyncClient) -> None:
    listing = (await api_client.get("/api/v1/architectures")).json()

    assert listing["items"] == []
    assert listing["page"]["total"] == 0


async def test_list_rejects_invalid_use_case(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/architectures?use_case=bogus")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# --- GET /architectures/{slug} ----------------------------------------------


async def test_detail_returns_full_document(
    api_client: httpx.AsyncClient, pipeline: ConfigurablePipeline
) -> None:
    await _run_scrape(api_client, pipeline, PipelineResult(parsed=[parsed("web-a")], pages_found=1))

    detail = (await api_client.get("/api/v1/architectures/web-a")).json()

    assert detail["slug"] == "web-a"
    assert len(detail["aws_services"]) == 2
    assert detail["characteristics"]["ops_model"] == "managed_services"


async def test_detail_unknown_slug_returns_404(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/architectures/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ARCHITECTURE_NOT_FOUND"


# --- Scrape job endpoints ----------------------------------------------------


async def test_scrape_history_lists_completed_job(
    api_client: httpx.AsyncClient, pipeline: ConfigurablePipeline
) -> None:
    await _run_scrape(api_client, pipeline, PipelineResult(parsed=[parsed("web-a")], pages_found=1))

    history = (await api_client.get("/api/v1/scrape/jobs")).json()

    assert len(history["items"]) == 1
    assert history["items"][0]["status"] == "completed"
    assert history["items"][0]["trigger_source"] == "api"


async def test_scrape_job_unknown_id_returns_404(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/scrape/jobs/unknown")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCRAPE_JOB_NOT_FOUND"


async def test_scrape_rejects_concurrent_job_with_409(
    api_client: httpx.AsyncClient, integration_db: MongoDatabase
) -> None:
    """A pre-existing running job blocks a new trigger (§6, S2.3 AC)."""
    from datetime import UTC, datetime

    await integration_db[SCRAPE_JOBS_COLLECTION].insert_one(
        {
            "status": "running",
            "trigger_source": "api",
            "stats": {"pages_found": 0, "parsed_ok": 0, "failed": 0},
            "errors": [],
            "started_at": datetime.now(UTC),
            "finished_at": None,
        }
    )

    response = await api_client.post("/api/v1/scrape")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
