from typing import Any

import requests
from urllib3.exceptions import MaxRetryError, NameResolutionError

from app.core.logging import get_logger, log_errors
from app.db.session import SessionLocal
from app.models.check_result import CheckResult
from app.schemas.check_result import NormalizedError, Status
from app.services.check_result import CheckResultRepository
from app.services.endpoint import EndpointRepository

logger = get_logger("job")


def is_dns_error(exc: requests.exceptions.ConnectionError) -> bool:
    if not exc.args:
        return False

    if isinstance(exc.args[0], MaxRetryError):
        return isinstance(exc.args[0].reason, NameResolutionError)

    return False


def classify_status(actual_status_code: int, expected_status_code: int) -> Status:
    if actual_status_code == expected_status_code:
        return Status.GREEN

    if actual_status_code // 100 == expected_status_code // 100:
        return Status.ORANGE

    return Status.RED


def request_endpoint(url: str, expected_status_code: int) -> dict[str, Any]:
    error_type: str | None = None
    elapsed_time: int | None = None
    status_code: int | None = None

    try:
        with requests.get(
            url=url, allow_redirects=False, timeout=8, stream=True
        ) as response:
            elapsed_time = round(response.elapsed.total_seconds() * 1000)
            status_code = response.status_code

    except requests.exceptions.SSLError:
        error_type = NormalizedError.TLS_ERROR.value
    except requests.exceptions.Timeout:
        error_type = NormalizedError.TIMEOUT.value
    except requests.exceptions.ConnectionError as exc:
        if is_dns_error(exc):
            error_type = NormalizedError.DNS_ERROR.value
        else:
            error_type = NormalizedError.CONNECTION_ERROR.value
    except requests.exceptions.RequestException:
        error_type = NormalizedError.UNKNOWN_ERROR.value

    return {
        "latency_ms": elapsed_time,
        "status_code": status_code,
        "result_status": Status.RED
        if status_code is None
        else classify_status(status_code, expected_status_code),
        "error_type": error_type,
    }


@log_errors(logger)
def run_endpoint_check(endpoint_id: int) -> None:
    with SessionLocal() as session:
        endpoint = EndpointRepository(session=session).get(endpoint_id=endpoint_id)

        if endpoint is None:
            return

        endpoint_url = endpoint.url
        expected_status_code = endpoint.expected_status_code

    request_result = request_endpoint(
        url=endpoint_url, expected_status_code=expected_status_code
    )

    with SessionLocal() as session:
        check_res = CheckResult(endpoint_id=endpoint_id, **request_result)
        check_repo = CheckResultRepository(session=session)
        check_repo.create(check_res)

    if request_result["error_type"] is not None:
        logger.error(
            "Check failed for endpoint %s: %s",
            endpoint_id,
            request_result["error_type"],
        )
    else:
        logger.info(
            "Checked endpoint %s: status %s, HTTP %s",
            endpoint_id,
            request_result["result_status"].value,
            request_result["status_code"],
        )
