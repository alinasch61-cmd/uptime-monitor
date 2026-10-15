from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.endpoint import Endpoint
from app.models.user import User
from app.schemas.check_result import Status


@pytest.fixture
def endpoint_history(
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    other_authenticated_user: tuple[int, dict[str, str]],
) -> dict[int, list[int]]:
    owner_id, _ = authenticated_user
    other_owner_id, _ = other_authenticated_user
    history = {}
    for index, user_id in enumerate([owner_id, owner_id, other_owner_id]):
        endpoint = Endpoint(
            user_id=user_id,
            url=f"https://example.com/health/{index}",
            expected_status_code=200,
            check_frequency_seconds=120,
        )
        db.add(endpoint)
        db.flush()
        checks = [
            CheckResult(
                endpoint_id=endpoint.id,
                checked_at=datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
                - timedelta(minutes=offset),
                latency_ms=25,
                status_code=200,
                result_status=Status.GREEN,
                error_type=None,
            )
            for offset in range(2)
        ]
        db.add_all(checks)
        db.flush()
        history[endpoint.id] = [check.id for check in checks]
    db.commit()
    return history


def test_delete_endpoint_cascades_to_check_history(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    other_authenticated_user: tuple[int, dict[str, str]],
    endpoint_history: dict[int, list[int]],
):
    owner_id, headers = authenticated_user
    other_owner_id, _ = other_authenticated_user
    endpoint_ids = list(endpoint_history)
    deleted_id = endpoint_ids[0]
    remaining_ids = set(endpoint_ids[1:])

    response = client.delete(f"/endpoints/{deleted_id}", headers=headers)

    assert response.status_code == 204
    assert set(db.scalars(select(Endpoint.id))) == remaining_ids
    assert set(db.scalars(select(CheckResult.id))) == {
        check_id
        for endpoint_id in remaining_ids
        for check_id in endpoint_history[endpoint_id]
    }
    assert set(db.scalars(select(User.id))) == {owner_id, other_owner_id}


def test_delete_user_cascades_to_endpoints_and_check_history(
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    other_authenticated_user: tuple[int, dict[str, str]],
    endpoint_history: dict[int, list[int]],
):
    owner_id, _ = authenticated_user
    other_owner_id, _ = other_authenticated_user
    other_endpoint_id = list(endpoint_history)[-1]

    # A bulk SQL delete bypasses ORM relationship cascades.
    db.execute(delete(User).where(User.id == owner_id))
    db.commit()

    assert list(db.scalars(select(User.id))) == [other_owner_id]
    assert list(db.scalars(select(Endpoint.id))) == [other_endpoint_id]
    assert set(db.scalars(select(CheckResult.id))) == set(
        endpoint_history[other_endpoint_id]
    )
