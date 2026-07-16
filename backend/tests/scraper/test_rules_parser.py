"""Tests for the rule-based parser (S1.2/S1.3) — real AWS pages as fixtures, no network."""

from pathlib import Path

import pytest

from app.core.errors import ScrapeError
from app.models.enums import ServiceCategory
from app.scraper.parser import ArchitectureParser
from app.scraper.rules_parser import RulesBasedParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def parser() -> RulesBasedParser:
    return RulesBasedParser()


def test_parser_satisfies_protocol(parser: RulesBasedParser) -> None:
    checked: ArchitectureParser = parser  # would fail mypy if the protocol drifted

    assert checked.parser_version == "rules-v1"


async def test_parses_virtual_waiting_room_fixture(parser: RulesBasedParser) -> None:
    source_url = "https://aws.amazon.com/solutions/implementations/virtual-waiting-room-on-aws"

    result = await parser.parse(load_fixture("virtual_waiting_room.html"), source_url)

    assert result.title == "Virtual Waiting Room on AWS"
    assert result.slug == "virtual-waiting-room-on-aws"
    assert result.source_url == source_url
    assert result.description.startswith("This solution helps buffer incoming user requests")
    assert result.parser_version == "rules-v1"
    service_names = {service.name for service in result.aws_services}
    assert {"Amazon CloudFront", "Amazon DynamoDB", "AWS Lambda"} <= service_names
    assert "cloudfront" in result.tags


async def test_parses_distributed_load_testing_fixture(parser: RulesBasedParser) -> None:
    source_url = "https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws"

    result = await parser.parse(load_fixture("distributed_load_testing.html"), source_url)

    assert result.title == "Distributed Load Testing on AWS"
    assert result.diagram_url is not None
    assert result.diagram_url.startswith("https://aws.amazon.com/")
    assert "architecture-diagram" in result.diagram_url
    service_names = {service.name for service in result.aws_services}
    assert {"AWS Fargate", "Amazon S3", "Amazon API Gateway"} <= service_names
    fargate = next(s for s in result.aws_services if s.name == "AWS Fargate")
    assert fargate.category is ServiceCategory.COMPUTE
    assert fargate.purpose  # every service carries a human-readable purpose


async def test_every_fixture_yields_complete_characteristics(parser: RulesBasedParser) -> None:
    """S1.3 AC: every stored architecture has a complete, enum-valid characteristics object."""
    for fixture in ("virtual_waiting_room.html", "distributed_load_testing.html"):
        result = await parser.parse(load_fixture(fixture), f"https://example.com/{fixture}")

        # Pydantic already enforces enum validity; assert list dimensions are populated.
        characteristics = result.characteristics
        assert characteristics.use_cases
        assert characteristics.scale
        assert characteristics.traffic_patterns
        assert characteristics.processing_styles
        assert result.use_cases == characteristics.use_cases


async def test_title_falls_back_to_title_tag(parser: RulesBasedParser) -> None:
    html = "<html><head><title>Batch Pipeline | AWS Solutions</title></head><body></body></html>"

    result = await parser.parse(html, "https://example.com/batch")

    assert result.title == "Batch Pipeline"
    assert result.slug == "batch-pipeline"


async def test_page_without_title_raises_scrape_error(parser: RulesBasedParser) -> None:
    with pytest.raises(ScrapeError):
        await parser.parse(
            "<html><body><p>no headings here</p></body></html>", "https://example.com/x"
        )


async def test_description_falls_back_to_first_substantial_paragraph(
    parser: RulesBasedParser,
) -> None:
    long_paragraph = (
        "This architecture ingests clickstream events and aggregates them for near "
        "real-time dashboards across multiple regions."
    )
    html = f"<html><body><h1>Clickstream</h1><p>short</p><p>{long_paragraph}</p></body></html>"

    result = await parser.parse(html, "https://example.com/clickstream")

    assert result.description == long_paragraph


async def test_services_deduplicated_and_case_sensitive(parser: RulesBasedParser) -> None:
    html = (
        "<html><body><h1>Sample</h1>"
        "<p>Uses AWS Lambda and more Lambda functions with s3://bucket paths.</p>"
        "</body></html>"
    )

    result = await parser.parse(html, "https://example.com/sample")

    service_names = [service.name for service in result.aws_services]
    assert service_names.count("AWS Lambda") == 1
    assert "Amazon S3" not in service_names  # lowercase s3:// must not match
