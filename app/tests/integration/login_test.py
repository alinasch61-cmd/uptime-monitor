from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.security import decode_access_token


@pytest.fixture
def registered_user(client: TestClient) -> dict[str, str]:
    credentials = {"username": "registered_user", "password": "secret_password"}
    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201
    return credentials


def test_registered_user_can_log_in(
    client: TestClient, registered_user: dict[str, str]
):
    response = client.post("/auth/login", data=registered_user)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]
    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == registered_user["username"]
    assert payload["exp"] > datetime.now(UTC).timestamp()


@pytest.mark.parametrize(
    ("wrong_username", "wrong_password"),
    [(False, True), (True, False), (True, True)],
    ids=["wrong_password", "wrong_username", "both_wrong"],
)
def test_log_in_with_wrong_credentials(
    client: TestClient,
    registered_user: dict[str, str],
    wrong_username: bool,
    wrong_password: bool,
):
    credentials = registered_user.copy()
    if wrong_username:
        credentials["username"] = "unknown_user"
    if wrong_password:
        credentials["password"] = "wrong_password"

    response = client.post("/auth/login", data=credentials)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert "access_token" not in response.json()
