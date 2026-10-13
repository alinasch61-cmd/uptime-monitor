from datetime import timedelta
from socket import gaierror
from unittest.mock import MagicMock, patch

import pytest
import requests
from urllib3.connection import HTTPConnection
from urllib3.exceptions import MaxRetryError, NameResolutionError, NewConnectionError

from app.schemas.check_result import NormalizedError, Status
from app.workers.job import classify_status, request_endpoint

URL = "https://example.com/health"


@pytest.mark.parametrize(
    ("exception", "expected_error"),
    [
        (
            requests.exceptions.SSLError("certificate failure"),
            NormalizedError.TLS_ERROR,
        ),
        (requests.exceptions.Timeout(), NormalizedError.TIMEOUT),
        (requests.exceptions.ConnectTimeout(), NormalizedError.TIMEOUT),
        (requests.exceptions.ReadTimeout(), NormalizedError.TIMEOUT),
        (
            requests.exceptions.ConnectionError(
                MaxRetryError(
                    None,
                    URL,
                    NameResolutionError(
                        "example.com", HTTPConnection("example.com"), gaierror()
                    ),
                )
            ),
            NormalizedError.DNS_ERROR,
        ),
        (requests.exceptions.ConnectionError(), NormalizedError.CONNECTION_ERROR),
        (
            requests.exceptions.ConnectionError("connection refused"),
            NormalizedError.CONNECTION_ERROR,
        ),
        (
            requests.exceptions.ConnectionError(
                MaxRetryError(
                    None,
                    URL,
                    NewConnectionError(
                        HTTPConnection("example.com"), "connection refused"
                    ),
                )
            ),
            NormalizedError.CONNECTION_ERROR,
        ),
        (
            requests.exceptions.RequestException("unexpected failure"),
            NormalizedError.UNKNOWN_ERROR,
        ),
    ],
)
def test_request_endpoint_normalizes_http_errors(exception, expected_error):
    with patch("app.workers.job.requests.get", side_effect=exception) as get:
        result = request_endpoint(URL, expected_status_code=200)

    get.assert_called_once_with(url=URL, allow_redirects=False, timeout=8, stream=True)
    assert result == {
        "latency_ms": None,
        "status_code": None,
        "result_status": Status.RED,
        "error_type": expected_error.value,
    }


@pytest.mark.parametrize(
    ("status_code", "expected_status"),
    [(200, Status.GREEN), (201, Status.ORANGE), (503, Status.RED)],
)
def test_request_endpoint_http_response_has_no_transport_error(
    status_code, expected_status
):
    response = MagicMock(spec=requests.Response)
    response.__enter__.return_value = response
    response.status_code = status_code
    response.elapsed = timedelta(microseconds=123600)

    with patch("app.workers.job.requests.get", return_value=response) as get:
        result = request_endpoint(URL, expected_status_code=200)

    get.assert_called_once_with(url=URL, allow_redirects=False, timeout=8, stream=True)
    assert result == {
        "latency_ms": 124,
        "status_code": status_code,
        "result_status": expected_status,
        "error_type": None,
    }
    response.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize(
    ("actual", "expected", "result"),
    [
        (201, 201, Status.GREEN),
        (403, 404, Status.ORANGE),
        (204, 200, Status.ORANGE),
        (401, 404, Status.ORANGE),
        (500, 200, Status.RED),
        (301, 200, Status.RED),
    ],
)
def test_check_classification(actual, expected, result):
    assert classify_status(actual, expected) == result
