import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.endpoint import Endpoint


@pytest.fixture
def endpoints(
    db: Session,
    authenticated_user: tuple[int, dict[str, str]],
    other_authenticated_user: tuple[int, dict[str, str]],
) -> list[Endpoint]:
    owner_id, _ = authenticated_user
    other_owner_id, _ = other_authenticated_user
    endpoints = [
        Endpoint(
            user_id=user_id,
            url=f"https://example.com/health/{index}",
            expected_status_code=200,
            check_frequency_seconds=120,
        )
        for index, user_id in enumerate([owner_id, owner_id, other_owner_id])
    ]
    db.add_all(endpoints)
    db.commit()
    return endpoints


def test_get_endpoints_returns_only_owned_endpoints(
    client: TestClient,
    authenticated_user: tuple[int, dict[str, str]],
    endpoints: list[Endpoint],
):
    owner_id, headers = authenticated_user

    response = client.get("/endpoints/", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [endpoint.id for endpoint in endpoints[:2]]
    assert all(item["user_id"] == owner_id for item in body)


def test_get_existing_endpoint(
    client: TestClient,
    authenticated_user: tuple[int, dict[str, str]],
    endpoints: list[Endpoint],
):
    owner_id, headers = authenticated_user
    endpoint = endpoints[0]

    response = client.get(f"/endpoints/{endpoint.id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == endpoint.id
    assert body["url"] == endpoint.url
    assert body["user_id"] == owner_id


def test_get_nonexistent_endpoint_returns_404(
    client: TestClient, authenticated_user: tuple[int, dict[str, str]]
):
    _, headers = authenticated_user

    response = client.get("/endpoints/999999", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}


def test_get_another_users_endpoint_returns_404(
    client: TestClient,
    authenticated_user: tuple[int, dict[str, str]],
    endpoints: list[Endpoint],
):
    _, headers = authenticated_user

    response = client.get(f"/endpoints/{endpoints[2].id}", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}
