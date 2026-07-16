"""Domain models for parsed AWS reference architectures (CLAUDE.md §5.1)."""

from datetime import datetime

from pydantic import BaseModel, Field

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


class AwsService(BaseModel):
    """One AWS service used by an architecture."""

    name: str
    category: ServiceCategory
    purpose: str


class ArchitectureCharacteristics(BaseModel):
    """The 9 recommendation dimensions an architecture serves (CLAUDE.md §5.1).

    Mirrors the recommendation request field-for-field so matching is a direct
    O(n·f) comparison. List-valued dimensions hold every value the design
    suits; scalar dimensions hold the strongest tier it serves well.
    """

    use_cases: list[UseCase] = Field(min_length=1)
    scale: list[Scale] = Field(min_length=1)
    traffic_patterns: list[TrafficPattern] = Field(min_length=1)
    latency_sensitivity: LatencySensitivity
    processing_styles: list[ProcessingStyle] = Field(min_length=1)
    data_intensity: DataIntensity
    availability: Availability
    ops_model: OpsModel
    cost_profile: CostProfile


class ParsedArchitecture(BaseModel):
    """Structured output of parsing one scraped architecture page."""

    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_url: str
    description: str
    use_cases: list[UseCase]
    aws_services: list[AwsService]
    characteristics: ArchitectureCharacteristics
    diagram_url: str | None
    tags: list[str]
    parser_version: str


class Architecture(ParsedArchitecture):
    """A persisted architecture document (CLAUDE.md §5.1).

    Adds the scrape/parse timestamps to the parsed payload; ``slug`` and
    ``source_url`` are the stable identifiers, so no Mongo ``_id`` is exposed.
    """

    scraped_at: datetime
    parsed_at: datetime
