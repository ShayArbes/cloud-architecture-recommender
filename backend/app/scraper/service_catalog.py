"""Catalog of recognizable AWS services for rule-based extraction (S1.2).

A data table owned by the scraper: each entry maps a detection regex to the
service's canonical name and category. Detection runs over the raw HTML
(not just visible text) because AWS pages embed much of their content in
client-rendered JSON.
"""

from dataclasses import dataclass

from app.models.enums import ServiceCategory


@dataclass(frozen=True)
class ServiceDefinition:
    """Canonical name, detection regex fragment, and category for one service."""

    name: str
    pattern: str
    category: ServiceCategory


# Patterns are matched with surrounding word boundaries, case-sensitively —
# AWS service names are proper nouns, and case-sensitivity avoids matching
# lowercase technical tokens (e.g. "s3://" URLs) as service mentions.
SERVICE_CATALOG: tuple[ServiceDefinition, ...] = (
    # Compute
    ServiceDefinition("AWS Lambda", r"Lambda", ServiceCategory.COMPUTE),
    ServiceDefinition("Amazon EC2", r"EC2", ServiceCategory.COMPUTE),
    ServiceDefinition("AWS Fargate", r"Fargate", ServiceCategory.COMPUTE),
    ServiceDefinition("Amazon ECS", r"ECS|Elastic Container Service", ServiceCategory.COMPUTE),
    ServiceDefinition("Amazon EKS", r"EKS|Elastic Kubernetes Service", ServiceCategory.COMPUTE),
    ServiceDefinition("AWS Batch", r"AWS Batch", ServiceCategory.COMPUTE),
    ServiceDefinition("AWS Elastic Beanstalk", r"Elastic Beanstalk", ServiceCategory.COMPUTE),
    # Storage
    ServiceDefinition("Amazon S3", r"Amazon S3|S3", ServiceCategory.STORAGE),
    ServiceDefinition("Amazon EFS", r"EFS|Elastic File System", ServiceCategory.STORAGE),
    ServiceDefinition("Amazon FSx", r"FSx", ServiceCategory.STORAGE),
    ServiceDefinition("Amazon S3 Glacier", r"Glacier", ServiceCategory.STORAGE),
    # Database
    ServiceDefinition("Amazon DynamoDB", r"DynamoDB", ServiceCategory.DATABASE),
    ServiceDefinition("Amazon Aurora", r"Aurora", ServiceCategory.DATABASE),
    ServiceDefinition("Amazon RDS", r"RDS|Relational Database Service", ServiceCategory.DATABASE),
    ServiceDefinition("Amazon ElastiCache", r"ElastiCache", ServiceCategory.DATABASE),
    ServiceDefinition("Amazon DocumentDB", r"DocumentDB", ServiceCategory.DATABASE),
    ServiceDefinition("Amazon Neptune", r"Neptune", ServiceCategory.DATABASE),
    ServiceDefinition("Amazon Timestream", r"Timestream", ServiceCategory.DATABASE),
    # Networking & content delivery
    ServiceDefinition("Amazon API Gateway", r"API Gateway", ServiceCategory.NETWORKING),
    ServiceDefinition("Amazon CloudFront", r"CloudFront", ServiceCategory.NETWORKING),
    ServiceDefinition("Amazon Route 53", r"Route 53", ServiceCategory.NETWORKING),
    ServiceDefinition(
        "Elastic Load Balancing",
        r"Elastic Load Balanc\w+|Application Load Balancer|Network Load Balancer",
        ServiceCategory.NETWORKING,
    ),
    ServiceDefinition("Amazon VPC", r"VPC|Virtual Private Cloud", ServiceCategory.NETWORKING),
    ServiceDefinition("AWS AppSync", r"AppSync", ServiceCategory.NETWORKING),
    ServiceDefinition("AWS Global Accelerator", r"Global Accelerator", ServiceCategory.NETWORKING),
    # Analytics
    ServiceDefinition("Amazon Kinesis", r"Kinesis", ServiceCategory.ANALYTICS),
    ServiceDefinition("Amazon Athena", r"Athena", ServiceCategory.ANALYTICS),
    ServiceDefinition("Amazon EMR", r"EMR", ServiceCategory.ANALYTICS),
    ServiceDefinition("AWS Glue", r"AWS Glue", ServiceCategory.ANALYTICS),
    ServiceDefinition("Amazon QuickSight", r"QuickSight", ServiceCategory.ANALYTICS),
    ServiceDefinition("Amazon OpenSearch Service", r"OpenSearch", ServiceCategory.ANALYTICS),
    ServiceDefinition("Amazon Redshift", r"Redshift", ServiceCategory.ANALYTICS),
    ServiceDefinition(
        "Amazon MSK", r"MSK|Managed Streaming for Apache Kafka", ServiceCategory.ANALYTICS
    ),
    # Integration
    ServiceDefinition("Amazon SQS", r"SQS|Simple Queue Service", ServiceCategory.INTEGRATION),
    ServiceDefinition(
        "Amazon SNS", r"SNS|Simple Notification Service", ServiceCategory.INTEGRATION
    ),
    ServiceDefinition("Amazon EventBridge", r"EventBridge", ServiceCategory.INTEGRATION),
    ServiceDefinition("AWS Step Functions", r"Step Functions", ServiceCategory.INTEGRATION),
    ServiceDefinition("Amazon MQ", r"Amazon MQ", ServiceCategory.INTEGRATION),
    ServiceDefinition("Amazon SES", r"SES|Simple Email Service", ServiceCategory.INTEGRATION),
    # Machine learning
    ServiceDefinition("Amazon SageMaker", r"SageMaker", ServiceCategory.ML),
    ServiceDefinition("Amazon Bedrock", r"Bedrock", ServiceCategory.ML),
    ServiceDefinition("Amazon Rekognition", r"Rekognition", ServiceCategory.ML),
    ServiceDefinition("Amazon Comprehend", r"Comprehend", ServiceCategory.ML),
    ServiceDefinition("Amazon Textract", r"Textract", ServiceCategory.ML),
    ServiceDefinition("Amazon Transcribe", r"Transcribe", ServiceCategory.ML),
    ServiceDefinition("Amazon Polly", r"Polly", ServiceCategory.ML),
    ServiceDefinition("Amazon Lex", r"Amazon Lex", ServiceCategory.ML),
    ServiceDefinition("Amazon Personalize", r"Personalize", ServiceCategory.ML),
    # Security & identity
    ServiceDefinition("AWS IAM", r"IAM|Identity and Access Management", ServiceCategory.SECURITY),
    ServiceDefinition("Amazon Cognito", r"Cognito", ServiceCategory.SECURITY),
    ServiceDefinition("AWS KMS", r"KMS|Key Management Service", ServiceCategory.SECURITY),
    ServiceDefinition("AWS WAF", r"WAF", ServiceCategory.SECURITY),
    ServiceDefinition("AWS Shield", r"AWS Shield", ServiceCategory.SECURITY),
    ServiceDefinition("AWS Secrets Manager", r"Secrets Manager", ServiceCategory.SECURITY),
    ServiceDefinition("Amazon GuardDuty", r"GuardDuty", ServiceCategory.SECURITY),
    # Operations & other
    ServiceDefinition("Amazon CloudWatch", r"CloudWatch", ServiceCategory.OTHER),
    ServiceDefinition("AWS CloudFormation", r"CloudFormation", ServiceCategory.OTHER),
    ServiceDefinition("AWS CloudTrail", r"CloudTrail", ServiceCategory.OTHER),
    ServiceDefinition("AWS X-Ray", r"X-Ray", ServiceCategory.OTHER),
    ServiceDefinition("AWS Systems Manager", r"Systems Manager", ServiceCategory.OTHER),
    ServiceDefinition("AWS IoT Core", r"IoT Core", ServiceCategory.OTHER),
)

# Human-readable default purpose per category — the rules parser cannot infer a
# service's specific role from static HTML; the optional LLM parser (S1.3) can.
CATEGORY_PURPOSES: dict[ServiceCategory, str] = {
    ServiceCategory.COMPUTE: "Runs application compute workloads",
    ServiceCategory.STORAGE: "Stores objects or files used by the workload",
    ServiceCategory.DATABASE: "Persists and serves structured data",
    ServiceCategory.NETWORKING: "Routes, delivers, or secures network traffic",
    ServiceCategory.ANALYTICS: "Processes or analyzes data at scale",
    ServiceCategory.INTEGRATION: "Connects components with messaging or workflows",
    ServiceCategory.ML: "Provides machine-learning capabilities",
    ServiceCategory.SECURITY: "Handles identity, access, or protection",
    ServiceCategory.OTHER: "Supports operations of the architecture",
}
