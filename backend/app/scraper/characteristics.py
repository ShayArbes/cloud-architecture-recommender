"""Deterministic heuristics deriving the 9-dimension characteristics (S1.3).

This is the mandatory no-API-key path (CLAUDE.md §2): keyword and
service-category rules map parsed page content onto the recommendation
dimensions. Pure functions — same input always yields the same output.
"""

from app.models.architecture import ArchitectureCharacteristics, AwsService
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

# --- Keyword tables (matched against lowercased title + description) --------

_USE_CASE_KEYWORDS: dict[UseCase, tuple[str, ...]] = {
    UseCase.ECOMMERCE: ("ecommerce", "e-commerce", "retail", "storefront", "shopping"),
    UseCase.REAL_TIME_ANALYTICS: (
        "real-time analytic",
        "real time analytic",
        "clickstream",
        "dashboards",
    ),
    UseCase.BATCH_PROCESSING: ("batch processing", "batch job", "etl "),
    UseCase.EVENT_PROCESSING: ("event-driven", "event driven", "event processing"),
    UseCase.MEDIA_DELIVERY: ("media", "video", "live stream", "content delivery"),
    UseCase.IOT_INGESTION: ("iot", "internet of things", "telemetry", "sensor"),
    UseCase.ML_INFERENCE: (
        "machine learning",
        "inference",
        "generative ai",
        "llm",
        "model training",
    ),
    UseCase.PUBLIC_API: ("public api", "rest api", "api backend"),
    UseCase.INTERNAL_TOOL: ("internal tool", "back office", "admin portal"),
    UseCase.WEB_APPLICATION: ("web application", "website", "web app", "waiting room", "frontend"),
}

_BURSTY_KEYWORDS = ("burst", "spike", "surge", "peak traffic", "waiting room", "flash")
_LOW_LATENCY_KEYWORDS = ("low latency", "low-latency", "real-time", "real time", "millisecond")
_HIGH_DATA_KEYWORDS = ("big data", "petabyte", "terabyte", "data lake", "high volume")
_CRITICAL_KEYWORDS = ("mission-critical", "mission critical", "disaster recovery", "multi-region")

# --- Service-based rule tables ----------------------------------------------

_STREAMING_SERVICES = frozenset({"Amazon Kinesis", "Amazon MSK"})
_BATCH_SERVICES = frozenset({"AWS Batch", "Amazon EMR", "AWS Glue"})
_EVENT_SERVICES = frozenset(
    {"Amazon SQS", "Amazon SNS", "Amazon EventBridge", "AWS Step Functions"}
)
_REQUEST_RESPONSE_SERVICES = frozenset(
    {"Amazon API Gateway", "Elastic Load Balancing", "AWS AppSync", "Amazon CloudFront"}
)
_LATENCY_OPTIMIZED_SERVICES = frozenset(
    {"Amazon CloudFront", "Amazon ElastiCache", "AWS Global Accelerator"}
)
_HIGH_AVAILABILITY_SERVICES = frozenset(
    {"Amazon Route 53", "AWS Global Accelerator", "Elastic Load Balancing"}
)
# Serverless/fully-managed building blocks — drive ops model and elasticity.
_MANAGED_SERVICES = frozenset(
    {
        "AWS Lambda",
        "AWS Fargate",
        "Amazon DynamoDB",
        "Amazon S3",
        "Amazon API Gateway",
        "Amazon SQS",
        "Amazon SNS",
        "Amazon EventBridge",
        "AWS Step Functions",
        "Amazon Aurora",
        "Amazon Bedrock",
    }
)
_SELF_MANAGED_SERVICES = frozenset({"Amazon EC2", "Amazon EKS"})
_EXPENSIVE_SERVICES = frozenset(
    {"Amazon EMR", "Amazon Redshift", "Amazon SageMaker", "Amazon EKS", "Amazon OpenSearch Service"}
)


def extract_characteristics(
    title: str, description: str, services: list[AwsService]
) -> ArchitectureCharacteristics:
    """Derive a complete, enum-valid characteristics object from parsed content."""
    text = f"{title} {description}".lower()
    service_names = {service.name for service in services}
    categories = {service.category for service in services}

    use_cases = _derive_use_cases(text, service_names, categories)
    processing_styles = _derive_processing_styles(service_names)
    is_serverless = bool(service_names & _MANAGED_SERVICES) and not (
        service_names & _SELF_MANAGED_SERVICES
    )

    return ArchitectureCharacteristics(
        use_cases=use_cases,
        scale=_derive_scale(is_serverless, service_names),
        traffic_patterns=_derive_traffic_patterns(text, is_serverless, processing_styles),
        latency_sensitivity=_derive_latency_sensitivity(text, service_names, processing_styles),
        processing_styles=processing_styles,
        data_intensity=_derive_data_intensity(text, categories),
        availability=_derive_availability(text, service_names),
        ops_model=_derive_ops_model(service_names),
        cost_profile=_derive_cost_profile(service_names, is_serverless),
    )


