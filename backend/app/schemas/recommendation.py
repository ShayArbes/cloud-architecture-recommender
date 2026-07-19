"""API DTOs for the recommendation endpoint (CLAUDE.md §6.1, §6.2).

The request carries all 9 required dimensions as ``StrEnum`` fields, so an
invalid or missing value fails Pydantic validation and is returned as a 422
with field-level detail. Enums are the single source of truth from
``models/enums`` — never re-declared here.

The optional bonus (CLAUDE.md §6.1) is ``FlexibleRecommendationRequest``: the
same 9 fields as free text, normalized to these enums by a separate step in
front of the engine — the strict request and the scoring engine are unchanged.
"""

from pydantic import BaseModel, ConfigDict, Field

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
from app.schemas.architecture import ArchitectureSummary


class RecommendationRequest(BaseModel):
    """The 9-dimension requirements object (all fields required)."""

    # Reject unknown fields so a typo'd dimension is a 422, not silently ignored.
    model_config = ConfigDict(extra="forbid")

    use_case: UseCase
    scale: Scale
    traffic_pattern: TrafficPattern
    latency_sensitivity: LatencySensitivity
    processing_style: ProcessingStyle
    data_intensity: DataIntensity
    availability_requirement: Availability
    ops_preference: OpsModel
    budget_sensitivity: CostProfile


class FlexibleRecommendationRequest(BaseModel):
    """The 9-dimension requirements as free text (bonus, CLAUDE.md §6.1).

    Every field is a required non-empty string. A normalization step maps each
    value to the nearest enum before scoring; unmappable values are rejected
    there. Structural validation (missing/unknown fields) still happens here.
    """

    model_config = ConfigDict(extra="forbid")

    use_case: str = Field(min_length=1)
    scale: str = Field(min_length=1)
    traffic_pattern: str = Field(min_length=1)
    latency_sensitivity: str = Field(min_length=1)
    processing_style: str = Field(min_length=1)
    data_intensity: str = Field(min_length=1)
    availability_requirement: str = Field(min_length=1)
    ops_preference: str = Field(min_length=1)
    budget_sensitivity: str = Field(min_length=1)


class Recommendation(BaseModel):
    """One ranked architecture with its score, explanation, and per-field breakdown."""

    architecture: ArchitectureSummary
    score: float
    explanation: str
    match_breakdown: dict[str, float]


class RecommendationResponse(BaseModel):
    """Ranked recommendations plus how many candidates were evaluated."""

    recommendations: list[Recommendation]
    total_candidates_evaluated: int
