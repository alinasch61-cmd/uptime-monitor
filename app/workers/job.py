from typing import Any

import requests
from urllib3.exceptions import NameResolutionError

from app.db.session import SessionLocal
from app.models.check_result import CheckResult
from app.schemas.check_result import NormalizedError, Status
from app.services.check_result import CheckResultRepository
from app.services.endpoint import EndpointRepository


def request_endpoint(url: str, expected_status_code: int) -> dict[str, Any]:
    status: Status = Status.RED
    error_type: NormalizedError | None = None
    elapsed_time: float | None = None
    status_code: int | None = None

    try:
        response: requests.Response = requests.get(
            url=url, allow_redirects=False, timeout=8
        )

        elapsed_time = response.elapsed.total_seconds() * 1000
        status_code = response.status_code

        if response.status_code == expected_status_code:
            status = Status.GREEN
        elif response.status_code // 100 == expected_status_code // 100:
            status = Status.ORANGE
    except requests.exceptions.SSLError:
        error_type = NormalizedError.TLS_ERROR
    except requests.exceptions.Timeout:
        error_type = NormalizedError.TIMEOUT
    except requests.exceptions.ConnectionError as exc:
        if isinstance(exc.__cause__, NameResolutionError):
            error_type = NormalizedError.DNS_ERROR
        else:
            error_type = NormalizedError.CONNECTION_ERROR
    except requests.exceptions.RequestException:
        error_type = NormalizedError.UNKNOWN_ERROR

    return {
        "latency_ms": elapsed_time,
        "status_code": status_code,
        "result_status": status,
        "error_type": error_type,
    }


def run_endpoint_check(endpoint_id: int) -> None:
    with SessionLocal() as session:
        endpoint_repo = EndpointRepository(session=session)
        endpoint = endpoint_repo.get(endpoint_id=endpoint_id)

        if endpoint is None:
            return

        request_result = request_endpoint(
            url=endpoint.url, expected_status_code=endpoint.expected_status_code
        )

        check_res = CheckResult(endpoint_id=endpoint_id, **request_result)
        check_repo = CheckResultRepository(session=session)
        check_repo.create(check_res)
