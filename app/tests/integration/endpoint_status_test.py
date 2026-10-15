from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.endpoint import Endpoint
from app.schemas.check_result import Status


@pytest.fixture
def endpoint(db: Session, authenticated_user: tuple[int, dict[str, str]]) -> Endpoint:
    user_id, _ = authenticated_user
    endpoint = Endpoint(
        user_id=user_id,
        url="https://example.com/health",
        expected_status_code=200,
        check_frequency_seconds=120,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@pytest.fixture
def latest_check(db: Session, endpoint: Endpoint) -> CheckResult:
    checked_at = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    latest = CheckResult(
        endpoint_id=endpoint.id,
        checked_at=checked_at,
        latency_ms=25,
        status_code=200,
        result_status=Status.GREEN,
        error_type=None,
    )
    older = CheckResult(
        endpoint_id=endpoint.id,
        checked_at=checked_at - timedelta(minutes=5),
        latency_ms=200,
        status_code=503,
        result_status=Status.RED,
        error_type=None,
    )
    # Insert the older check last so selection must use the check timestamp.
    db.add_all([latest, older])
    db.commit()
    db.refresh(latest)
    return latest


def test_get_status_returns_latest_check(
    client: TestClient,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
    latest_check: CheckResult,
):
    _, headers = authenticated_user

    response = client.get(f"/endpoints/{endpoint.id}/status", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert datetime.fromisoformat(body.pop("checked_at")) == latest_check.checked_at
    assert body == {
        "latency_ms": 25,
        "status_code": 200,
        "result_status": "green",
        "error_type": None,
    }


def test_get_status_for_nonexistent_endpoint_returns_404(
    client: TestClient, authenticated_user: tuple[int, dict[str, str]]
):
    _, headers = authenticated_user

    response = client.get("/endpoints/999999/status", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}


def test_get_status_for_unchecked_endpoint_returns_404(
    client: TestClient,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
):
    _, headers = authenticated_user

    response = client.get(f"/endpoints/{endpoint.id}/status", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Status not available"}


def test_get_status_for_another_users_endpoint_returns_404(
    client: TestClient,
    other_authenticated_user: tuple[int, dict[str, str]],
    latest_check: CheckResult,
):
    _, headers = other_authenticated_user

    response = client.get(
        f"/endpoints/{latest_check.endpoint_id}/status", headers=headers
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}
