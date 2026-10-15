from datetime import timedelta
from io import BytesIO
from unittest.mock import ANY, call, patch

import pytest
import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.check_result import CheckResult
from app.models.endpoint import Endpoint
from app.schemas.check_result import NormalizedError, Status
from app.services.endpoint import EndpointRepository
from app.workers import job, scheduler

URL = "https://example.com/health"


@pytest.fixture(autouse=True)
def worker_sessions(db: Session, monkeypatch: pytest.MonkeyPatch):
    sessions = sessionmaker(
        bind=db.get_bind(),
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    monkeypatch.setattr(job, "SessionLocal", sessions)
    monkeypatch.setattr(scheduler, "SessionLocal", sessions)


@pytest.fixture
def endpoint_ids(
    db: Session, authenticated_user: tuple[int, dict[str, str]]
) -> tuple[int, int]:
    user_id, _ = authenticated_user
    endpoints = [
        Endpoint(
            user_id=user_id,
            url=url,
            expected_status_code=201,
            check_frequency_seconds=120,
        )
        for url in (URL, "https://example.com/other")
    ]
    db.add_all(endpoints)
    db.flush()
    ids = (endpoints[0].id, endpoints[1].id)
    db.commit()
    return ids


def test_scheduler_dispatches_only_due_endpoints(
    db: Session, authenticated_user: tuple[int, dict[str, str]]
):
    user_id, _ = authenticated_user
    now = db.scalar(select(func.now()))
    assert now is not None
    # Due now, several intervals overdue, future, and paused.
    endpoints = [
        Endpoint(
            user_id=user_id,
            url=f"{URL}/{index}",
            expected_status_code=200,
            check_frequency_seconds=frequency,
            next_check_at=now + timedelta(seconds=offset),
            is_paused=paused,
        )
        for index, (offset, frequency, paused) in enumerate(
            [(0, 300, False), (-300, 120, False), (60, 120, False), (-300, 120, True)]
        )
    ]
    db.add_all(endpoints)
    db.flush()
    ids = [endpoint.id for endpoint in endpoints]
    db.commit()

    with (
        patch("app.services.endpoint.datetime") as clock,
        patch.object(scheduler.queue, "enqueue") as enqueue,
    ):
        clock.now.return_value = now
        scheduler.dispatch_checks()

    assert enqueue.call_count == 2
    enqueue.assert_has_calls(
        [call(job.run_endpoint_check, endpoint_id) for endpoint_id in ids[:2]],
        any_order=True,
    )
    db.expire_all()
    for endpoint_id, offset in zip(ids, (300, 60, 60, -300), strict=True):
        endpoint = db.get(Endpoint, endpoint_id)
        assert endpoint is not None
        assert endpoint.next_check_at == now + timedelta(seconds=offset)


@pytest.mark.parametrize(
    ("outcome", "expected_status", "expected_error"),
    [
        (201, Status.GREEN, None),
        (301, Status.RED, None),
        (requests.exceptions.Timeout(), Status.RED, NormalizedError.TIMEOUT),
    ],
    ids=[
        "exact_response",
        "redirect_not_followed",
        "timeout",
    ],
)
def test_job_checks_one_endpoint_and_persists_result(
    db: Session,
    endpoint_ids: tuple[int, int],
    outcome: int | requests.exceptions.RequestException,
    expected_status: Status,
    expected_error: NormalizedError | None,
):
    endpoint_id, _ = endpoint_ids
    response = requests.Response()
    response.raw = BytesIO()
    response.elapsed = timedelta(milliseconds=125)
    if isinstance(outcome, int):
        response.status_code = outcome
        if outcome == 301:
            response.headers["Location"] = "https://example.com/redirected"

    with (
        patch(
            "app.workers.job.requests.get",
            return_value=response,
            side_effect=outcome if isinstance(outcome, Exception) else None,
        ) as get,
        patch.object(
            EndpointRepository, "get", autospec=True, side_effect=EndpointRepository.get
        ) as load_endpoint,
    ):
        job.run_endpoint_check(endpoint_id)

    load_endpoint.assert_called_once_with(ANY, endpoint_id=endpoint_id)
    get.assert_called_once_with(url=URL, allow_redirects=False, timeout=8, stream=True)
    result = db.scalars(select(CheckResult)).one()
    assert result.endpoint_id == endpoint_id
    assert result.result_status == expected_status
    assert result.error_type == (expected_error.value if expected_error else None)
    assert result.status_code == (outcome if isinstance(outcome, int) else None)
    assert result.latency_ms == (125 if isinstance(outcome, int) else None)
    assert result.checked_at is not None


def test_job_exits_when_endpoint_was_deleted(
    db: Session, endpoint_ids: tuple[int, int]
):
    endpoint_id, _ = endpoint_ids
    db.delete(db.get(Endpoint, endpoint_id))
    db.commit()

    with patch("app.workers.job.requests.get") as get:
        job.run_endpoint_check(endpoint_id)

    get.assert_not_called()
    assert db.scalars(select(CheckResult)).all() == []
