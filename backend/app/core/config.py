"""Application configuration loaded from the environment (CLAUDE.md §2)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings sourced from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "cloud_arch_db"

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"

    # Comma-separated list of CORS origins (parsed via `cors_origins_list`).
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Scraper politeness knobs (retry policy lives in core/constants.py)
    scraper_max_concurrency: int = 3
    scraper_timeout_seconds: float = 15.0
    scraper_user_agent: str = (
        "CloudArchRecommenderBot/0.1 (+https://github.com/ShayArbes/cloud-architecture-recommender)"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Return the configured CORS origins as a cleaned list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance (one load per process)."""
    return Settings()
