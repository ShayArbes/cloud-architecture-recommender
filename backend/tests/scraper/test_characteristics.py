"""Tests for the deterministic characteristics heuristics (S1.3)."""

from app.models.architecture import AwsService
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
from app.scraper.characteristics import extract_characteristics


def service(name: str, category: ServiceCategory) -> AwsService:
    return AwsService(name=name, category=category, purpose="test")


LAMBDA = service("AWS Lambda", ServiceCategory.COMPUTE)
DYNAMODB = service("Amazon DynamoDB", ServiceCategory.DATABASE)
API_GATEWAY = service("Amazon API Gateway", ServiceCategory.NETWORKING)
CLOUDFRONT = service("Amazon CloudFront", ServiceCategory.NETWORKING)
EC2 = service("Amazon EC2", ServiceCategory.COMPUTE)
KINESIS = service("Amazon Kinesis", ServiceCategory.ANALYTICS)
EMR = service("Amazon EMR", ServiceCategory.ANALYTICS)
REDSHIFT = service("Amazon Redshift", ServiceCategory.ANALYTICS)
SQS = service("Amazon SQS", ServiceCategory.INTEGRATION)
SAGEMAKER = service("Amazon SageMaker", ServiceCategory.ML)
ROUTE53 = service("Amazon Route 53", ServiceCategory.NETWORKING)


def test_serverless_web_stack_profile() -> None:
    result = extract_characteristics(
        "Serverless E-Commerce Platform",
        "An ecommerce storefront that absorbs bursts of traffic.",
        [LAMBDA, DYNAMODB, API_GATEWAY],
    )

    assert UseCase.ECOMMERCE in result.use_cases
    assert result.scale == [Scale.SMALL, Scale.MEDIUM, Scale.LARGE]  # serverless is elastic
    assert TrafficPattern.BURSTY in result.traffic_patterns
    assert ProcessingStyle.REQUEST_RESPONSE in result.processing_styles
    assert result.ops_model is OpsModel.MANAGED_SERVICES
    assert result.cost_profile is CostProfile.LOW


def test_streaming_analytics_profile() -> None:
    result = extract_characteristics(
        "Real-Time Analytics Pipeline",
        "Processes clickstream data into dashboards over a data lake.",
        [KINESIS, LAMBDA, DYNAMODB],
    )

    assert UseCase.REAL_TIME_ANALYTICS in result.use_cases
    assert ProcessingStyle.STREAMING in result.processing_styles
    assert result.data_intensity is DataIntensity.HIGH
    assert result.latency_sensitivity is LatencySensitivity.HIGH


def test_batch_heavy_profile_is_latency_tolerant() -> None:
    result = extract_characteristics(
        "Nightly Batch Processing",
        "Runs scheduled batch processing ETL windows.",
        [service("AWS Batch", ServiceCategory.COMPUTE)],
    )

    assert UseCase.BATCH_PROCESSING in result.use_cases
    assert result.processing_styles == [ProcessingStyle.BATCH]
    assert TrafficPattern.SCHEDULED in result.traffic_patterns
    assert result.latency_sensitivity is LatencySensitivity.LOW


def test_ec2_heavy_profile_is_self_managed_and_larger_scale() -> None:
    result = extract_characteristics(
        "Custom Cluster",
        "A compute cluster on virtual machines.",
        [EC2],
    )

    assert result.scale == [Scale.MEDIUM, Scale.LARGE]
    assert result.ops_model is OpsModel.SELF_MANAGED_OK


def test_mixed_stack_is_balanced_ops() -> None:
    result = extract_characteristics(
        "Hybrid Platform",
        "Web workload combining managed and self-managed compute.",
        [EC2, LAMBDA, DYNAMODB, API_GATEWAY],
    )

    assert result.ops_model is OpsModel.BALANCED


def test_expensive_services_raise_cost_profile() -> None:
    result = extract_characteristics(
        "Data Warehouse", "Analytics at scale.", [EMR, REDSHIFT, SAGEMAKER]
    )

    assert result.cost_profile is CostProfile.HIGH


def test_multi_region_text_marks_critical_availability() -> None:
    result = extract_characteristics(
        "Global Platform",
        "A multi-region deployment for disaster recovery.",
        [ROUTE53, CLOUDFRONT],
    )

    assert result.availability is Availability.CRITICAL


def test_route53_without_keywords_marks_high_availability() -> None:
    result = extract_characteristics("DNS Fronted App", "A web app.", [ROUTE53, LAMBDA])

    assert result.availability is Availability.HIGH


def test_ml_category_implies_ml_inference_use_case() -> None:
    result = extract_characteristics("Smart Pipeline", "Predictions.", [SAGEMAKER, SQS])

    assert UseCase.ML_INFERENCE in result.use_cases
    assert ProcessingStyle.EVENT_DRIVEN in result.processing_styles


def test_no_signals_falls_back_to_internal_tool_defaults() -> None:
    result = extract_characteristics("Mystery", "No clues here.", [])

    # AC: the object is complete and enum-valid even with zero signals.
    assert result.use_cases == [UseCase.INTERNAL_TOOL]
    assert result.processing_styles == [ProcessingStyle.REQUEST_RESPONSE]
    assert result.scale
    assert result.traffic_patterns
    assert result.data_intensity is DataIntensity.LOW
    assert result.availability is Availability.STANDARD


def test_extraction_is_deterministic() -> None:
    args = (
        "Serverless E-Commerce Platform",
        "An ecommerce storefront with bursts.",
        [LAMBDA, DYNAMODB, API_GATEWAY, CLOUDFRONT],
    )

    assert extract_characteristics(*args) == extract_characteristics(*args)
