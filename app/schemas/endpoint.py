from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class NormalizedError(Enum):
    TIMEOUT = 0
    DNS_ERROR = 1
    CONNECTION_ERROR = 2
    TLS_ERROR = 3
    UNKNOWN_ERROR = 4

class EndpointBase(BaseModel):
    check_frequency_seconds: int

class EndpointCreate(EndpointBase):
    url: str
    expected_status_code: int

class EndpointUpdate(EndpointBase):
    is_paused: bool

class EndpointResponse(EndpointCreate):
    id: int
    next_check_at: datetime
    is_paused: bool
    created_at: datetime
    