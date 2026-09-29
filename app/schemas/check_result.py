from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class Status(Enum):
    GREEN = "green"
    ORANGE = "orange"
    RED = "red"


class NormalizedError(Enum):
    TIMEOUT = "timeout"
    DNS_ERROR = "dns error"
    CONNECTION_ERROR = "connection error"
    TLS_ERROR = "tls error"
    UNKNOWN_ERROR = "unknown error"


class CheckResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    checked_at: datetime
    latency_ms: int | None
    status_code: int | None
    result_status: Status
    error_type: NormalizedError | None
