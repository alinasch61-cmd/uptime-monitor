import os
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import settings
from app.db.session import get_db
from app.main import app


@pytest.fixture
def db() -> Generator[Session]:
    engine = create_engine(os.getenv("TEST_DATABASE_URL", settings.database_url))
    # Transactional DDL and savepoints keep application commits isolated from
    # existing data and remove the entire test schema on teardown.
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = f"test_registration_{uuid4().hex}"
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                alembic_config = Config(
                    str(Path(__file__).resolve().parents[3] / "alembic.ini")
                )
                alembic_config.attributes.update(
                    connection=connection,
                    version_table_schema=schema,
                    configure_logger=False,
                )
                command.upgrade(alembic_config, "head")
                with Session(
                    bind=connection, join_transaction_mode="create_savepoint"
                ) as session:
                    yield session
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def client(db: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


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
def other_authenticated_user(client: TestClient) -> tuple[int, dict[str, str]]:
    return register_and_log_in(client, "other_owner")
