"""FastAPI dependency wiring: db → repositories → services (CLAUDE.md §3.1).

Repositories are constructed per-request from the app-scoped Motor client;
routers depend on repository *protocols* so services stay unit-testable.
"""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.db.client import MongoClient, MongoDatabase, get_mongo_client
from app.repositories.architectures import MongoArchitectureRepository
from app.repositories.protocols import (
    ArchitectureReader,
    ArchitectureWriter,
    ScrapeJobRecorder,
)
from app.repositories.scrape_jobs import MongoScrapeJobRepository
from app.scraper.pipeline import HttpScrapePipeline, ScrapePipeline
from app.services.recommendation.service import RecommendationService
from app.services.scrape import ScrapeService

SettingsDep = Annotated[Settings, Depends(get_settings)]
MongoClientDep = Annotated[MongoClient, Depends(get_mongo_client)]


def get_database(client: MongoClientDep, settings: SettingsDep) -> MongoDatabase:
    """Return the application's MongoDB database handle."""
    return client[settings.mongo_db_name]


DatabaseDep = Annotated[MongoDatabase, Depends(get_database)]


def get_architecture_reader(database: DatabaseDep) -> ArchitectureReader:
    """Provide an architecture reader backed by MongoDB."""
    return MongoArchitectureRepository(database)


def get_architecture_writer(database: DatabaseDep) -> ArchitectureWriter:
    """Provide an architecture writer backed by MongoDB."""
    return MongoArchitectureRepository(database)


def get_scrape_job_recorder(database: DatabaseDep) -> ScrapeJobRecorder:
    """Provide a scrape-job recorder backed by MongoDB."""
    return MongoScrapeJobRepository(database)


def get_scrape_pipeline(settings: SettingsDep) -> ScrapePipeline:
    """Provide the HTTP scrape pipeline."""
    return HttpScrapePipeline(settings)


ArchitectureReaderDep = Annotated[ArchitectureReader, Depends(get_architecture_reader)]
ArchitectureWriterDep = Annotated[ArchitectureWriter, Depends(get_architecture_writer)]
ScrapeJobRecorderDep = Annotated[ScrapeJobRecorder, Depends(get_scrape_job_recorder)]
ScrapePipelineDep = Annotated[ScrapePipeline, Depends(get_scrape_pipeline)]


def get_scrape_service(
    recorder: ScrapeJobRecorderDep,
    writer: ArchitectureWriterDep,
    pipeline: ScrapePipelineDep,
) -> ScrapeService:
    """Assemble the scrape orchestration service."""
    return ScrapeService(recorder, writer, pipeline)


ScrapeServiceDep = Annotated[ScrapeService, Depends(get_scrape_service)]


def get_recommendation_service(reader: ArchitectureReaderDep) -> RecommendationService:
    """Assemble the recommendation service over the architecture reader."""
    return RecommendationService(reader)


RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]
