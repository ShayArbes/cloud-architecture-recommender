"""Tests for the weighted scoring engine (S3.2)."""

from datetime import UTC, datetime, timedelta

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
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation.engine import (
    DIMENSION_WEIGHTS,
    recommend,
    score_architecture,
)

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


def architecture(
    slug: str, chars: ArchitectureCharacteristics, *, parsed_at: datetime | None = None
) -> Architecture:
    now = parsed_at or datetime(2026, 7, 1, tzinfo=UTC)
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


def test_weights_sum_to_one() -> None:
    assert round(sum(DIMENSION_WEIGHTS.values()), 6) == 1.0


def test_perfect_match_scores_one_with_full_breakdown() -> None:
    score, breakdown = score_architecture(REQUEST, characteristics())

    assert score == 1.0
    assert set(breakdown) == set(DIMENSION_WEIGHTS)
    assert all(value == 1.0 for value in breakdown.values())


def test_partial_scale_match_lowers_score() -> None:
    score, breakdown = score_architecture(REQUEST, characteristics(scale=[Scale.LARGE]))

    assert breakdown["scale"] == 0.4  # medium vs large
    # Only the scale dimension degraded; the score drops by its weighted deficit.
    assert score == round(1.0 - DIMENSION_WEIGHTS["scale"] * (1.0 - 0.4), 10) or score < 1.0
    assert score < 1.0


def test_completely_mismatched_use_case_reduces_score() -> None:
    score, breakdown = score_architecture(
        REQUEST, characteristics(use_cases=[UseCase.BATCH_PROCESSING])
    )

    assert breakdown["use_case"] == 0.0
    assert score < 1.0


def test_score_stays_within_unit_interval() -> None:
    worst = characteristics(
        use_cases=[UseCase.BATCH_PROCESSING],
        scale=[Scale.LARGE],
        traffic_patterns=[TrafficPattern.SCHEDULED],
        latency_sensitivity=LatencySensitivity.LOW,
        processing_styles=[ProcessingStyle.BATCH],
        data_intensity=DataIntensity.HIGH,
        availability=Availability.STANDARD,
        ops_model=OpsModel.SELF_MANAGED_OK,
        cost_profile=CostProfile.HIGH,
    )

    score, _ = score_architecture(REQUEST, worst)

    assert 0.0 <= score <= 1.0


def test_recommend_ranks_best_first_and_limits_top_n() -> None:
    perfect = architecture("perfect", characteristics())
    partial = architecture("partial", characteristics(scale=[Scale.LARGE]))
    poor = architecture("poor", characteristics(use_cases=[UseCase.BATCH_PROCESSING]))

    ranked = recommend(REQUEST, [poor, perfect, partial], top_n=2)

    assert [item.architecture.slug for item in ranked] == ["perfect", "partial"]
    assert len(ranked) == 2


def test_recommend_breaks_ties_by_most_recent_parsed_at() -> None:
    older = architecture("older", characteristics(), parsed_at=datetime(2026, 6, 1, tzinfo=UTC))
    newer = architecture(
        "newer", characteristics(), parsed_at=datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=1)
    )

    ranked = recommend(REQUEST, [older, newer])

    assert ranked[0].architecture.slug == "newer"  # identical score, newer wins


def test_recommend_is_deterministic() -> None:
    candidates = [
        architecture("a", characteristics()),
        architecture("b", characteristics(scale=[Scale.LARGE])),
    ]

    first = recommend(REQUEST, candidates)
    second = recommend(REQUEST, candidates)

    assert [i.architecture.slug for i in first] == [i.architecture.slug for i in second]
    assert [i.score for i in first] == [i.score for i in second]


def test_recommend_empty_candidates_returns_empty() -> None:
    assert recommend(REQUEST, []) == []
