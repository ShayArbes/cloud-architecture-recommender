"""Template-based explanations for recommendations (CLAUDE.md §6.3).

The explanation is generated purely from the match breakdown and score, so it
can never contradict them. It always names the strongest dimension(s) and, when
the fit is imperfect, the weakest — giving the user a readable "why".
"""

from app.schemas.recommendation import RecommendationRequest

# Readable noun phrase per breakdown dimension (keys match the request fields).
_DIMENSION_PHRASES: dict[str, str] = {
    "use_case": "use case",
    "scale": "scale",
    "traffic_pattern": "traffic pattern",
    "latency_sensitivity": "latency sensitivity",
    "processing_style": "processing style",
    "data_intensity": "data intensity",
    "availability_requirement": "availability",
    "ops_preference": "ops model",
    "budget_sensitivity": "cost profile",
}

# Overall-fit qualifier by score band.
_STRONG_FIT = 0.85
_GOOD_FIT = 0.6
_PARTIAL_FIT = 0.4

# Per-dimension thresholds for calling a dimension a strength or a weakness.
_STRENGTH_THRESHOLD = 0.9
_WEAKNESS_THRESHOLD = 0.6

_MAX_STRENGTHS = 3
_MAX_WEAKNESSES = 2


def _qualifier(score: float) -> str:
    if score >= _STRONG_FIT:
        return "Strong fit"
    if score >= _GOOD_FIT:
        return "Good fit"
    if score >= _PARTIAL_FIT:
        return "Partial fit"
    return "Weak fit"


def _readable(value: str) -> str:
    return value.replace("_", " ")


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"


def build_explanation(
    request: RecommendationRequest, breakdown: dict[str, float], score: float
) -> str:
    """Generate a human-readable explanation from the breakdown and score."""
    values = request.model_dump()

    def phrase(dimension: str) -> str:
        return f"{_DIMENSION_PHRASES[dimension]} ({_readable(values[dimension])})"

    by_score = sorted(breakdown.items(), key=lambda item: (item[1], item[0]), reverse=True)

    strengths = [dim for dim, value in by_score if value >= _STRENGTH_THRESHOLD][:_MAX_STRENGTHS]
    # Always name at least the single strongest dimension.
    if not strengths:
        strengths = [by_score[0][0]]

    # Weakest first, so the most important gap is named.
    weaknesses = [dim for dim, value in reversed(by_score) if value < _WEAKNESS_THRESHOLD][
        :_MAX_WEAKNESSES
    ]

    strength_text = f"{_qualifier(score)}: strong match on {_join([phrase(d) for d in strengths])}."
    if weaknesses:
        weakness_text = f" Weaker on {_join([phrase(d) for d in weaknesses])}."
    else:
        weakness_text = " Matches well across the remaining dimensions."
    return strength_text + weakness_text
