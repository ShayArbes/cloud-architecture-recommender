"""Free-text → enum normalization for the recommendation bonus (CLAUDE.md §6.1).

A deterministic step *in front of* the engine: it maps free-form requirement
strings to the canonical enum values and hands a strict ``RecommendationRequest``
to the same scoring path. The engine is never changed or bypassed — this is the
separate normalization layer §6.1 calls for.

Resolution order per field: exact enum value → separator/case-normalized token
→ curated synonym → otherwise a domain ``ValidationError`` (422) naming the
field, the received value, and the allowed options.
"""

from enum import StrEnum
from typing import TypeVar

from app.core.errors import ValidationError
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
from app.schemas.recommendation import (
    FlexibleRecommendationRequest,
    RecommendationRequest,
)

E = TypeVar("E", bound=StrEnum)


def _canonical(raw: str) -> str:
    """Collapse case and separators so ``E-Commerce`` and ``ecommerce`` match."""
    return raw.strip().lower().replace("-", "_").replace(" ", "_")


def _lookup(enum_cls: type[E], aliases: dict[str, E]) -> dict[str, E]:
    """Build a token→member map from the enum values plus canonicalized aliases."""
    table: dict[str, E] = {member.value: member for member in enum_cls}
    for alias, member in aliases.items():
        table[_canonical(alias)] = member
    return table


# Curated synonyms per dimension. Keys are written naturally and canonicalized
# on load; every enum value already resolves without needing an entry here.
_USE_CASE_ALIASES: dict[str, UseCase] = {
    "web app": UseCase.WEB_APPLICATION,
    "webapp": UseCase.WEB_APPLICATION,
    "website": UseCase.WEB_APPLICATION,
    "web": UseCase.WEB_APPLICATION,
    "api": UseCase.PUBLIC_API,
    "rest api": UseCase.PUBLIC_API,
    "http api": UseCase.PUBLIC_API,
    "e-commerce": UseCase.ECOMMERCE,
    "online store": UseCase.ECOMMERCE,
    "online shop": UseCase.ECOMMERCE,
    "shop": UseCase.ECOMMERCE,
    "store": UseCase.ECOMMERCE,
    "retail": UseCase.ECOMMERCE,
    "storefront": UseCase.ECOMMERCE,
    "analytics": UseCase.REAL_TIME_ANALYTICS,
    "real time analytics": UseCase.REAL_TIME_ANALYTICS,
    "streaming analytics": UseCase.REAL_TIME_ANALYTICS,
    "dashboards": UseCase.REAL_TIME_ANALYTICS,
    "batch": UseCase.BATCH_PROCESSING,
    "etl": UseCase.BATCH_PROCESSING,
    "data pipeline": UseCase.BATCH_PROCESSING,
    "events": UseCase.EVENT_PROCESSING,
    "event driven": UseCase.EVENT_PROCESSING,
    "pub sub": UseCase.EVENT_PROCESSING,
    "media": UseCase.MEDIA_DELIVERY,
    "video": UseCase.MEDIA_DELIVERY,
    "content delivery": UseCase.MEDIA_DELIVERY,
    "cdn": UseCase.MEDIA_DELIVERY,
    "internal": UseCase.INTERNAL_TOOL,
    "back office": UseCase.INTERNAL_TOOL,
    "admin": UseCase.INTERNAL_TOOL,
    "admin portal": UseCase.INTERNAL_TOOL,
    "iot": UseCase.IOT_INGESTION,
    "internet of things": UseCase.IOT_INGESTION,
    "telemetry": UseCase.IOT_INGESTION,
    "sensors": UseCase.IOT_INGESTION,
    "ml": UseCase.ML_INFERENCE,
    "machine learning": UseCase.ML_INFERENCE,
    "inference": UseCase.ML_INFERENCE,
    "ai": UseCase.ML_INFERENCE,
    "llm": UseCase.ML_INFERENCE,
}

