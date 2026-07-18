"""Per-dimension compatibility matrices for scoring (CLAUDE.md §6.3).

Every matrix is an O(1) dict keyed on ``(requested_value, supported_value)``
enum-value pairs. An exact match always scores 1.0; "adjacent" values earn
explicit partial credit; unrelated values score 0.0 (the default).

Two matrix families:
- **Ordinal** dimensions (scale, latency, data intensity, availability, ops
  model, cost) have a natural order; partial credit falls off with distance
  ``{0: 1.0, 1: 0.4, 2: 0.1}`` — matching the CLAUDE.md §6.3 example
  (``scale=medium`` vs supported ``large`` → 0.4).
- **Categorical** dimensions (use case, traffic pattern, processing style)
  have no single order, so adjacency is declared as explicit symmetric pairs.
"""

from collections.abc import Sequence
from enum import StrEnum

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

CompatibilityMatrix = dict[tuple[str, str], float]

# Partial credit for ordinal dimensions by absolute rank distance.
_ORDINAL_DISTANCE_SCORES: dict[int, float] = {0: 1.0, 1: 0.4, 2: 0.1}


def _ordinal_matrix(order: list[StrEnum]) -> CompatibilityMatrix:
    """Build a symmetric distance-based matrix over an ordered enum sequence."""
    matrix: CompatibilityMatrix = {}
    for i, first in enumerate(order):
        for j, second in enumerate(order):
            matrix[(first.value, second.value)] = _ORDINAL_DISTANCE_SCORES.get(abs(i - j), 0.0)
    return matrix


def _categorical_matrix(
    members: list[StrEnum], adjacencies: list[tuple[StrEnum, StrEnum, float]]
) -> CompatibilityMatrix:
    """Build a symmetric matrix: 1.0 on the diagonal, declared pairs, else 0.0."""
    matrix: CompatibilityMatrix = {(member.value, member.value): 1.0 for member in members}
    for first, second, score in adjacencies:
        matrix[(first.value, second.value)] = score
        matrix[(second.value, first.value)] = score
    return matrix


# --- Ordinal dimensions -----------------------------------------------------

SCALE_MATRIX = _ordinal_matrix([Scale.SMALL, Scale.MEDIUM, Scale.LARGE])
LATENCY_MATRIX = _ordinal_matrix(
    [LatencySensitivity.LOW, LatencySensitivity.MEDIUM, LatencySensitivity.HIGH]
)
DATA_INTENSITY_MATRIX = _ordinal_matrix(
    [DataIntensity.LOW, DataIntensity.MEDIUM, DataIntensity.HIGH]
)
AVAILABILITY_MATRIX = _ordinal_matrix(
    [Availability.STANDARD, Availability.HIGH, Availability.CRITICAL]
)
OPS_MODEL_MATRIX = _ordinal_matrix(
    [OpsModel.MANAGED_SERVICES, OpsModel.BALANCED, OpsModel.SELF_MANAGED_OK]
)
COST_PROFILE_MATRIX = _ordinal_matrix([CostProfile.LOW, CostProfile.MEDIUM, CostProfile.HIGH])

# --- Categorical dimensions -------------------------------------------------

USE_CASE_MATRIX = _categorical_matrix(
    list(UseCase),
    [
        (UseCase.WEB_APPLICATION, UseCase.PUBLIC_API, 0.6),
        (UseCase.WEB_APPLICATION, UseCase.ECOMMERCE, 0.6),
        (UseCase.WEB_APPLICATION, UseCase.INTERNAL_TOOL, 0.5),
        (UseCase.ECOMMERCE, UseCase.PUBLIC_API, 0.4),
        (UseCase.PUBLIC_API, UseCase.INTERNAL_TOOL, 0.4),
        (UseCase.REAL_TIME_ANALYTICS, UseCase.EVENT_PROCESSING, 0.6),
        (UseCase.REAL_TIME_ANALYTICS, UseCase.IOT_INGESTION, 0.4),
        (UseCase.EVENT_PROCESSING, UseCase.IOT_INGESTION, 0.6),
        (UseCase.EVENT_PROCESSING, UseCase.BATCH_PROCESSING, 0.4),
        (UseCase.MEDIA_DELIVERY, UseCase.WEB_APPLICATION, 0.4),
        (UseCase.ML_INFERENCE, UseCase.REAL_TIME_ANALYTICS, 0.4),
    ],
)

TRAFFIC_PATTERN_MATRIX = _categorical_matrix(
    list(TrafficPattern),
    [
        (TrafficPattern.BURSTY, TrafficPattern.SPIKY, 0.7),
        (TrafficPattern.BURSTY, TrafficPattern.UNPREDICTABLE, 0.5),
        (TrafficPattern.SPIKY, TrafficPattern.UNPREDICTABLE, 0.5),
        (TrafficPattern.STEADY, TrafficPattern.SCHEDULED, 0.4),
        (TrafficPattern.STEADY, TrafficPattern.BURSTY, 0.3),
    ],
)

PROCESSING_STYLE_MATRIX = _categorical_matrix(
    list(ProcessingStyle),
    [
        (ProcessingStyle.EVENT_DRIVEN, ProcessingStyle.STREAMING, 0.6),
        (ProcessingStyle.BATCH, ProcessingStyle.STREAMING, 0.3),
        (ProcessingStyle.REQUEST_RESPONSE, ProcessingStyle.EVENT_DRIVEN, 0.3),
    ],
)


def score_scalar(matrix: CompatibilityMatrix, requested: StrEnum, supported: StrEnum) -> float:
    """Compatibility of a requested value against a single supported value."""
    return matrix.get((requested.value, supported.value), 0.0)


def score_supported(
    matrix: CompatibilityMatrix, requested: StrEnum, supported: Sequence[StrEnum]
) -> float:
    """Best compatibility of a requested value against a set of supported values.

    An empty support list scores 0.0 — the architecture does not serve the
    dimension at all.
    """
    return max((score_scalar(matrix, requested, value) for value in supported), default=0.0)
