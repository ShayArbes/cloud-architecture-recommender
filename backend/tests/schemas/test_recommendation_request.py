"""Tests for the recommendation request schema (S3.1)."""

import pytest
from pydantic import ValidationError

from app.models.enums import Scale, UseCase
from app.schemas.recommendation import RecommendationRequest

VALID_PAYLOAD = {
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


def test_valid_payload_parses_to_enums() -> None:
    request = RecommendationRequest.model_validate(VALID_PAYLOAD)

    assert request.use_case is UseCase.ECOMMERCE
    assert request.scale is Scale.MEDIUM


def test_missing_field_raises_validation_error() -> None:
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "scale"}

    with pytest.raises(ValidationError) as exc_info:
        RecommendationRequest.model_validate(payload)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("scale",) and error["type"] == "missing" for error in errors)


def test_invalid_enum_value_raises_validation_error() -> None:
    payload = {**VALID_PAYLOAD, "use_case": "not_a_use_case"}

    with pytest.raises(ValidationError) as exc_info:
        RecommendationRequest.model_validate(payload)

    assert any(error["loc"] == ("use_case",) for error in exc_info.value.errors())


def test_unknown_field_is_rejected() -> None:
    payload = {**VALID_PAYLOAD, "unexpected": "value"}

    with pytest.raises(ValidationError) as exc_info:
        RecommendationRequest.model_validate(payload)

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


def test_all_nine_dimensions_are_required() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RecommendationRequest.model_validate({})

    missing = {error["loc"][0] for error in exc_info.value.errors() if error["type"] == "missing"}
    assert missing == set(VALID_PAYLOAD)
