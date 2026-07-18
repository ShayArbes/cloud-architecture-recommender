"""Tests for GET /architectures (S2.1) — endpoint driven by an in-memory reader.

The reader protocol is faked so these exercise the HTTP layer (pagination,
filters, mapping, validation) without a database.
"""

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

_BASE_TIME = datetime(2026, 7, 1, tzinfo=UTC)


def make_architecture(index: int, use_case: UseCase, tags: list[str]) -> Architecture:
    scraped = _BASE_TIME + timedelta(hours=index)
    return Architecture(
        slug=f"arch-{index}",
        title=f"Architecture {index}",
        source_url=f"https://aws.amazon.com/solutions/arch-{index}",
        description="A sample architecture.",
        use_cases=[use_case],
        aws_services=[
            AwsService(name="AWS Lambda", category=ServiceCategory.COMPUTE, purpose="compute")
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[use_case],
            scale=[Scale.SMALL, Scale.MEDIUM],
            traffic_patterns=[TrafficPattern.STEADY],
            latency_sensitivity=LatencySensitivity.MEDIUM,
            processing_styles=[ProcessingStyle.REQUEST_RESPONSE],
            data_intensity=DataIntensity.MEDIUM,
            availability=Availability.HIGH,
            ops_model=OpsModel.MANAGED_SERVICES,
            cost_profile=CostProfile.LOW,
        ),
        diagram_url=None,
        tags=tags,
        parser_version="rules-v1",
        scraped_at=scraped,
        parsed_at=scraped,
    )


# Newest first is index 2, 1, 0 (scraped_at ascends with index).
_ALL = [
    make_architecture(0, UseCase.WEB_APPLICATION, ["lambda", "dynamodb"]),
    make_architecture(1, UseCase.ECOMMERCE, ["lambda"]),
    make_architecture(2, UseCase.WEB_APPLICATION, ["cloudfront"]),
]


class FakeArchitectureReader:
    """In-memory reader mirroring the Mongo repository's list semantics."""

    def __init__(self, architectures: list[Architecture]) -> None:
        self._architectures = architectures

    async def list_page(
        self,
        *,
        limit: int,
        offset: int,
        use_case: UseCase | None = None,
        tag: str | None = None,
    ) -> tuple[list[Architecture], int]:
        matches = [
            arch
            for arch in self._architectures
            if (use_case is None or use_case in arch.characteristics.use_cases)
            and (tag is None or tag in arch.tags)
        ]
        matches.sort(key=lambda arch: arch.scraped_at, reverse=True)
        return matches[offset : offset + limit], len(matches)

    async def get_by_slug(self, slug: str) -> Architecture | None:
        return next((a for a in self._architectures if a.slug == slug), None)

    async def list_all(self) -> list[Architecture]:
        return list(self._architectures)


@pytest.fixture
def client_with(request: pytest.FixtureRequest) -> Iterator[TestClient]:
    architectures: list[Architecture] = getattr(request, "param", _ALL)
    app.dependency_overrides[get_architecture_reader] = lambda: FakeArchitectureReader(
        architectures
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_lists_all_newest_first(client_with: TestClient) -> None:
    response = client_with.get("/api/v1/architectures")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == {"total": 3, "limit": 20, "offset": 0}
    slugs = [item["slug"] for item in body["items"]]
    assert slugs == ["arch-2", "arch-1", "arch-0"]  # scraped_at desc


def test_summary_projects_metadata_not_full_document(client_with: TestClient) -> None:
    item = client_with.get("/api/v1/architectures").json()["items"][0]

    assert item["service_count"] == 1
    assert "characteristics" not in item  # heavy internal field not leaked
    assert "aws_services" not in item
    assert set(item) == {
        "slug",
        "title",
        "source_url",
        "description",
        "use_cases",
        "service_count",
        "tags",
        "scraped_at",
        "parsed_at",
    }


def test_pagination_limit_and_offset(client_with: TestClient) -> None:
    body = client_with.get("/api/v1/architectures?limit=1&offset=1").json()

    assert body["page"] == {"total": 3, "limit": 1, "offset": 1}
    assert [item["slug"] for item in body["items"]] == ["arch-1"]


def test_filter_by_use_case(client_with: TestClient) -> None:
    body = client_with.get("/api/v1/architectures?use_case=web_application").json()

    assert body["page"]["total"] == 2
    assert {item["slug"] for item in body["items"]} == {"arch-0", "arch-2"}


def test_filter_by_tag(client_with: TestClient) -> None:
    body = client_with.get("/api/v1/architectures?tag=cloudfront").json()

    assert [item["slug"] for item in body["items"]] == ["arch-2"]


def test_combined_filters_are_anded(client_with: TestClient) -> None:
    body = client_with.get("/api/v1/architectures?use_case=web_application&tag=lambda").json()

    assert [item["slug"] for item in body["items"]] == ["arch-0"]


@pytest.mark.parametrize("client_with", [[]], indirect=True)
def test_empty_inventory_returns_empty_page(client_with: TestClient) -> None:
    body = client_with.get("/api/v1/architectures").json()

    assert body["items"] == []
    assert body["page"]["total"] == 0


def test_invalid_use_case_returns_422_envelope(client_with: TestClient) -> None:
    response = client_with.get("/api/v1/architectures?use_case=not_a_use_case")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_limit_over_max_returns_422(client_with: TestClient) -> None:
    assert client_with.get("/api/v1/architectures?limit=101").status_code == 422


def test_negative_offset_returns_422(client_with: TestClient) -> None:
    assert client_with.get("/api/v1/architectures?offset=-1").status_code == 422


# --- GET /architectures/{slug} (S2.2) --------------------------------------


def test_detail_returns_full_document(client_with: TestClient) -> None:
    response = client_with.get("/api/v1/architectures/arch-0")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "arch-0"
    assert body["title"] == "Architecture 0"
    # Detail exposes the heavy fields the summary omits.
    assert body["aws_services"][0]["name"] == "AWS Lambda"
    assert body["aws_services"][0]["category"] == "compute"
    assert body["characteristics"]["ops_model"] == "managed_services"
    assert set(body["use_cases"]) == {"web_application"}


def test_detail_unknown_slug_returns_404_envelope(client_with: TestClient) -> None:
    response = client_with.get("/api/v1/architectures/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "ARCHITECTURE_NOT_FOUND"
    assert error["details"] == {"slug": "does-not-exist"}
