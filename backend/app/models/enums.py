"""Domain enums shared across parsing, storage, and the API (CLAUDE.md §5.1)."""

from enum import StrEnum


class ServiceCategory(StrEnum):
    """Functional category of an AWS service within an architecture."""

    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORKING = "networking"
    ANALYTICS = "analytics"
    INTEGRATION = "integration"
    ML = "ml"
    SECURITY = "security"
    OTHER = "other"


# ---------------------------------------------------------------------------
# The 9 recommendation dimensions (CLAUDE.md §6.1) — defined once, imported
# everywhere: request schema, stored characteristics, compatibility matrices.
# ---------------------------------------------------------------------------


class UseCase(StrEnum):
    """Primary workload type an architecture serves."""

    WEB_APPLICATION = "web_application"
    PUBLIC_API = "public_api"
    ECOMMERCE = "ecommerce"
    REAL_TIME_ANALYTICS = "real_time_analytics"
    BATCH_PROCESSING = "batch_processing"
    EVENT_PROCESSING = "event_processing"
    MEDIA_DELIVERY = "media_delivery"
    INTERNAL_TOOL = "internal_tool"
    IOT_INGESTION = "iot_ingestion"
    ML_INFERENCE = "ml_inference"


class Scale(StrEnum):
    """Workload size the design targets."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class TrafficPattern(StrEnum):
    """Shape of incoming traffic over time."""

    STEADY = "steady"
    BURSTY = "bursty"
    SPIKY = "spiky"
    SCHEDULED = "scheduled"
    UNPREDICTABLE = "unpredictable"


class LatencySensitivity(StrEnum):
    """How sensitive the workload is to response latency."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProcessingStyle(StrEnum):
    """Dominant computation/communication pattern."""

    REQUEST_RESPONSE = "request_response"
    EVENT_DRIVEN = "event_driven"
    BATCH = "batch"
    STREAMING = "streaming"


class DataIntensity(StrEnum):
    """Relative volume/throughput of data the workload handles."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Availability(StrEnum):
    """Required availability tier."""

    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class OpsModel(StrEnum):
    """Preferred operations model."""

    MANAGED_SERVICES = "managed_services"
    BALANCED = "balanced"
    SELF_MANAGED_OK = "self_managed_ok"


class CostProfile(StrEnum):
    """Relative cost tier of running the architecture."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
