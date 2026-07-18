"""API DTOs for the recommendation endpoint (CLAUDE.md §6.1, §6.2).

The request carries all 9 required dimensions as ``StrEnum`` fields, so an
invalid or missing value fails Pydantic validation and is returned as a 422
with field-level detail. Enums are the single source of truth from
``models/enums`` — never re-declared here.
"""

from pydantic import BaseModel, ConfigDict

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
