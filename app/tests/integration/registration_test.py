import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password_hash
from app.models.user import User


def test_register_new_user(client: TestClient, db: Session):
    response = client.post(
        "/auth/register", json={"username": "new_user", "password": "secret_password"}
    )

    assert response.status_code == 201
    user = db.scalars(select(User)).one()
    assert response.json() == {"id": user.id, "username": "new_user"}
    assert user.username == "new_user"
    assert user.password_hash != "secret_password"
    assert verify_password_hash("secret_password", user.password_hash)


def test_register_duplicate_username(client: TestClient, db: Session):
    first_response = client.post(
        "/auth/register", json={"username": "same_user", "password": "first_password"}
    )
    assert first_response.status_code == 201

    response = client.post(
        "/auth/register", json={"username": "same_user", "password": "second_password"}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "A user with this username already exists"}
    user = db.scalars(select(User)).one()
    assert user.id == first_response.json()["id"]
    assert user.username == "same_user"
    assert verify_password_hash("first_password", user.password_hash)


@pytest.mark.parametrize(
    ("username", "password", "invalid_fields"),
    [
        ("", "valid_password", {"username"}),
        ("valid_user", "", {"password"}),
        ("", "", {"username", "password"}),
    ],
    ids=["empty_username", "empty_password", "both_empty"],
)
def test_register_empty_credentials(
    client: TestClient,
    db: Session,
    username: str,
    password: str,
    invalid_fields: set[str],
):
    response = client.post(
        "/auth/register", json={"username": username, "password": password}
    )

    assert response.status_code == 422
    assert {error["loc"][-1] for error in response.json()["detail"]} == invalid_fields
    assert db.scalars(select(User)).all() == []
