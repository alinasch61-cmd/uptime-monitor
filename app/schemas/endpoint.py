from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class NormalizedError(Enum):
    TIMEOUT = 0
    DNS_ERROR = 1
    CONNECTION_ERROR = 2
    TLS_ERROR = 3
    UNKNOWN_ERROR = 4


class EndpointUpdate(BaseModel):
    check_frequency_seconds: int | None = Field(ge=120, default=None)
    is_paused: bool | None = None


class EndpointCreate(BaseModel):
    check_frequency_seconds: int = Field(ge=120, default=120)
    is_paused: bool = False
    url: str
    expected_status_code: int = Field(ge=100, le=599, default=200)


class EndpointResponse(EndpointCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    next_check_at: datetime
    created_at: datetime
    user_id: int