_SCALE_ALIASES: dict[str, Scale] = {
    "s": Scale.SMALL,
    "tiny": Scale.SMALL,
    "startup": Scale.SMALL,
    "m": Scale.MEDIUM,
    "mid": Scale.MEDIUM,
    "moderate": Scale.MEDIUM,
    "l": Scale.LARGE,
    "big": Scale.LARGE,
    "huge": Scale.LARGE,
    "enterprise": Scale.LARGE,
}

_TRAFFIC_ALIASES: dict[str, TrafficPattern] = {
    "constant": TrafficPattern.STEADY,
    "stable": TrafficPattern.STEADY,
    "even": TrafficPattern.STEADY,
    "consistent": TrafficPattern.STEADY,
    "burst": TrafficPattern.BURSTY,
    "bursts": TrafficPattern.BURSTY,
    "spike": TrafficPattern.SPIKY,
    "spikes": TrafficPattern.SPIKY,
    "peaky": TrafficPattern.SPIKY,
    "periodic": TrafficPattern.SCHEDULED,
    "cron": TrafficPattern.SCHEDULED,
    "timed": TrafficPattern.SCHEDULED,
    "random": TrafficPattern.UNPREDICTABLE,
    "variable": TrafficPattern.UNPREDICTABLE,
    "erratic": TrafficPattern.UNPREDICTABLE,
    "volatile": TrafficPattern.UNPREDICTABLE,
}

_LATENCY_ALIASES: dict[str, LatencySensitivity] = {
    "relaxed": LatencySensitivity.LOW,
    "tolerant": LatencySensitivity.LOW,
    "not sensitive": LatencySensitivity.LOW,
    "insensitive": LatencySensitivity.LOW,
    "moderate": LatencySensitivity.MEDIUM,
    "mid": LatencySensitivity.MEDIUM,
    "sensitive": LatencySensitivity.HIGH,
    "low latency": LatencySensitivity.HIGH,
    "real time": LatencySensitivity.HIGH,
    "realtime": LatencySensitivity.HIGH,
}

_DATA_INTENSITY_ALIASES: dict[str, DataIntensity] = {
    "light": DataIntensity.LOW,
    "minimal": DataIntensity.LOW,
    "moderate": DataIntensity.MEDIUM,
    "mid": DataIntensity.MEDIUM,
    "heavy": DataIntensity.HIGH,
    "intensive": DataIntensity.HIGH,
    "big data": DataIntensity.HIGH,
    "data heavy": DataIntensity.HIGH,
}

_PROCESSING_ALIASES: dict[str, ProcessingStyle] = {
    "request response": ProcessingStyle.REQUEST_RESPONSE,
    "sync": ProcessingStyle.REQUEST_RESPONSE,
    "synchronous": ProcessingStyle.REQUEST_RESPONSE,
    "rest": ProcessingStyle.REQUEST_RESPONSE,
    "event driven": ProcessingStyle.EVENT_DRIVEN,
    "events": ProcessingStyle.EVENT_DRIVEN,
    "async": ProcessingStyle.EVENT_DRIVEN,
    "asynchronous": ProcessingStyle.EVENT_DRIVEN,
    "batch job": ProcessingStyle.BATCH,
    "batch jobs": ProcessingStyle.BATCH,
    "stream": ProcessingStyle.STREAMING,
    "streams": ProcessingStyle.STREAMING,
}

_AVAILABILITY_ALIASES: dict[str, Availability] = {
    "normal": Availability.STANDARD,
    "basic": Availability.STANDARD,
    "default": Availability.STANDARD,
    "ha": Availability.HIGH,
    "highly available": Availability.HIGH,
    "mission critical": Availability.CRITICAL,
    "always on": Availability.CRITICAL,
    "five nines": Availability.CRITICAL,
}

