"""Tests for free-text → enum normalization (recommendation bonus, §6.1)."""

import pytest

from app.core.errors import ValidationError
from app.models.enums import (
    Availability,
    CostProfile,
    OpsModel,
    Scale,
    TrafficPattern,
    UseCase,
)
from app.schemas.recommendation import (
    FlexibleRecommendationRequest,
    RecommendationRequest,
)
from app.services.recommendation.normalization import normalize_request

FLEX_VALID = {
    "use_case": "ecommerce",
    "scale": "medium",
    "traffic_pattern": "bursty",
    "latency_sensitivity": "medium",
    "processing_style": "request_response",
    "data_intensity": "medium",
    "availability_requirement": "high",
    "ops_preference": "managed_services",
    "budget_sensitivity": "medium",
}


def flex(**overrides: str) -> FlexibleRecommendationRequest:
    return FlexibleRecommendationRequest.model_validate({**FLEX_VALID, **overrides})


def test_exact_enum_values_pass_through() -> None:
    result = normalize_request(flex())

    assert isinstance(result, RecommendationRequest)
    assert result.use_case is UseCase.ECOMMERCE
    assert result.availability_requirement is Availability.HIGH


def test_normalization_is_case_and_separator_insensitive() -> None:
    result = normalize_request(
        flex(use_case="E-Commerce", ops_preference="Managed Services", scale="  MEDIUM  ")
    )

    assert result.use_case is UseCase.ECOMMERCE
    assert result.ops_preference is OpsModel.MANAGED_SERVICES
    assert result.scale is Scale.MEDIUM


def test_synonyms_map_to_nearest_enum() -> None:
    result = normalize_request(
        flex(
            use_case="online store",
            ops_preference="serverless",
            scale="big",
            traffic_pattern="spikes",
            budget_sensitivity="cost sensitive",
        )
    )

    assert result.use_case is UseCase.ECOMMERCE
    assert result.ops_preference is OpsModel.MANAGED_SERVICES
    assert result.scale is Scale.LARGE
    assert result.traffic_pattern is TrafficPattern.SPIKY
    assert result.budget_sensitivity is CostProfile.HIGH


def test_normalized_request_equals_strict_parse() -> None:
    assert normalize_request(flex()) == RecommendationRequest.model_validate(FLEX_VALID)


def test_unrecognized_value_raises_validation_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        normalize_request(flex(use_case="teleportation"))

    error = exc_info.value
    assert error.code == "UNRECOGNIZED_REQUIREMENT"
    assert error.status_code == 422
    assert error.details["field"] == "use_case"
    assert error.details["received"] == "teleportation"
    assert "ecommerce" in error.details["allowed"]


@pytest.mark.parametrize("field", sorted(FLEX_VALID))
def test_every_dimension_reports_its_own_field_on_failure(field: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        normalize_request(flex(**{field: "definitely-not-valid"}))

    assert exc_info.value.details["field"] == field
