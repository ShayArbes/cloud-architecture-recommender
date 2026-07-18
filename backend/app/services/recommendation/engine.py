"""Deterministic weighted-scoring recommendation engine (CLAUDE.md §6.3).

Pure and I/O-free: it takes a requirements object and a list of candidate
architectures and returns them ranked. Scoring is a single O(n·f) pass — for
each of ``n`` candidates it scores ``f = 9`` dimensions via O(1) matrix lookups
(``compatibility.py``). The same input always yields the same output; the LLM
is never involved in scoring.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.models.architecture import Architecture, ArchitectureCharacteristics
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation import compatibility as compat

# Default number of ranked results returned (configurable per call).
DEFAULT_TOP_N = 3

# Per-dimension weights — the single place they are defined. ``use_case`` is
# weighted highest (CLAUDE.md §6.3); the nine weights sum to 1.0 so the
# weighted sum is already normalized to [0, 1].
DIMENSION_WEIGHTS: dict[str, float] = {
    "use_case": 0.20,
    "scale": 0.12,
    "traffic_pattern": 0.10,
    "latency_sensitivity": 0.12,
    "processing_style": 0.12,
    "data_intensity": 0.08,
    "availability_requirement": 0.12,
    "ops_preference": 0.08,
    "budget_sensitivity": 0.06,
}

_ScoreFn = Callable[[RecommendationRequest, ArchitectureCharacteristics], float]


@dataclass(frozen=True)
class _DimensionSpec:
    """Binds a breakdown key to its weight and its compatibility scorer."""

    name: str
    weight: float
    score: _ScoreFn


# One spec per dimension. List-valued characteristics use ``score_supported``
# (best over the supported set); scalar characteristics use ``score_scalar``.
_DIMENSIONS: tuple[_DimensionSpec, ...] = (
    _DimensionSpec(
        "use_case",
        DIMENSION_WEIGHTS["use_case"],
        lambda r, c: compat.score_supported(compat.USE_CASE_MATRIX, r.use_case, c.use_cases),
    ),
    _DimensionSpec(
        "scale",
        DIMENSION_WEIGHTS["scale"],
        lambda r, c: compat.score_supported(compat.SCALE_MATRIX, r.scale, c.scale),
    ),
    _DimensionSpec(
        "traffic_pattern",
        DIMENSION_WEIGHTS["traffic_pattern"],
        lambda r, c: compat.score_supported(
            compat.TRAFFIC_PATTERN_MATRIX, r.traffic_pattern, c.traffic_patterns
        ),
    ),
    _DimensionSpec(
        "latency_sensitivity",
        DIMENSION_WEIGHTS["latency_sensitivity"],
        lambda r, c: compat.score_scalar(
            compat.LATENCY_MATRIX, r.latency_sensitivity, c.latency_sensitivity
        ),
    ),
    _DimensionSpec(
        "processing_style",
        DIMENSION_WEIGHTS["processing_style"],
        lambda r, c: compat.score_supported(
            compat.PROCESSING_STYLE_MATRIX, r.processing_style, c.processing_styles
        ),
    ),
    _DimensionSpec(
        "data_intensity",
        DIMENSION_WEIGHTS["data_intensity"],
        lambda r, c: compat.score_scalar(
            compat.DATA_INTENSITY_MATRIX, r.data_intensity, c.data_intensity
        ),
    ),
    _DimensionSpec(
        "availability_requirement",
        DIMENSION_WEIGHTS["availability_requirement"],
        lambda r, c: compat.score_scalar(
            compat.AVAILABILITY_MATRIX, r.availability_requirement, c.availability
        ),
    ),
    _DimensionSpec(
        "ops_preference",
        DIMENSION_WEIGHTS["ops_preference"],
        lambda r, c: compat.score_scalar(compat.OPS_MODEL_MATRIX, r.ops_preference, c.ops_model),
    ),
    _DimensionSpec(
        "budget_sensitivity",
        DIMENSION_WEIGHTS["budget_sensitivity"],
        lambda r, c: compat.score_scalar(
            compat.COST_PROFILE_MATRIX, r.budget_sensitivity, c.cost_profile
        ),
    ),
)


@dataclass(frozen=True)
class ScoredArchitecture:
    """An architecture with its overall score and per-dimension breakdown."""

    architecture: Architecture
    score: float
    breakdown: dict[str, float]


def score_architecture(
    request: RecommendationRequest, characteristics: ArchitectureCharacteristics
) -> tuple[float, dict[str, float]]:
    """Return the weighted score in [0, 1] and the per-dimension breakdown."""
    breakdown = {spec.name: spec.score(request, characteristics) for spec in _DIMENSIONS}
    score = sum(DIMENSION_WEIGHTS[name] * value for name, value in breakdown.items())
    # Guard against float drift so the contract's [0, 1] bound always holds.
    return min(1.0, max(0.0, score)), breakdown


def recommend(
    request: RecommendationRequest,
    candidates: list[Architecture],
    top_n: int = DEFAULT_TOP_N,
) -> list[ScoredArchitecture]:
    """Rank ``candidates`` for ``request`` and return the top ``top_n``.

    Sorted by score descending; ties are broken by most recently parsed
    (CLAUDE.md §6.3). A single pass scores each candidate once.
    """
    scored = [
        ScoredArchitecture(candidate, *score_architecture(request, candidate.characteristics))
        for candidate in candidates
    ]
    scored.sort(key=lambda item: (item.score, item.architecture.parsed_at), reverse=True)
    return scored[:top_n]