_OPS_ALIASES: dict[str, OpsModel] = {
    "managed": OpsModel.MANAGED_SERVICES,
    "serverless": OpsModel.MANAGED_SERVICES,
    "fully managed": OpsModel.MANAGED_SERVICES,
    "no ops": OpsModel.MANAGED_SERVICES,
    "noops": OpsModel.MANAGED_SERVICES,
    "hands off": OpsModel.MANAGED_SERVICES,
    "mixed": OpsModel.BALANCED,
    "hybrid": OpsModel.BALANCED,
    "self managed": OpsModel.SELF_MANAGED_OK,
    "diy": OpsModel.SELF_MANAGED_OK,
    "self hosted": OpsModel.SELF_MANAGED_OK,
    "unmanaged": OpsModel.SELF_MANAGED_OK,
    "hands on": OpsModel.SELF_MANAGED_OK,
}

_COST_ALIASES: dict[str, CostProfile] = {
    "insensitive": CostProfile.LOW,
    "flexible": CostProfile.LOW,
    "generous": CostProfile.LOW,
    "moderate": CostProfile.MEDIUM,
    "mid": CostProfile.MEDIUM,
    "tight": CostProfile.HIGH,
    "price sensitive": CostProfile.HIGH,
    "cost sensitive": CostProfile.HIGH,
    "low budget": CostProfile.HIGH,
    "cheap": CostProfile.HIGH,
}

_USE_CASE_LOOKUP = _lookup(UseCase, _USE_CASE_ALIASES)
_SCALE_LOOKUP = _lookup(Scale, _SCALE_ALIASES)
_TRAFFIC_LOOKUP = _lookup(TrafficPattern, _TRAFFIC_ALIASES)
_LATENCY_LOOKUP = _lookup(LatencySensitivity, _LATENCY_ALIASES)
_PROCESSING_LOOKUP = _lookup(ProcessingStyle, _PROCESSING_ALIASES)
_DATA_INTENSITY_LOOKUP = _lookup(DataIntensity, _DATA_INTENSITY_ALIASES)
_AVAILABILITY_LOOKUP = _lookup(Availability, _AVAILABILITY_ALIASES)
_OPS_LOOKUP = _lookup(OpsModel, _OPS_ALIASES)
_COST_LOOKUP = _lookup(CostProfile, _COST_ALIASES)


def _resolve(field: str, raw: str, enum_cls: type[E], table: dict[str, E]) -> E:
    """Resolve one free-text value to its enum, or raise a 422 naming the field."""
    member = table.get(_canonical(raw))
    if member is None:
        raise ValidationError(
            f"Unrecognized value for '{field}'",
            details={
                "field": field,
                "received": raw,
                "allowed": [option.value for option in enum_cls],
            },
            code="UNRECOGNIZED_REQUIREMENT",
        )
    return member


def normalize_request(request: FlexibleRecommendationRequest) -> RecommendationRequest:
    """Map a free-text requirements object to the strict enum-based request.

    Raises:
        ValidationError: if any field cannot be mapped to a known enum value.
    """
    return RecommendationRequest(
        use_case=_resolve("use_case", request.use_case, UseCase, _USE_CASE_LOOKUP),
        scale=_resolve("scale", request.scale, Scale, _SCALE_LOOKUP),
        traffic_pattern=_resolve(
            "traffic_pattern", request.traffic_pattern, TrafficPattern, _TRAFFIC_LOOKUP
        ),
        latency_sensitivity=_resolve(
            "latency_sensitivity",
            request.latency_sensitivity,
            LatencySensitivity,
            _LATENCY_LOOKUP,
        ),
        processing_style=_resolve(
            "processing_style", request.processing_style, ProcessingStyle, _PROCESSING_LOOKUP
        ),
        data_intensity=_resolve(
            "data_intensity", request.data_intensity, DataIntensity, _DATA_INTENSITY_LOOKUP
        ),
        availability_requirement=_resolve(
            "availability_requirement",
            request.availability_requirement,
            Availability,
            _AVAILABILITY_LOOKUP,
        ),
        ops_preference=_resolve("ops_preference", request.ops_preference, OpsModel, _OPS_LOOKUP),
        budget_sensitivity=_resolve(
            "budget_sensitivity", request.budget_sensitivity, CostProfile, _COST_LOOKUP
        ),
    )