def _derive_use_cases(
    text: str, service_names: set[str], categories: set[ServiceCategory]
) -> list[UseCase]:
    matched = [
        use_case
        for use_case, keywords in _USE_CASE_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    if ServiceCategory.ML in categories and UseCase.ML_INFERENCE not in matched:
        matched.append(UseCase.ML_INFERENCE)
    if "AWS IoT Core" in service_names and UseCase.IOT_INGESTION not in matched:
        matched.append(UseCase.IOT_INGESTION)
    if matched:
        return matched
    # Fallback: anything serving HTTP is a web application; otherwise internal.
    if service_names & _REQUEST_RESPONSE_SERVICES:
        return [UseCase.WEB_APPLICATION]
    return [UseCase.INTERNAL_TOOL]


def _derive_processing_styles(service_names: set[str]) -> list[ProcessingStyle]:
    styles = []
    if service_names & _REQUEST_RESPONSE_SERVICES:
        styles.append(ProcessingStyle.REQUEST_RESPONSE)
    if service_names & _EVENT_SERVICES:
        styles.append(ProcessingStyle.EVENT_DRIVEN)
    if service_names & _STREAMING_SERVICES:
        styles.append(ProcessingStyle.STREAMING)
    if service_names & _BATCH_SERVICES:
        styles.append(ProcessingStyle.BATCH)
    return styles or [ProcessingStyle.REQUEST_RESPONSE]


def _derive_scale(is_serverless: bool, service_names: set[str]) -> list[Scale]:
    if is_serverless:
        # Serverless designs scale elastically across the whole range.
        return [Scale.SMALL, Scale.MEDIUM, Scale.LARGE]
    if service_names & _SELF_MANAGED_SERVICES:
        return [Scale.MEDIUM, Scale.LARGE]
    return [Scale.SMALL, Scale.MEDIUM]


def _derive_traffic_patterns(
    text: str, is_serverless: bool, processing_styles: list[ProcessingStyle]
) -> list[TrafficPattern]:
    patterns = []
    if any(keyword in text for keyword in _BURSTY_KEYWORDS):
        patterns.extend([TrafficPattern.BURSTY, TrafficPattern.SPIKY])
    elif is_serverless:
        patterns.append(TrafficPattern.BURSTY)
    if ProcessingStyle.BATCH in processing_styles:
        patterns.append(TrafficPattern.SCHEDULED)
    if not patterns or ProcessingStyle.REQUEST_RESPONSE in processing_styles:
        patterns.append(TrafficPattern.STEADY)
    return patterns


def _derive_latency_sensitivity(
    text: str, service_names: set[str], processing_styles: list[ProcessingStyle]
) -> LatencySensitivity:
    if (
        any(keyword in text for keyword in _LOW_LATENCY_KEYWORDS)
        or service_names & _LATENCY_OPTIMIZED_SERVICES
    ):
        return LatencySensitivity.HIGH
    if processing_styles == [ProcessingStyle.BATCH]:
        return LatencySensitivity.LOW
    return LatencySensitivity.MEDIUM


def _derive_data_intensity(text: str, categories: set[ServiceCategory]) -> DataIntensity:
    if any(keyword in text for keyword in _HIGH_DATA_KEYWORDS) or (
        ServiceCategory.ANALYTICS in categories
    ):
        return DataIntensity.HIGH
    if categories & {ServiceCategory.DATABASE, ServiceCategory.STORAGE}:
        return DataIntensity.MEDIUM
    return DataIntensity.LOW


def _derive_availability(text: str, service_names: set[str]) -> Availability:
    if any(keyword in text for keyword in _CRITICAL_KEYWORDS):
        return Availability.CRITICAL
    if service_names & _HIGH_AVAILABILITY_SERVICES:
        return Availability.HIGH
    return Availability.STANDARD


def _derive_ops_model(service_names: set[str]) -> OpsModel:
    managed_count = len(service_names & _MANAGED_SERVICES)
    self_managed_count = len(service_names & _SELF_MANAGED_SERVICES)
    if self_managed_count and managed_count <= self_managed_count:
        return OpsModel.SELF_MANAGED_OK
    if self_managed_count:
        return OpsModel.BALANCED
    return OpsModel.MANAGED_SERVICES


def _derive_cost_profile(service_names: set[str], is_serverless: bool) -> CostProfile:
    if len(service_names & _EXPENSIVE_SERVICES) >= 2:
        return CostProfile.HIGH
    if is_serverless and not (service_names & _EXPENSIVE_SERVICES):
        return CostProfile.LOW
    return CostProfile.MEDIUM
