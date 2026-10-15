import socket
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.endpoint import Endpoint


@pytest.fixture(autouse=True)
def resolve_test_urls(monkeypatch: pytest.MonkeyPatch):
    def resolve_address(host, port, *, type):
        addresses = {
            "example.com": "93.184.216.34",
            "localhost": "127.0.0.1",
            "127.0.0.1": "127.0.0.1",
            "::1": "::1",
        }
        ip = addresses[host]
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        address = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
        return [(family, type, socket.IPPROTO_TCP, "", address)]

    monkeypatch.setattr(
        "app.schemas.endpoint.socket",
        SimpleNamespace(SOCK_STREAM=socket.SOCK_STREAM, getaddrinfo=resolve_address),
    )


def register_and_log_in(
    client: TestClient, username: str
) -> tuple[int, dict[str, str]]:
    credentials = {"username": username, "password": "secret_password"}
    registration = client.post("/auth/register", json=credentials)
    login = client.post("/auth/login", data=credentials)
    return registration.json()["id"], {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def authenticated_user(client: TestClient) -> tuple[int, dict[str, str]]:
    return register_and_log_in(client, "endpoint_owner")


@pytest.fixture
def endpoint_payload() -> dict[str, str | int]:
    return {
        "url": "https://example.com/health",
        "expected_status_code": 200,
        "check_frequency_seconds": 120,
    }


@pytest.mark.parametrize(
    ("status_code", "frequency"),
    [(200, 300), (200, 120), (100, 120), (599, 120)],
    ids=["typical_values", "minimum_frequency", "minimum_status", "maximum_status"],
)
def test_create_endpoint(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint_payload: dict[str, str | int],
    status_code: int,
    frequency: int,
):
    user_id, headers = authenticated_user
    endpoint_payload.update(
        expected_status_code=status_code, check_frequency_seconds=frequency
    )

    response = client.post("/endpoints/", json=endpoint_payload, headers=headers)

    assert response.status_code == 201
    body = response.json()
    endpoint = db.scalars(select(Endpoint)).one()
    assert body["id"] == endpoint.id
    assert body["user_id"] == endpoint.user_id == user_id
    assert body["url"] == endpoint.url == endpoint_payload["url"]
    assert body["expected_status_code"] == endpoint.expected_status_code == status_code
    assert (
        body["check_frequency_seconds"] == endpoint.check_frequency_seconds == frequency
    )
    assert body["is_paused"] is endpoint.is_paused is False
    assert datetime.fromisoformat(body["created_at"]) == endpoint.created_at
    assert datetime.fromisoformat(body["next_check_at"]) == endpoint.next_check_at


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", ""),
        ("url", "http://localhost/health"),
        ("url", "http://127.0.0.1/health"),
        ("url", "http://[::1]/health"),
        ("check_frequency_seconds", 119),
        ("check_frequency_seconds", 0),
        ("check_frequency_seconds", -1),
        ("expected_status_code", 99),
        ("expected_status_code", 600),
    ],
    ids=[
        "empty_url",
        "localhost",
        "ipv4_loopback",
        "ipv6_loopback",
        "frequency_below_minimum",
        "zero_frequency",
        "negative_frequency",
        "status_below_minimum",
        "status_above_maximum",
    ],
)
def test_create_endpoint_with_invalid_input(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint_payload: dict[str, str | int],
    field: str,
    value: str | int,
):
    _, headers = authenticated_user
    endpoint_payload[field] = value

    response = client.post("/endpoints/", json=endpoint_payload, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"]
    assert db.scalars(select(Endpoint)).all() == []


@pytest.mark.parametrize(
    "field", ["url", "expected_status_code", "check_frequency_seconds"]
)
def test_create_endpoint_requires_all_fields(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint_payload: dict[str, str | int],
    field: str,
):
    _, headers = authenticated_user
    del endpoint_payload[field]

    response = client.post("/endpoints/", json=endpoint_payload, headers=headers)

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", field] and error["type"] == "missing"
        for error in response.json()["detail"]
    )
    assert db.scalars(select(Endpoint)).all() == []


def test_duplicate_endpoint_is_rejected_for_same_user(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint_payload: dict[str, str | int],
):
    user_id, headers = authenticated_user
    first = client.post("/endpoints/", json=endpoint_payload, headers=headers)
    assert first.status_code == 201
    endpoint_payload["check_frequency_seconds"] = 300

    duplicate = client.post("/endpoints/", json=endpoint_payload, headers=headers)

    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "Endpoint with this URL and status code already exists"
    }
    endpoint = db.scalars(select(Endpoint)).one()
    assert endpoint.id == first.json()["id"]
    assert endpoint.user_id == user_id
    assert endpoint.check_frequency_seconds == 120


def test_another_user_can_create_same_endpoint(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint_payload: dict[str, str | int],
):
    first_user_id, first_headers = authenticated_user
    second_user_id, second_headers = register_and_log_in(client, "another_owner")

    first = client.post("/endpoints/", json=endpoint_payload, headers=first_headers)
    second = client.post("/endpoints/", json=endpoint_payload, headers=second_headers)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    endpoints = db.scalars(select(Endpoint).order_by(Endpoint.id)).all()
    assert len(endpoints) == 2
    assert [endpoint.user_id for endpoint in endpoints] == [
        first_user_id,
        second_user_id,
    ]
    assert first.json()["user_id"] == first_user_id
    assert second.json()["user_id"] == second_user_id
    assert all(endpoint.url == endpoint_payload["url"] for endpoint in endpoints)
    assert all(endpoint.expected_status_code == 200 for endpoint in endpoints)


def test_same_user_can_create_same_url_with_different_status(
    client: TestClient,
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    endpoint_payload: dict[str, str | int],
):
    user_id, headers = authenticated_user
    first = client.post("/endpoints/", json=endpoint_payload, headers=headers)
    assert first.status_code == 201
    endpoint_payload["expected_status_code"] = 201

    second = client.post("/endpoints/", json=endpoint_payload, headers=headers)

    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]
    endpoints = db.scalars(select(Endpoint)).all()
    assert len(endpoints) == 2
    assert {endpoint.expected_status_code for endpoint in endpoints} == {200, 201}
    assert all(endpoint.user_id == user_id for endpoint in endpoints)
    assert all(endpoint.url == endpoint_payload["url"] for endpoint in endpoints)
