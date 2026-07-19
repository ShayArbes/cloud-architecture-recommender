"""Curated seed architectures (CLAUDE.md §5.3 story S5.3).

A small, hand-authored inventory so the app is demonstrable immediately even
when live scraping is blocked. The catalogue is pure data — plain
``ParsedArchitecture`` values with no timestamps — so the seed runner
(:mod:`app.db.seed`) can stamp and upsert them exactly the way the scrape
pipeline persists real results. Values are spread across all nine dimensions so
recommendations return varied, meaningful rankings.
"""

from app.models.architecture import (
    ArchitectureCharacteristics,
    AwsService,
    ParsedArchitecture,
)
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

# Marks documents that originated from this curated set rather than a scrape,
# so they can be re-parsed or purged independently (CLAUDE.md §5.1).
SEED_PARSER_VERSION = "seed-v1"


SEED_ARCHITECTURES: list[ParsedArchitecture] = [
    ParsedArchitecture(
        slug="serverless-ecommerce-platform",
        title="Serverless E-Commerce Platform",
        source_url="https://aws.amazon.com/architecture/serverless-ecommerce-platform",
        description=(
            "A fully managed serverless storefront: API Gateway fronts Lambda "
            "functions backed by DynamoDB, absorbing bursty shopping traffic "
            "without provisioned servers."
        ),
        use_cases=[UseCase.ECOMMERCE, UseCase.WEB_APPLICATION],
        aws_services=[
            AwsService(
                name="Amazon API Gateway",
                category=ServiceCategory.NETWORKING,
                purpose="Routes and throttles client API traffic",
            ),
            AwsService(
                name="AWS Lambda",
                category=ServiceCategory.COMPUTE,
                purpose="Runs checkout and catalogue logic on demand",
            ),
            AwsService(
                name="Amazon DynamoDB",
                category=ServiceCategory.DATABASE,
                purpose="Stores orders and product data at any scale",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.ECOMMERCE, UseCase.WEB_APPLICATION],
            scale=[Scale.SMALL, Scale.MEDIUM],
            traffic_patterns=[TrafficPattern.BURSTY, TrafficPattern.SPIKY],
            latency_sensitivity=LatencySensitivity.MEDIUM,
            processing_styles=[ProcessingStyle.REQUEST_RESPONSE, ProcessingStyle.EVENT_DRIVEN],
            data_intensity=DataIntensity.MEDIUM,
            availability=Availability.HIGH,
            ops_model=OpsModel.MANAGED_SERVICES,
            cost_profile=CostProfile.MEDIUM,
        ),
        diagram_url="https://d1.awsstatic.com/architecture/serverless-ecommerce.png",
        tags=["serverless", "lambda", "dynamodb", "api-gateway"],
        parser_version=SEED_PARSER_VERSION,
    ),
    ParsedArchitecture(
        slug="real-time-streaming-analytics",
        title="Real-Time Streaming Analytics",
        source_url="https://aws.amazon.com/architecture/real-time-streaming-analytics",
        description=(
            "Ingests high-volume event streams through Kinesis, processes them "
            "with managed stream processors, and serves low-latency dashboards "
            "for operational analytics."
        ),
        use_cases=[UseCase.REAL_TIME_ANALYTICS, UseCase.EVENT_PROCESSING],
        aws_services=[
            AwsService(
                name="Amazon Kinesis Data Streams",
                category=ServiceCategory.ANALYTICS,
                purpose="Buffers millions of events per second",
            ),
            AwsService(
                name="Amazon Managed Service for Apache Flink",
                category=ServiceCategory.ANALYTICS,
                purpose="Runs continuous stream processing queries",
            ),
            AwsService(
                name="Amazon OpenSearch Service",
                category=ServiceCategory.ANALYTICS,
                purpose="Indexes results for real-time dashboards",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.REAL_TIME_ANALYTICS, UseCase.EVENT_PROCESSING],
            scale=[Scale.MEDIUM, Scale.LARGE],
            traffic_patterns=[TrafficPattern.UNPREDICTABLE, TrafficPattern.SPIKY],
            latency_sensitivity=LatencySensitivity.HIGH,
            processing_styles=[ProcessingStyle.STREAMING],
            data_intensity=DataIntensity.HIGH,
            availability=Availability.HIGH,
            ops_model=OpsModel.BALANCED,
            cost_profile=CostProfile.HIGH,
        ),
        diagram_url="https://d1.awsstatic.com/architecture/streaming-analytics.png",
        tags=["streaming", "kinesis", "flink", "analytics"],
        parser_version=SEED_PARSER_VERSION,
    ),
    ParsedArchitecture(
        slug="scheduled-batch-data-pipeline",
        title="Scheduled Batch Data Pipeline",
        source_url="https://aws.amazon.com/architecture/scheduled-batch-data-pipeline",
        description=(
            "A nightly ETL pipeline: AWS Batch crunches large datasets on a "
            "schedule and lands curated tables in S3 for downstream querying, "
            "optimising cost over latency."
        ),
        use_cases=[UseCase.BATCH_PROCESSING],
        aws_services=[
            AwsService(
                name="AWS Batch",
                category=ServiceCategory.COMPUTE,
                purpose="Runs containerised batch jobs on managed compute",
            ),
            AwsService(
                name="Amazon S3",
                category=ServiceCategory.STORAGE,
                purpose="Stores raw and curated datasets cheaply",
            ),
            AwsService(
                name="AWS Step Functions",
                category=ServiceCategory.INTEGRATION,
                purpose="Orchestrates multi-stage batch workflows",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.BATCH_PROCESSING],
            scale=[Scale.MEDIUM, Scale.LARGE],
            traffic_patterns=[TrafficPattern.SCHEDULED],
            latency_sensitivity=LatencySensitivity.LOW,
            processing_styles=[ProcessingStyle.BATCH],
            data_intensity=DataIntensity.HIGH,
            availability=Availability.STANDARD,
            ops_model=OpsModel.SELF_MANAGED_OK,
            cost_profile=CostProfile.LOW,
        ),
        diagram_url=None,
        tags=["batch", "etl", "s3", "step-functions"],
        parser_version=SEED_PARSER_VERSION,
    ),
    ParsedArchitecture(
        slug="containerised-public-api",
        title="Containerised Public REST API",
        source_url="https://aws.amazon.com/architecture/containerised-public-api",
        description=(
            "A highly available public API on ECS Fargate behind an Application "
            "Load Balancer, with Aurora for transactional data — built for "
            "steady, latency-sensitive request/response traffic."
        ),
        use_cases=[UseCase.PUBLIC_API, UseCase.WEB_APPLICATION],
        aws_services=[
            AwsService(
                name="Application Load Balancer",
                category=ServiceCategory.NETWORKING,
                purpose="Distributes requests across container tasks",
            ),
            AwsService(
                name="Amazon ECS on AWS Fargate",
                category=ServiceCategory.COMPUTE,
                purpose="Runs the API containers without managing servers",
            ),
            AwsService(
                name="Amazon Aurora",
                category=ServiceCategory.DATABASE,
                purpose="Serves transactional reads and writes with HA",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.PUBLIC_API, UseCase.WEB_APPLICATION],
            scale=[Scale.MEDIUM, Scale.LARGE],
            traffic_patterns=[TrafficPattern.STEADY, TrafficPattern.BURSTY],
            latency_sensitivity=LatencySensitivity.HIGH,
            processing_styles=[ProcessingStyle.REQUEST_RESPONSE],
            data_intensity=DataIntensity.MEDIUM,
            availability=Availability.CRITICAL,
            ops_model=OpsModel.BALANCED,
            cost_profile=CostProfile.MEDIUM,
        ),
        diagram_url="https://d1.awsstatic.com/architecture/public-api-fargate.png",
        tags=["containers", "ecs", "fargate", "aurora", "api"],
        parser_version=SEED_PARSER_VERSION,
    ),
    ParsedArchitecture(
        slug="global-media-streaming-delivery",
        title="Global Media Streaming & Delivery",
        source_url="https://aws.amazon.com/architecture/global-media-streaming-delivery",
        description=(
            "Transcodes and delivers video globally: MediaConvert prepares "
            "renditions stored in S3 and served through CloudFront for "
            "low-latency, high-throughput playback."
        ),
        use_cases=[UseCase.MEDIA_DELIVERY],
        aws_services=[
            AwsService(
                name="Amazon CloudFront",
                category=ServiceCategory.NETWORKING,
                purpose="Caches and streams media close to viewers",
            ),
            AwsService(
                name="AWS Elemental MediaConvert",
                category=ServiceCategory.OTHER,
                purpose="Transcodes source video into adaptive renditions",
            ),
            AwsService(
                name="Amazon S3",
                category=ServiceCategory.STORAGE,
                purpose="Stores source and packaged media assets",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.MEDIA_DELIVERY],
            scale=[Scale.LARGE],
            traffic_patterns=[TrafficPattern.SPIKY, TrafficPattern.BURSTY],
            latency_sensitivity=LatencySensitivity.MEDIUM,
            processing_styles=[ProcessingStyle.STREAMING, ProcessingStyle.REQUEST_RESPONSE],
            data_intensity=DataIntensity.HIGH,
            availability=Availability.HIGH,
            ops_model=OpsModel.MANAGED_SERVICES,
            cost_profile=CostProfile.HIGH,
        ),
        diagram_url="https://d1.awsstatic.com/architecture/media-delivery.png",
        tags=["media", "cloudfront", "mediaconvert", "video"],
        parser_version=SEED_PARSER_VERSION,
    ),
    ParsedArchitecture(
        slug="iot-telemetry-ingestion",
        title="IoT Telemetry Ingestion",
        source_url="https://aws.amazon.com/architecture/iot-telemetry-ingestion",
        description=(
            "Millions of devices publish telemetry through AWS IoT Core, which "
            "routes events to a serverless pipeline for storage and alerting on "
            "unpredictable, always-on traffic."
        ),
        use_cases=[UseCase.IOT_INGESTION, UseCase.EVENT_PROCESSING],
        aws_services=[
            AwsService(
                name="AWS IoT Core",
                category=ServiceCategory.INTEGRATION,
                purpose="Terminates device connections and routes messages",
            ),
            AwsService(
                name="Amazon Kinesis Data Firehose",
                category=ServiceCategory.ANALYTICS,
                purpose="Batches telemetry into durable storage",
            ),
            AwsService(
                name="Amazon Timestream",
                category=ServiceCategory.DATABASE,
                purpose="Stores time-series telemetry for querying",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.IOT_INGESTION, UseCase.EVENT_PROCESSING],
            scale=[Scale.MEDIUM, Scale.LARGE],
            traffic_patterns=[TrafficPattern.UNPREDICTABLE, TrafficPattern.STEADY],
            latency_sensitivity=LatencySensitivity.MEDIUM,
            processing_styles=[ProcessingStyle.EVENT_DRIVEN, ProcessingStyle.STREAMING],
            data_intensity=DataIntensity.HIGH,
            availability=Availability.HIGH,
            ops_model=OpsModel.MANAGED_SERVICES,
            cost_profile=CostProfile.MEDIUM,
        ),
        diagram_url=None,
        tags=["iot", "iot-core", "kinesis", "timestream"],
        parser_version=SEED_PARSER_VERSION,
    ),
    ParsedArchitecture(
        slug="internal-admin-dashboard",
        title="Internal Admin Dashboard",
        source_url="https://aws.amazon.com/architecture/internal-admin-dashboard",
        description=(
            "A lightweight internal tool: Amplify hosts the frontend and a small "
            "Lambda + DynamoDB backend serves a handful of operators, favouring "
            "low cost and minimal operations."
        ),
        use_cases=[UseCase.INTERNAL_TOOL, UseCase.WEB_APPLICATION],
        aws_services=[
            AwsService(
                name="AWS Amplify Hosting",
                category=ServiceCategory.NETWORKING,
                purpose="Hosts and deploys the dashboard frontend",
            ),
            AwsService(
                name="AWS Lambda",
                category=ServiceCategory.COMPUTE,
                purpose="Serves the admin API on demand",
            ),
            AwsService(
                name="Amazon DynamoDB",
                category=ServiceCategory.DATABASE,
                purpose="Stores configuration and audit records",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.INTERNAL_TOOL, UseCase.WEB_APPLICATION],
            scale=[Scale.SMALL],
            traffic_patterns=[TrafficPattern.STEADY],
            latency_sensitivity=LatencySensitivity.LOW,
            processing_styles=[ProcessingStyle.REQUEST_RESPONSE],
            data_intensity=DataIntensity.LOW,
            availability=Availability.STANDARD,
            ops_model=OpsModel.MANAGED_SERVICES,
            cost_profile=CostProfile.LOW,
        ),
        diagram_url=None,
        tags=["internal-tool", "amplify", "lambda", "dynamodb"],
        parser_version=SEED_PARSER_VERSION,
    ),
    ParsedArchitecture(
        slug="ml-inference-api",
        title="Real-Time ML Inference API",
        source_url="https://aws.amazon.com/architecture/ml-inference-api",
        description=(
            "Serves low-latency model predictions from SageMaker endpoints "
            "behind API Gateway, scaling with bursty inference demand for "
            "latency-sensitive applications."
        ),
        use_cases=[UseCase.ML_INFERENCE, UseCase.PUBLIC_API],
        aws_services=[
            AwsService(
                name="Amazon API Gateway",
                category=ServiceCategory.NETWORKING,
                purpose="Exposes the inference endpoint to clients",
            ),
            AwsService(
                name="Amazon SageMaker Endpoints",
                category=ServiceCategory.ML,
                purpose="Hosts models for real-time inference",
            ),
            AwsService(
                name="Amazon ElastiCache",
                category=ServiceCategory.DATABASE,
                purpose="Caches frequent predictions to cut latency",
            ),
        ],
        characteristics=ArchitectureCharacteristics(
            use_cases=[UseCase.ML_INFERENCE, UseCase.PUBLIC_API],
            scale=[Scale.MEDIUM],
            traffic_patterns=[TrafficPattern.BURSTY],
            latency_sensitivity=LatencySensitivity.HIGH,
            processing_styles=[ProcessingStyle.REQUEST_RESPONSE, ProcessingStyle.EVENT_DRIVEN],
            data_intensity=DataIntensity.MEDIUM,
            availability=Availability.HIGH,
            ops_model=OpsModel.BALANCED,
            cost_profile=CostProfile.HIGH,
        ),
        diagram_url="https://d1.awsstatic.com/architecture/ml-inference.png",
        tags=["ml", "sagemaker", "inference", "api-gateway"],
        parser_version=SEED_PARSER_VERSION,
    ),
]
