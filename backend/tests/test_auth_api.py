from collections.abc import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import auth as auth_routes
from app.db.session import get_db
from app.main import app
from app.models.user import User


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=Session,
    )
    User.__table__.create(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    User.__table__.drop(bind=engine)
    engine.dispose()


def test_register_succeeds_and_login_works(client: TestClient):
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "engineer@example.com",
            "full_name": "Senior Engineer",
            "password": "valid-pass-123",
        },
    )

    assert register_response.status_code == 201
    assert register_response.json()["email"] == "engineer@example.com"

    login_response = client.post(
        "/api/auth/login",
        json={"email": "engineer@example.com", "password": "valid-pass-123"},
    )

    assert login_response.status_code == 200
    body = login_response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_register_rejects_password_longer_than_72_utf8_bytes_before_hashing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    hash_calls = 0
    password = "🙂" * 19

    def fail_if_called(password: str) -> str:
        nonlocal hash_calls
        hash_calls += 1
        raise AssertionError("get_password_hash should not be called")

    monkeypatch.setattr(auth_routes, "get_password_hash", fail_if_called)

    response = client.post(
        "/api/auth/register",
        json={
            "email": "too-long@example.com",
            "full_name": "Senior Engineer",
            "password": password,
        },
    )

    assert len(password) == 19
    assert len(password.encode("utf-8")) == 76
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Value error, Password must be at most 72 bytes when UTF-8 encoded"
    assert hash_calls == 0


def test_register_rejects_password_shorter_than_minimum(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    hash_calls = 0

    def fail_if_called(password: str) -> str:
        nonlocal hash_calls
        hash_calls += 1
        raise AssertionError("get_password_hash should not be called")

    monkeypatch.setattr(auth_routes, "get_password_hash", fail_if_called)

    response = client.post(
        "/api/auth/register",
        json={
            "email": "too-short@example.com",
            "full_name": "Senior Engineer",
            "password": "short",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "String should have at least 8 characters"
    assert hash_calls == 0
