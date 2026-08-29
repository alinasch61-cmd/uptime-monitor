from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Status(Enum):
    GREEN = "green"
    ORANGE = "orange"
    RED = "red"

class CheckResultResponse(BaseModel):
    checked_at: datetime
    latency_ms: int | None
    status_code: int | None
    result_status: Status | None
    error_type: str | None