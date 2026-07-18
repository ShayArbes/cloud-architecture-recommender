"""Integration tests for the architecture repository (S1.4/S2.1)."""

from datetime import UTC, datetime, timedelta

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
from app.repositories.protocols import ArchitectureReader, ArchitectureWriter

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


def _now_ms() -> datetime:
    # BSON stores millisecond precision — truncate so round-trips compare equal.
    now = datetime.now(UTC)
    return now.replace(microsecond=(now.microsecond // 1000) * 1000)


def make_architecture(
    title: str = "Sample App",
    description: str = "v1",
    *,
    slug: str = "sample-app",
    source_url: str = "https://aws.amazon.com/solutions/sample-app",
    use_cases: list[UseCase] | None = None,
    tags: list[str] | None = None,
    scraped_at: datetime | None = None,
) -> Architecture:
    resolved_use_cases = use_cases if use_cases is not None else CHARACTERISTICS.use_cases
    characteristics = CHARACTERISTICS.model_copy(update={"use_cases": resolved_use_cases})
    timestamp = scraped_at or _now_ms()
    return Architecture(
        slug=slug,
        title=title,
        source_url=source_url,
        description=description,
        use_cases=resolved_use_cases,
        aws_services=[
            AwsService(name="AWS Lambda", category=ServiceCategory.COMPUTE, purpose="compute")
        ],
        characteristics=characteristics,
        diagram_url=None,
        tags=tags if tags is not None else ["lambda"],
        parser_version="rules-v1",
        scraped_at=timestamp,
        parsed_at=timestamp,
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


def test_repository_satisfies_reader_protocol(mongo_database: MongoDatabase) -> None:
    checked: ArchitectureReader = MongoArchitectureRepository(mongo_database)

    assert checked is not None


async def _seed_three(repository: MongoArchitectureRepository) -> None:
    base = datetime(2026, 7, 1, tzinfo=UTC)
    await repository.upsert(
        make_architecture(
            slug="web-a",
            source_url="https://aws.amazon.com/solutions/web-a",
            use_cases=[UseCase.WEB_APPLICATION],
            tags=["lambda", "dynamodb"],
            scraped_at=base,
        )
    )
    await repository.upsert(
        make_architecture(
            slug="shop-b",
            source_url="https://aws.amazon.com/solutions/shop-b",
            use_cases=[UseCase.ECOMMERCE],
            tags=["lambda"],
            scraped_at=base + timedelta(hours=1),
        )
    )
    await repository.upsert(
        make_architecture(
            slug="web-c",
            source_url="https://aws.amazon.com/solutions/web-c",
            use_cases=[UseCase.WEB_APPLICATION],
            tags=["cloudfront"],
            scraped_at=base + timedelta(hours=2),
        )
    )


async def test_list_page_returns_newest_first_with_total(
    mongo_database: MongoDatabase,
) -> None:
    repository = MongoArchitectureRepository(mongo_database)
    await _seed_three(repository)

    page, total = await repository.list_page(limit=20, offset=0)

    assert total == 3
    assert [arch.slug for arch in page] == ["web-c", "shop-b", "web-a"]


async def test_list_page_paginates(mongo_database: MongoDatabase) -> None:
    repository = MongoArchitectureRepository(mongo_database)
    await _seed_three(repository)

    page, total = await repository.list_page(limit=1, offset=1)

    assert total == 3
    assert [arch.slug for arch in page] == ["shop-b"]


async def test_list_page_filters_by_use_case_and_tag(mongo_database: MongoDatabase) -> None:
    repository = MongoArchitectureRepository(mongo_database)
    await _seed_three(repository)

    by_use_case, use_case_total = await repository.list_page(
        limit=20, offset=0, use_case=UseCase.WEB_APPLICATION
    )
    assert use_case_total == 2
    assert {arch.slug for arch in by_use_case} == {"web-a", "web-c"}

    by_tag, tag_total = await repository.list_page(limit=20, offset=0, tag="cloudfront")
    assert tag_total == 1
    assert [arch.slug for arch in by_tag] == ["web-c"]


async def test_list_all_returns_every_candidate(mongo_database: MongoDatabase) -> None:
    repository = MongoArchitectureRepository(mongo_database)
    await _seed_three(repository)

    everything = await repository.list_all()

    assert {arch.slug for arch in everything} == {"web-a", "shop-b", "web-c"}
