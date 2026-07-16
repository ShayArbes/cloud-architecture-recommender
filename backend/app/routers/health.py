"""Health/liveness endpoint used by clients and the Docker healthcheck."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.db.client import MongoClient, get_mongo_client, ping
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])

MongoClientDep = Annotated[MongoClient, Depends(get_mongo_client)]


@router.get("/health", response_model=HealthResponse)
async def health(client: MongoClientDep) -> HealthResponse:
    """Report process liveness and MongoDB connectivity.

    Always returns HTTP 200 while the process is alive; MongoDB reachability is
    reported in the ``mongodb`` field so the endpoint doubles as a readiness hint
    without failing liveness probes.
    """
    mongodb_ok = await ping(client)
    return HealthResponse(status="ok", mongodb="connected" if mongodb_ok else "disconnected")
