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
