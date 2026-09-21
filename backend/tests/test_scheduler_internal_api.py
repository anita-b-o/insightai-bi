from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import internal
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.scheduler_invocation import SchedulerInvocation
from app.models.worker_status import WorkerStatus
from app.services.worker_status_service import get_worker_health_snapshot


@pytest.fixture()
def scheduler_client(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine, tables=[SchedulerInvocation.__table__, WorkerStatus.__table__])
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
    monkeypatch.setattr(settings, "scheduler_secret", "test-scheduler-secret")
    monkeypatch.setattr(settings, "scheduler_request_max_age_seconds", 300)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        db = TestingSession()
        try:
            yield client, db
        finally:
            db.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine, tables=[SchedulerInvocation.__table__, WorkerStatus.__table__])
    engine.dispose()


def _headers(*, invocation_id: str | None = None, timestamp: int | None = None, secret: str = "test-scheduler-secret") -> dict[str, str]:
    actual_timestamp = timestamp if timestamp is not None else int(time.time())
    actual_invocation_id = invocation_id or str(uuid4())
    message = f"{actual_timestamp}.{actual_invocation_id}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return {
        "X-Scheduler-Timestamp": str(actual_timestamp),
        "X-Scheduler-Invocation-Id": actual_invocation_id,
        "X-Scheduler-Signature": signature,
    }


def test_scheduler_endpoint_runs_real_cycle_and_returns_safe_summary(monkeypatch, scheduler_client):
    client, _ = scheduler_client
    monkeypatch.setattr(internal, "run_scheduled_dashboard_refresh_job", lambda db: {"processed": 2})

    response = client.post("/internal/scheduled-refresh/run", headers=_headers(), json={})

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["processed_count"] == 2
    assert set(response.json()) == {"status", "invocation_id", "processed_count"}


@pytest.mark.parametrize("headers", [{}, {"X-Scheduler-Timestamp": "not-a-time"}])
def test_scheduler_endpoint_rejects_missing_or_malformed_auth(scheduler_client, headers):
    client, _ = scheduler_client
    response = client.post("/internal/scheduled-refresh/run", headers=headers)
    assert response.status_code == 401


def test_scheduler_endpoint_rejects_invalid_signature(scheduler_client):
    client, _ = scheduler_client
    response = client.post("/internal/scheduled-refresh/run", headers=_headers(secret="wrong-secret"))
    assert response.status_code == 401


def test_scheduler_endpoint_rejects_expired_timestamp(scheduler_client):
    client, _ = scheduler_client
    response = client.post("/internal/scheduled-refresh/run", headers=_headers(timestamp=int(time.time()) - 301))
    assert response.status_code == 401


def test_scheduler_endpoint_replay_is_idempotent(monkeypatch, scheduler_client):
    client, _ = scheduler_client
    calls = 0

    def cycle(db):
        nonlocal calls
        calls += 1
        return {"processed": 1}

    monkeypatch.setattr(internal, "run_scheduled_dashboard_refresh_job", cycle)
    headers = _headers()
    assert client.post("/internal/scheduled-refresh/run", headers=headers).status_code == 200
    replay = client.post("/internal/scheduled-refresh/run", headers=headers)

    assert replay.status_code == 200
    assert replay.json()["status"] == "already_processed"
    assert calls == 1


def test_scheduler_endpoint_is_disabled_without_secret(monkeypatch, scheduler_client):
    client, _ = scheduler_client
    monkeypatch.setattr(settings, "scheduler_secret", None)
    assert client.post("/internal/scheduled-refresh/run", headers=_headers()).status_code == 503


def test_scheduler_endpoint_records_cycle_failure(monkeypatch, scheduler_client):
    client, db = scheduler_client
    monkeypatch.setattr(internal, "run_scheduled_dashboard_refresh_job", lambda db: (_ for _ in ()).throw(RuntimeError("boom")))
    headers = _headers()

    response = client.post("/internal/scheduled-refresh/run", headers=headers)

    assert response.status_code == 500
    record = db.query(SchedulerInvocation).one()
    assert record.status == "failed"
    assert record.error_message == "Scheduled refresh cycle failed"


def test_worker_health_uses_scheduler_interval_and_grace(monkeypatch, scheduler_client):
    _, db = scheduler_client
    monkeypatch.setattr(settings, "scheduler_expected_interval_seconds", 600)
    monkeypatch.setattr(settings, "scheduler_heartbeat_grace_seconds", 300)
    assert get_worker_health_snapshot(db)["status"] == "degraded"

    db.add(WorkerStatus(worker_name="dashboard_refresh_worker", last_worker_heartbeat_at=datetime.now(timezone.utc) - timedelta(seconds=899)))
    db.commit()
    assert get_worker_health_snapshot(db)["status"] == "healthy"

    status = db.get(WorkerStatus, "dashboard_refresh_worker")
    status.last_worker_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=901)
    db.commit()
    assert get_worker_health_snapshot(db)["status"] == "degraded"


def test_worker_health_is_degraded_for_last_cycle_error(scheduler_client):
    _, db = scheduler_client
    db.add(
        WorkerStatus(
            worker_name="dashboard_refresh_worker",
            last_worker_heartbeat_at=datetime.now(timezone.utc),
            last_worker_error="cycle failed",
        )
    )
    db.commit()
    assert get_worker_health_snapshot(db)["reason"] == "last_cycle_error"
