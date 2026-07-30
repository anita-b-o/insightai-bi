from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import auth as auth_routes
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.user import User


def register_and_login(client: TestClient, email: str = "engineer@example.com") -> str:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "full_name": "Senior Engineer",
            "password": "valid-pass-123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "valid-pass-123"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


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


def test_current_user_accepts_a_valid_token(client: TestClient):
    token = register_and_login(client)

    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "engineer@example.com"


@pytest.mark.parametrize(
    "token",
    [
        "corrupt-token",
        "header.payload.signature",
        create_access_token(subject="1", expires_delta=timedelta(seconds=-1)),
        create_access_token(subject="not-a-number"),
    ],
)
def test_current_user_rejects_invalid_expired_and_malformed_tokens(client: TestClient, token: str):
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired authentication token"


def test_current_user_rejects_a_deleted_user(client: TestClient):
    token = register_and_login(client)
    override = app.dependency_overrides[get_db]
    db_generator = override()
    db = next(db_generator)
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db_generator.close()

    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_inactive_user_cannot_login_or_restore_a_session(client: TestClient):
    token = register_and_login(client)
    override = app.dependency_overrides[get_db]
    db_generator = override()
    db = next(db_generator)
    try:
        user = db.query(User).filter(User.email == "engineer@example.com").one()
        user.is_active = False
        db.commit()
    finally:
        db_generator.close()

    me_response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    login_response = client.post(
        "/api/auth/login",
        json={"email": "engineer@example.com", "password": "valid-pass-123"},
    )

    assert me_response.status_code == 401
    assert login_response.status_code == 401
