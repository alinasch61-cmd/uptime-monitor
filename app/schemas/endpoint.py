import ipaddress
import socket
from datetime import datetime
from enum import Enum
from socket import gaierror
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NormalizedError(Enum):
    TIMEOUT = 0
    DNS_ERROR = 1
    CONNECTION_ERROR = 2
    TLS_ERROR = 3
    UNKNOWN_ERROR = 4


class EndpointUpdate(BaseModel):
    check_frequency_seconds: int | None = Field(ge=120, default=None)
    is_paused: bool | None = None


class EndpointBase(BaseModel):
    check_frequency_seconds: int = Field(ge=120)
    is_paused: bool = False
    url: str = Field(max_length=2000)
    expected_status_code: int = Field(ge=100, le=599)


class EndpointCreate(EndpointBase):
    @model_validator(mode="after")
    def validate_url(self) -> Self:
        parsed_url = urlparse(self.url)

        if parsed_url.scheme not in ("http", "https"):
            raise ValueError("Only http and https URLs are allowed")

        if not parsed_url.hostname:
            raise ValueError("Hostname is not provided")

        try:
            info_lines = socket.getaddrinfo(
                parsed_url.hostname,
                parsed_url.port or (443 if parsed_url.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except gaierror:
            raise ValueError("Unable to resolve address")

        for info in info_lines:
            ip = ipaddress.ip_address(info[4][0])

            if any(
                [
                    ip.is_loopback,
                    ip.is_reserved,
                    ip.is_unspecified,
                    ip.is_private,
                    ip.is_multicast,
                    ip.is_link_local,
                ]
            ):
                raise ValueError(f"Target resolves to blocked IP: {ip}")

        return self


class EndpointResponse(EndpointBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    next_check_at: datetime
    created_at: datetime
    user_id: int
