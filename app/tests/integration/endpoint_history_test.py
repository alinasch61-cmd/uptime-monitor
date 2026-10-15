from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.endpoint import Endpoint
from app.schemas.check_result import Status


@pytest.fixture
def history(
    db: Session, authenticated_user: tuple[int, dict[str, str]]
) -> tuple[int, list[CheckResult]]:
    user_id, _ = authenticated_user
    endpoint = Endpoint(
        user_id=user_id,
        url="https://example.com/health",
        expected_status_code=200,
        check_frequency_seconds=120,
    )
    db.add(endpoint)
    db.flush()
    checked_at = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    checks = [
        CheckResult(
            endpoint_id=endpoint.id,
            checked_at=checked_at - timedelta(minutes=index),
            latency_ms=25,
            status_code=200 if result_status == Status.GREEN else 503,
            result_status=result_status,
            error_type=None,
        )
        for index, result_status in enumerate(
            [Status.GREEN, Status.ORANGE, Status.RED] * 2
        )
    ]
    db.add_all(reversed(checks))
    db.commit()
    return endpoint.id, checks


@pytest.mark.parametrize(
    ("params", "expected_indices"),
    [
        ({}, [0, 1, 2, 3, 4, 5]),
        ({"limit": 2, "offset": 0}, [0, 1]),
        ({"limit": 2, "offset": 2}, [2, 3]),
        ({"limit": 2, "offset": 9}, []),
        ({"filter": "green"}, [0, 3]),
        ({"filter": "orange"}, [1, 4]),
        ({"filter": "red"}, [2, 5]),
        ({"filter": "green", "limit": 1, "offset": 1}, [3]),
    ],
    ids=[
        "newest_first",
        "first_page",
        "second_page",
        "offset_beyond_history",
        "filter_green",
        "filter_orange",
        "filter_red",
        "paginate_filtered_results",
    ],
)
def test_get_history(
    client: TestClient,
    authenticated_user: tuple[int, dict[str, str]],
    history: tuple[int, list[CheckResult]],
    params: dict[str, str | int],
    expected_indices: list[int],
):
    _, headers = authenticated_user
    endpoint_id, checks = history

    response = client.get(
        f"/endpoints/{endpoint_id}/history", params=params, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    expected = [checks[index] for index in expected_indices]
    assert [datetime.fromisoformat(item["checked_at"]) for item in body] == [
        check.checked_at for check in expected
    ]
    assert [item["result_status"] for item in body] == [
        check.result_status.value for check in expected
    ]


def test_get_history_for_nonexistent_endpoint_returns_404(
    client: TestClient, authenticated_user: tuple[int, dict[str, str]]
):
    _, headers = authenticated_user

    response = client.get("/endpoints/999999/history", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}


def test_get_history_for_another_users_endpoint_returns_404(
    client: TestClient,
    other_authenticated_user: tuple[int, dict[str, str]],
    history: tuple[int, list[CheckResult]],
):
    _, headers = other_authenticated_user
    endpoint_id, _ = history

    response = client.get(f"/endpoints/{endpoint_id}/history", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}
