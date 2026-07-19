"""Tests for the free-text recommendation request schema (bonus, §6.1)."""

import pytest
from pydantic import ValidationError

from app.schemas.recommendation import FlexibleRecommendationRequest

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


def test_valid_payload_keeps_raw_strings() -> None:
    request = FlexibleRecommendationRequest.model_validate(VALID_PAYLOAD)

    # Free text is preserved verbatim; mapping to enums happens downstream.
    assert request.use_case == "ecommerce"
    assert request.ops_preference == "managed_services"


def test_all_nine_dimensions_are_required() -> None:
    with pytest.raises(ValidationError) as exc_info:
        FlexibleRecommendationRequest.model_validate({})

    missing = {error["loc"][0] for error in exc_info.value.errors() if error["type"] == "missing"}
    assert missing == set(VALID_PAYLOAD)


def test_empty_string_is_rejected() -> None:
    payload = {**VALID_PAYLOAD, "scale": ""}

    with pytest.raises(ValidationError) as exc_info:
        FlexibleRecommendationRequest.model_validate(payload)

    assert any(error["loc"] == ("scale",) for error in exc_info.value.errors())


def test_unknown_field_is_rejected() -> None:
    payload = {**VALID_PAYLOAD, "unexpected": "value"}

    with pytest.raises(ValidationError) as exc_info:
        FlexibleRecommendationRequest.model_validate(payload)

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())
