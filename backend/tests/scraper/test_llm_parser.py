"""Tests for the optional Claude-enriched parser and parser factory (S1.3).

The Claude client is monkeypatched — no network, no API key required.
"""

from typing import Any

import pytest
from anthropic import AsyncAnthropic

from app.core.config import Settings
from app.models.architecture import ArchitectureCharacteristics
from app.models.enums import (
    Availability,
    CostProfile,
    DataIntensity,
    LatencySensitivity,
    OpsModel,
    ProcessingStyle,
    Scale,
    TrafficPattern,
    UseCase,
)
from app.scraper.factory import create_parser
from app.scraper.llm_parser import LLM_PARSER_VERSION, ClaudeEnrichedParser
from app.scraper.rules_parser import RulesBasedParser

HTML = (
    "<html><head><title>Serverless E-Commerce</title>"
    '<meta name="description" content="An ecommerce storefront on AWS Lambda."></head>'
    "<body><h1>Serverless E-Commerce</h1><p>Uses Lambda, DynamoDB and API Gateway.</p></body>"
    "</html>"
)
SOURCE_URL = "https://example.com/serverless-ecommerce"

CLAUDE_CHARACTERISTICS = ArchitectureCharacteristics(
    use_cases=[UseCase.ECOMMERCE, UseCase.WEB_APPLICATION],
    scale=[Scale.SMALL, Scale.MEDIUM],
    traffic_patterns=[TrafficPattern.SPIKY],
    latency_sensitivity=LatencySensitivity.HIGH,
    processing_styles=[ProcessingStyle.REQUEST_RESPONSE],
    data_intensity=DataIntensity.MEDIUM,
    availability=Availability.HIGH,
    ops_model=OpsModel.MANAGED_SERVICES,
    cost_profile=CostProfile.MEDIUM,
)


class FakeParsedMessage:
    def __init__(self, parsed_output: ArchitectureCharacteristics | None) -> None:
        self.parsed_output = parsed_output


def make_parser(
    monkeypatch: pytest.MonkeyPatch, parse_result: FakeParsedMessage | Exception
) -> ClaudeEnrichedParser:
    client = AsyncAnthropic(api_key="test-key")

    async def fake_parse(**_kwargs: Any) -> FakeParsedMessage:
        if isinstance(parse_result, Exception):
            raise parse_result
        return parse_result

    monkeypatch.setattr(client.messages, "parse", fake_parse)
    return ClaudeEnrichedParser(client, RulesBasedParser())


async def test_successful_enrichment_replaces_characteristics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = make_parser(monkeypatch, FakeParsedMessage(CLAUDE_CHARACTERISTICS))

    result = await parser.parse(HTML, SOURCE_URL)

    assert result.characteristics == CLAUDE_CHARACTERISTICS
    assert result.use_cases == CLAUDE_CHARACTERISTICS.use_cases
    assert result.parser_version == LLM_PARSER_VERSION
    assert result.title == "Serverless E-Commerce"  # structural fields stay rule-based


async def test_llm_failure_falls_back_to_rules_result(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = make_parser(monkeypatch, RuntimeError("api unreachable"))

    result = await parser.parse(HTML, SOURCE_URL)

    assert result.parser_version == "rules-v1"
    assert result.characteristics.use_cases  # rule-based characteristics intact


async def test_unparseable_llm_output_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = make_parser(monkeypatch, FakeParsedMessage(None))

    result = await parser.parse(HTML, SOURCE_URL)

    assert result.parser_version == "rules-v1"


def test_factory_returns_rules_parser_without_api_key() -> None:
    settings = Settings(anthropic_api_key="", _env_file=None)

    parser = create_parser(settings)

    assert isinstance(parser, RulesBasedParser)


def test_factory_returns_claude_parser_with_api_key() -> None:
    settings = Settings(anthropic_api_key="sk-test", _env_file=None)

    parser = create_parser(settings)

    assert isinstance(parser, ClaudeEnrichedParser)
    assert parser.parser_version == "llm-claude-sonnet-5-v1"
