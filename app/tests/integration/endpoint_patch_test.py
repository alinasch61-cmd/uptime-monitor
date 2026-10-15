from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.endpoint import Endpoint

FIXED_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def authenticated_user(client: TestClient) -> tuple[int, dict[str, str]]:
    credentials = {"username": "patch_owner", "password": "secret_password"}
    registration = client.post("/auth/register", json=credentials)
    login = client.post("/auth/login", data=credentials)
    return registration.json()["id"], {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def endpoint(db: Session, authenticated_user: tuple[int, dict[str, str]]) -> Endpoint:
    user_id, _ = authenticated_user
    endpoint = Endpoint(
        user_id=user_id,
        url="https://example.com/health",
        expected_status_code=200,
        check_frequency_seconds=120,
        is_paused=False,
        next_check_at=FIXED_NOW + timedelta(hours=1),
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


def assert_endpoint_matches(body: dict, endpoint: Endpoint):
    for field in (
        "id",
        "user_id",
        "url",
        "expected_status_code",
        "check_frequency_seconds",
        "is_paused",
    ):
        assert body[field] == getattr(endpoint, field)
    for field in ("created_at", "next_check_at"):
        assert datetime.fromisoformat(body[field]) == getattr(endpoint, field)


def test_patch_nonexistent_endpoint(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
):
    _, headers = authenticated_user

    response = client.patch(
        "/endpoints/999999", json={"is_paused": True}, headers=headers
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}
    assert db.scalars(select(Endpoint)).all() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"check_frequency_seconds": 300},
        {"is_paused": True},
        {"check_frequency_seconds": 300, "is_paused": True},
    ],
    ids=["frequency_only", "pause_only", "both_fields"],
)
def test_patch_endpoint_owned_by_another_user_returns_404(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
    changes: dict,
):
    _, owner_headers = authenticated_user
    original = client.get(f"/endpoints/{endpoint.id}", headers=owner_headers).json()
    credentials = {"username": "another_user", "password": "another_password"}
    client.post("/auth/register", json=credentials)
    login = client.post("/auth/login", data=credentials)
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.patch(
        f"/endpoints/{endpoint.id}", json=changes, headers=other_headers
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}
    db.refresh(endpoint)
    assert_endpoint_matches(original, endpoint)


@pytest.mark.parametrize(
    "changes",
    [
        {"check_frequency_seconds": 300},
        {"is_paused": True},
        {"check_frequency_seconds": 300, "is_paused": True},
    ],
    ids=["frequency_only", "pause_only", "both_fields"],
)
def test_patch_supported_fields(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
    changes: dict,
):
    _, headers = authenticated_user
    original = client.get(f"/endpoints/{endpoint.id}", headers=headers).json()

    response = client.patch(f"/endpoints/{endpoint.id}", json=changes, headers=headers)

    assert response.status_code == 200
    assert response.json() == original | changes
    db.refresh(endpoint)
    assert_endpoint_matches(response.json(), endpoint)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "https://other.example/health"),
        ("expected_status_code", 201),
        ("user_id", 999999),
        ("id", 999999),
        ("next_check_at", "2030-01-01T00:00:00Z"),
        ("created_at", "2030-01-01T00:00:00Z"),
    ],
)
def test_patch_cannot_change_other_fields(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
    field: str,
    value: str | int,
):
    _, headers = authenticated_user
    original = client.get(f"/endpoints/{endpoint.id}", headers=headers).json()

    response = client.patch(
        f"/endpoints/{endpoint.id}",
        json={field: value, "check_frequency_seconds": 300},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == original | {"check_frequency_seconds": 300}
    db.refresh(endpoint)
    assert_endpoint_matches(response.json(), endpoint)


@pytest.mark.parametrize("frequency", [119, 0, -1])
def test_patch_rejects_frequency_below_minimum(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
    frequency: int,
):
    _, headers = authenticated_user
    original = client.get(f"/endpoints/{endpoint.id}", headers=headers).json()

    response = client.patch(
        f"/endpoints/{endpoint.id}",
        json={"check_frequency_seconds": frequency, "is_paused": True},
        headers=headers,
    )

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", "check_frequency_seconds"]
        for error in response.json()["detail"]
    )
    db.refresh(endpoint)
    assert_endpoint_matches(original, endpoint)


@pytest.mark.parametrize("overdue_seconds", [3600, 0], ids=["past", "exactly_now"])
@pytest.mark.parametrize("frequency", [120, 300])
def test_resume_sets_next_check_to_database_now(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
    overdue_seconds: int,
    frequency: int,
):
    _, headers = authenticated_user
    database_now = db.scalar(select(func.now()))
    assert database_now is not None
    endpoint.is_paused = True
    endpoint.next_check_at = database_now - timedelta(seconds=overdue_seconds)
    db.commit()
    original_next_check = endpoint.next_check_at

    response = client.patch(
        f"/endpoints/{endpoint.id}",
        json={"is_paused": False, "check_frequency_seconds": frequency},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["is_paused"] is False
    assert response.json()["check_frequency_seconds"] == frequency
    assert datetime.fromisoformat(response.json()["next_check_at"]) == database_now
    db.refresh(endpoint)
    if overdue_seconds:
        assert endpoint.next_check_at > original_next_check
    assert_endpoint_matches(response.json(), endpoint)


def test_patch_active_endpoint_does_not_reschedule(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint: Endpoint,
):
    _, headers = authenticated_user
    original_next_check = endpoint.next_check_at

    response = client.patch(
        f"/endpoints/{endpoint.id}", json={"is_paused": False}, headers=headers
    )

    assert response.status_code == 200
    db.refresh(endpoint)
    assert endpoint.next_check_at == original_next_check
    assert_endpoint_matches(response.json(), endpoint)
