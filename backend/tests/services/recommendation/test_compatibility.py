"""Tests for the per-dimension compatibility matrices (S3.2)."""

from app.models.enums import (
    Availability,
    ProcessingStyle,
    Scale,
    TrafficPattern,
    UseCase,
)
from app.services.recommendation import compatibility as compat


def test_exact_match_scores_one() -> None:
    assert compat.score_scalar(compat.SCALE_MATRIX, Scale.MEDIUM, Scale.MEDIUM) == 1.0
    assert compat.score_scalar(compat.USE_CASE_MATRIX, UseCase.ECOMMERCE, UseCase.ECOMMERCE) == 1.0


def test_ordinal_distance_partial_credit_matches_claude_example() -> None:
    # CLAUDE.md §6.3: requested scale=medium vs supported large → 0.4.
    assert compat.score_scalar(compat.SCALE_MATRIX, Scale.MEDIUM, Scale.LARGE) == 0.4
    # Distance two earns the smallest partial credit.
    assert compat.score_scalar(compat.SCALE_MATRIX, Scale.SMALL, Scale.LARGE) == 0.1


def test_ordinal_matrix_is_symmetric() -> None:
    assert compat.score_scalar(
        compat.AVAILABILITY_MATRIX, Availability.STANDARD, Availability.CRITICAL
    ) == compat.score_scalar(
        compat.AVAILABILITY_MATRIX, Availability.CRITICAL, Availability.STANDARD
    )


def test_categorical_adjacency_is_symmetric_and_partial() -> None:
    forward = compat.score_scalar(
        compat.TRAFFIC_PATTERN_MATRIX, TrafficPattern.BURSTY, TrafficPattern.SPIKY
    )
    backward = compat.score_scalar(
        compat.TRAFFIC_PATTERN_MATRIX, TrafficPattern.SPIKY, TrafficPattern.BURSTY
    )
    assert forward == backward == 0.7


def test_unrelated_categorical_values_score_zero() -> None:
    assert (
        compat.score_scalar(
            compat.PROCESSING_STYLE_MATRIX,
            ProcessingStyle.REQUEST_RESPONSE,
            ProcessingStyle.BATCH,
        )
        == 0.0
    )


def test_score_supported_takes_the_best_match() -> None:
    # medium is exact within the set → 1.0 despite large also being present.
    assert (
        compat.score_supported(
            compat.SCALE_MATRIX, Scale.MEDIUM, [Scale.SMALL, Scale.MEDIUM, Scale.LARGE]
        )
        == 1.0
    )
    # No exact member → best adjacent (small→medium distance 1 = 0.4).
    assert compat.score_supported(compat.SCALE_MATRIX, Scale.SMALL, [Scale.MEDIUM]) == 0.4


def test_score_supported_empty_set_scores_zero() -> None:
    assert compat.score_supported(compat.SCALE_MATRIX, Scale.MEDIUM, []) == 0.0


def test_matrices_are_complete_over_their_enums() -> None:
    # Every ordered pair is present so lookups never fall through to the default
    # unexpectedly for in-domain values.
    for a in Scale:
        for b in Scale:
            assert (a.value, b.value) in compat.SCALE_MATRIX
