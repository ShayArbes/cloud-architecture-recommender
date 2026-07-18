"""Tests for template-based recommendation explanations (S3.3)."""

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
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation.explanation import build_explanation

REQUEST = RecommendationRequest(
    use_case=UseCase.ECOMMERCE,
    scale=Scale.MEDIUM,
    traffic_pattern=TrafficPattern.BURSTY,
    latency_sensitivity=LatencySensitivity.MEDIUM,
    processing_style=ProcessingStyle.REQUEST_RESPONSE,
    data_intensity=DataIntensity.MEDIUM,
    availability_requirement=Availability.HIGH,
    ops_preference=OpsModel.MANAGED_SERVICES,
    budget_sensitivity=CostProfile.MEDIUM,
)

_PERFECT = dict.fromkeys(
    [
        "use_case",
        "scale",
        "traffic_pattern",
        "latency_sensitivity",
        "processing_style",
        "data_intensity",
        "availability_requirement",
        "ops_preference",
        "budget_sensitivity",
    ],
    1.0,
)


def test_perfect_match_reads_as_strong_fit_without_weakness() -> None:
    text = build_explanation(REQUEST, _PERFECT, 1.0)

    assert text.startswith("Strong fit:")
    assert "use case (ecommerce)" in text
    assert "Weaker on" not in text


def test_names_the_weakest_dimension_on_partial_fit() -> None:
    breakdown = {**_PERFECT, "scale": 0.4, "budget_sensitivity": 0.1}

    text = build_explanation(REQUEST, breakdown, 0.7)

    assert text.startswith("Good fit:")
    # The lowest-scoring dimension is named first among the weaknesses.
    assert "cost profile (medium)" in text
    assert "Weaker on" in text


def test_qualifier_tracks_score_band() -> None:
    assert build_explanation(REQUEST, _PERFECT, 0.9).startswith("Strong fit")
    assert build_explanation(REQUEST, _PERFECT, 0.7).startswith("Good fit")
    assert build_explanation(REQUEST, _PERFECT, 0.5).startswith("Partial fit")
    assert build_explanation(REQUEST, _PERFECT, 0.2).startswith("Weak fit")


def test_always_names_a_strength_even_when_all_dimensions_are_weak() -> None:
    breakdown = dict.fromkeys(_PERFECT, 0.3)
    breakdown["use_case"] = 0.5  # the least-bad dimension

    text = build_explanation(REQUEST, breakdown, 0.3)

    assert "strong match on use case (ecommerce)" in text


def test_explanation_is_deterministic() -> None:
    breakdown = {**_PERFECT, "scale": 0.4}

    assert build_explanation(REQUEST, breakdown, 0.8) == build_explanation(REQUEST, breakdown, 0.8)
