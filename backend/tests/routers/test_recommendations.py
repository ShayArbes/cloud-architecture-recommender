"""Tests for POST /recommendations (S3.4) — endpoint over an in-memory reader."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_architecture_reader
from app.main import app
from app.models.architecture import (
    Architecture,
    ArchitectureCharacteristics,
    AwsService,
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

VALID_REQUEST = {
    "use_case": "ecommerce",
    "scale": "medium",
    "traffic_pattern": "bursty",
    "latency_sensitivity": "medium",
    "processing_style": "request_response",
    "data_intensity": "medium",
    "availability_requirement": "high",
    "ops_preference": "managed_services",
    "budget_sensitivity": "medium",
}


def characteristics(**overrides: object) -> ArchitectureCharacteristics:
    base = {
        "use_cases": [UseCase.ECOMMERCE],
        "scale": [Scale.MEDIUM],
        "traffic_patterns": [TrafficPattern.BURSTY],
        "latency_sensitivity": LatencySensitivity.MEDIUM,
        "processing_styles": [ProcessingStyle.REQUEST_RESPONSE],
        "data_intensity": DataIntensity.MEDIUM,
        "availability": Availability.HIGH,
        "ops_model": OpsModel.MANAGED_SERVICES,
        "cost_profile": CostProfile.MEDIUM,
    }
    base.update(overrides)
    return ArchitectureCharacteristics.model_validate(base)


def architecture(slug: str, chars: ArchitectureCharacteristics) -> Architecture:
    now = datetime(2026, 7, 1, tzinfo=UTC) + timedelta(hours=hash(slug) % 24)
    return Architecture(
        slug=slug,
        title=slug.title(),
        source_url=f"https://aws.amazon.com/solutions/{slug}",
        description="desc",
        use_cases=chars.use_cases,
        aws_services=[
            AwsService(name="AWS Lambda", category=ServiceCategory.COMPUTE, purpose="compute")
        ],
        characteristics=chars,
        diagram_url=None,
        tags=["lambda"],
        parser_version="rules-v1",
        scraped_at=now,
        parsed_at=now,
    )


class FakeReader:
    def __init__(self, architectures: list[Architecture]) -> None:
        self._architectures = architectures

    async def list_all(self) -> list[Architecture]:
        return list(self._architectures)

    async def list_page(
        self, **_kwargs: object
    ) -> tuple[list[Architecture], int]:  # pragma: no cover
        return self._architectures, len(self._architectures)

    async def get_by_slug(self, slug: str) -> Architecture | None:  # pragma: no cover
        return next((a for a in self._architectures if a.slug == slug), None)


_INVENTORY = [
    architecture("perfect", characteristics()),
    architecture("partial", characteristics(scale=[Scale.LARGE])),
    architecture("poor", characteristics(use_cases=[UseCase.BATCH_PROCESSING])),
    architecture("also-good", characteristics(latency_sensitivity=LatencySensitivity.HIGH)),
]


@pytest.fixture
def client_with(request: pytest.FixtureRequest) -> Iterator[TestClient]:
    inventory: list[Architecture] = getattr(request, "param", _INVENTORY)
    app.dependency_overrides[get_architecture_reader] = lambda: FakeReader(inventory)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_returns_top_three_ranked(client_with: TestClient) -> None:
    response = client_with.post("/api/v1/recommendations", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["total_candidates_evaluated"] == 4
    assert len(body["recommendations"]) == 3  # default top-3
    scores = [rec["score"] for rec in body["recommendations"]]
    assert scores == sorted(scores, reverse=True)
    assert body["recommendations"][0]["architecture"]["slug"] == "perfect"


def test_recommendation_shape_matches_contract(client_with: TestClient) -> None:
    rec = client_with.post("/api/v1/recommendations", json=VALID_REQUEST).json()["recommendations"][
        0
    ]

    assert set(rec) == {"architecture", "score", "explanation", "match_breakdown"}
    assert rec["score"] == 1.0
    assert len(rec["match_breakdown"]) == 9
    assert rec["explanation"].startswith("Strong fit")


def test_perfect_candidate_breakdown_is_all_ones(client_with: TestClient) -> None:
    rec = client_with.post("/api/v1/recommendations", json=VALID_REQUEST).json()["recommendations"][
        0
    ]

    assert all(value == 1.0 for value in rec["match_breakdown"].values())


@pytest.mark.parametrize("client_with", [[]], indirect=True)
def test_empty_inventory_returns_empty_result_not_error(client_with: TestClient) -> None:
    response = client_with.post("/api/v1/recommendations", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"] == []
    assert body["total_candidates_evaluated"] == 0


def test_missing_field_returns_422_envelope(client_with: TestClient) -> None:
    payload = {k: v for k, v in VALID_REQUEST.items() if k != "scale"}

    response = client_with.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_enum_returns_422(client_with: TestClient) -> None:
    payload = {**VALID_REQUEST, "use_case": "bogus"}

    assert client_with.post("/api/v1/recommendations", json=payload).status_code == 422


# --- Bonus: free-text endpoint (POST /recommendations/flexible, §6.1) -------


def test_flexible_endpoint_ranks_like_the_strict_one(client_with: TestClient) -> None:
    # VALID_REQUEST is already all strings, so it is a valid free-text payload.
    response = client_with.post("/api/v1/recommendations/flexible", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["total_candidates_evaluated"] == 4
    assert body["recommendations"][0]["architecture"]["slug"] == "perfect"


def test_flexible_endpoint_accepts_synonyms_and_casing(client_with: TestClient) -> None:
    payload = {
        **VALID_REQUEST,
        "use_case": "Online Store",
        "ops_preference": "serverless",
        "traffic_pattern": "Bursts",
    }

    response = client_with.post("/api/v1/recommendations/flexible", json=payload)

    assert response.status_code == 200
    assert response.json()["recommendations"][0]["architecture"]["slug"] == "perfect"


def test_flexible_unrecognized_value_returns_422_envelope(client_with: TestClient) -> None:
    payload = {**VALID_REQUEST, "use_case": "teleportation"}

    response = client_with.post("/api/v1/recommendations/flexible", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "UNRECOGNIZED_REQUIREMENT"
    assert error["details"]["field"] == "use_case"


def test_flexible_missing_field_returns_422(client_with: TestClient) -> None:
    payload = {k: v for k, v in VALID_REQUEST.items() if k != "scale"}

    assert client_with.post("/api/v1/recommendations/flexible", json=payload).status_code == 422
