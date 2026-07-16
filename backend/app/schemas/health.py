"""Response schema for the health endpoint."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness payload plus the current MongoDB connectivity status."""

    status: Literal["ok"]
    mongodb: Literal["connected", "disconnected"]
