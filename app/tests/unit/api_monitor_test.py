import socket
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult  # noqa: F401
from app.models.endpoint import Endpoint
from app.models.user import User  # noqa: F401
from app.schemas.endpoint import EndpointCreate
from app.services.endpoint import EndpointRepository

FIXED_NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("endpoint", "expected_next_check_time"),
    [
        (
            Endpoint(
                id=1,
                user_id=1,
                url="https://example.com/1",
                expected_status_code=200,
                check_frequency_seconds=120,
                next_check_at=FIXED_NOW,
                is_paused=False,
            ),
            FIXED_NOW + timedelta(seconds=120),
        ),
        (
            Endpoint(
                id=2,
                user_id=1,
                url="https://example.com/2",
                expected_status_code=200,
                check_frequency_seconds=120,
                next_check_at=FIXED_NOW - timedelta(seconds=120),
                is_paused=False,
            ),
            FIXED_NOW + timedelta(seconds=120),
        ),
        (
            Endpoint(
                id=3,
                user_id=1,
                url="https://example.com/3",
                expected_status_code=200,
                check_frequency_seconds=120,
                next_check_at=FIXED_NOW - timedelta(seconds=600),
                is_paused=False,
            ),
            FIXED_NOW + timedelta(seconds=120),
        ),
        (
            Endpoint(
                id=4,
                user_id=1,
                url="https://example.com/4",
                expected_status_code=200,
                check_frequency_seconds=120,
                next_check_at=FIXED_NOW - timedelta(seconds=70),
                is_paused=False,
            ),
            FIXED_NOW + timedelta(seconds=50),
        ),
        (
            Endpoint(
                id=5,
                user_id=1,
                url="https://example.com/5",
                expected_status_code=200,
                check_frequency_seconds=300,
                next_check_at=FIXED_NOW - timedelta(seconds=700),
                is_paused=False,
            ),
            FIXED_NOW + timedelta(seconds=200),
        ),
        (
            Endpoint(
                id=6,
                user_id=1,
                url="https://example.com/6",
                expected_status_code=200,
                check_frequency_seconds=300,
                next_check_at=FIXED_NOW - timedelta(seconds=1),
                is_paused=False,
            ),
            FIXED_NOW + timedelta(seconds=299),
        ),
    ],
)
def test_next_check_at_calculation(endpoint, expected_next_check_time):
    db_mock = MagicMock(spec=Session)
    repo = EndpointRepository(session=db_mock)

    with patch("app.services.endpoint.datetime") as mocked_datetime:
        mocked_datetime.now.return_value = FIXED_NOW
        assert repo.calculate_next_check_time(endpoint) == expected_next_check_time


@pytest.mark.parametrize(
    ("url", "expected_error_message"),
    [
        ("http://example.com", None),
        ("ftp://example.com", "Only http and https URLs are allowed"),
        ("file:///etc/passwd", "Only http and https URLs are allowed"),
        ("example.com", "Only http and https URLs are allowed"),
        ("//example.com", "Only http and https URLs are allowed"),
        ("http:///path", "Hostname is not provided"),
        ("https://", "Hostname is not provided"),
        ("http://127.0.0.1", "Target resolves to blocked IP"),
        ("http://127.255.255.254", "Target resolves to blocked IP"),
        ("http://[::1]", "Target resolves to blocked IP"),
        ("http://10.0.0.1", "Target resolves to blocked IP"),
        ("http://172.16.0.1", "Target resolves to blocked IP"),
        ("http://192.168.1.1", "Target resolves to blocked IP"),
        ("http://[fc00::1]", "Target resolves to blocked IP"),
        ("http://[fd00::1]", "Target resolves to blocked IP"),
        ("http://169.254.169.254", "Target resolves to blocked IP"),
        ("http://[fe80::1]", "Target resolves to blocked IP"),
        ("http://224.0.0.1", "Target resolves to blocked IP"),
        ("http://[ff02::1]", "Target resolves to blocked IP"),
        ("http://0.0.0.0", "Target resolves to blocked IP"),
        ("http://[::]", "Target resolves to blocked IP"),
        ("http://240.0.0.1", "Target resolves to blocked IP"),
        ("http://nonexistent.example", "Unable to resolve address"),
        ("https://invalid.example", "Unable to resolve address"),
        ("http://unresolvable.test", "Unable to resolve address"),
    ],
)
def test_validate_endpoint_url(url, expected_error_message):
    def resolve_address(host, port, *, type):
        if host in {"nonexistent.example", "invalid.example", "unresolvable.test"}:
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

        ip = "93.184.216.34" if host == "example.com" else host
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        address = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
        return [(family, type, socket.IPPROTO_TCP, "", address)]

    with patch("app.schemas.endpoint.socket.getaddrinfo", side_effect=resolve_address):
        if expected_error_message is None:
            EndpointCreate(
                url=url, check_frequency_seconds=120, expected_status_code=200
            )
        else:
            with pytest.raises(ValueError, match=expected_error_message):
                EndpointCreate(
                    url=url, check_frequency_seconds=120, expected_status_code=200
                )
