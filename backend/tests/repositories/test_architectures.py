"""Integration tests for the architecture repository (S1.4) — idempotent upserts."""

from datetime import UTC, datetime

from app.db.client import MongoDatabase
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
from app.repositories.architectures import MongoArchitectureRepository
from app.repositories.protocols import ArchitectureWriter

CHARACTERISTICS = ArchitectureCharacteristics(
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


def make_architecture(title: str = "Sample App", description: str = "v1") -> Architecture:
    # BSON stores millisecond precision — truncate so round-trips compare equal.
    now = datetime.now(UTC)
    now = now.replace(microsecond=(now.microsecond // 1000) * 1000)
    return Architecture(
        slug="sample-app",
        title=title,
        source_url="https://aws.amazon.com/solutions/sample-app",
        description=description,
        use_cases=CHARACTERISTICS.use_cases,
        aws_services=[
            AwsService(name="AWS Lambda", category=ServiceCategory.COMPUTE, purpose="compute")
        ],
        characteristics=CHARACTERISTICS,
        diagram_url=None,
        tags=["lambda"],
        parser_version="rules-v1",
        scraped_at=now,
        parsed_at=now,
    )


def test_repository_satisfies_writer_protocol(mongo_database: MongoDatabase) -> None:
    checked: ArchitectureWriter = MongoArchitectureRepository(mongo_database)

    assert checked is not None


async def test_upsert_then_get_round_trips_domain_model(mongo_database: MongoDatabase) -> None:
    repository = MongoArchitectureRepository(mongo_database)
    architecture = make_architecture()

    await repository.upsert(architecture)
    stored = await repository.get_by_slug("sample-app")

    assert stored == architecture


async def test_reupserting_same_source_url_never_duplicates(
    mongo_database: MongoDatabase,
) -> None:
    """S1.4 AC: re-running the scrape produces zero duplicates."""
    repository = MongoArchitectureRepository(mongo_database)

    await repository.upsert(make_architecture(description="first scrape"))
    await repository.upsert(make_architecture(description="second scrape"))

    assert await repository.count() == 1
    stored = await repository.get_by_slug("sample-app")
    assert stored is not None
    assert stored.description == "second scrape"  # latest scrape wins


async def test_get_by_unknown_slug_returns_none(mongo_database: MongoDatabase) -> None:
    repository = MongoArchitectureRepository(mongo_database)

    assert await repository.get_by_slug("does-not-exist") is None
