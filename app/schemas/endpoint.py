from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NormalizedError(Enum):
    TIMEOUT = 0
    DNS_ERROR = 1
    CONNECTION_ERROR = 2
    TLS_ERROR = 3
    UNKNOWN_ERROR = 4

class EndpointUpdate(BaseModel):
    check_frequency_seconds: int = Field(ge=120)
    is_paused: bool

class EndpointCreate(EndpointUpdate):
    url: str
    expected_status_code: int = Field(ge=100, le=599)

class EndpointResponse(EndpointCreate):
    id: int
    next_check_at: datetime
    created_at: datetime
    