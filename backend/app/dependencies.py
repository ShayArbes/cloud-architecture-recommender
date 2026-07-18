"""FastAPI dependency wiring: db → repositories → services (CLAUDE.md §3.1).

Repositories are constructed per-request from the app-scoped Motor client;
routers depend on repository *protocols* so services stay unit-testable.
"""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.db.client import MongoClient, MongoDatabase, get_mongo_client
from app.repositories.architectures import MongoArchitectureRepository
from app.repositories.protocols import ArchitectureReader

SettingsDep = Annotated[Settings, Depends(get_settings)]
MongoClientDep = Annotated[MongoClient, Depends(get_mongo_client)]


def get_database(client: MongoClientDep, settings: SettingsDep) -> MongoDatabase:
    """Return the application's MongoDB database handle."""
    return client[settings.mongo_db_name]


DatabaseDep = Annotated[MongoDatabase, Depends(get_database)]


def get_architecture_reader(database: DatabaseDep) -> ArchitectureReader:
    """Provide an architecture reader backed by MongoDB."""
    return MongoArchitectureRepository(database)


ArchitectureReaderDep = Annotated[ArchitectureReader, Depends(get_architecture_reader)]
