from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.dashboard import Dashboard
from app.services import dashboard_execution_service as refresh_locks


def _db() -> tuple[Session, object]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    Dashboard.__table__.create(bind=engine)
    db = Session(bind=engine)
    db.add(Dashboard(user_id=1, name="Ops", auto_refresh_enabled=True, freshness_status="never_refreshed"))
    db.commit()
    return db, engine


def test_lock_acquisition_blocks_second_owner_and_correct_owner_releases():
    db, engine = _db()
    try:
        first = refresh_locks.try_acquire_dashboard_refresh_lock(db, dashboard_id=1)
        assert first
        assert refresh_locks.try_acquire_dashboard_refresh_lock(db, dashboard_id=1) is None
        assert refresh_locks.release_dashboard_refresh_lock(db, dashboard_id=1, lock_token=first) is True
        assert refresh_locks.try_acquire_dashboard_refresh_lock(db, dashboard_id=1)
    finally:
        db.close()
        Dashboard.__table__.drop(bind=engine)
        engine.dispose()


def test_expired_lock_is_reacquired_and_stale_owner_cannot_release_new_lock(monkeypatch):
    db, engine = _db()
    try:
        now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        monkeypatch.setattr(refresh_locks, "_utc_now", lambda: now)
        first = refresh_locks.try_acquire_dashboard_refresh_lock(db, dashboard_id=1)
        assert first
        monkeypatch.setattr(refresh_locks, "_utc_now", lambda: now + timedelta(seconds=301))
        second = refresh_locks.try_acquire_dashboard_refresh_lock(db, dashboard_id=1)
        assert second and second != first
        assert refresh_locks.release_dashboard_refresh_lock(db, dashboard_id=1, lock_token=first) is False
        dashboard = db.get(Dashboard, 1)
        assert dashboard.refresh_in_progress is True
        assert dashboard.refresh_lock_token == second
        assert refresh_locks.release_dashboard_refresh_lock(db, dashboard_id=1, lock_token=second) is True
    finally:
        db.close()
        Dashboard.__table__.drop(bind=engine)
        engine.dispose()


def test_reconcile_expired_lock_removes_ownership_token(monkeypatch):
    db, engine = _db()
    try:
        now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        monkeypatch.setattr(refresh_locks, "_utc_now", lambda: now)
        assert refresh_locks.try_acquire_dashboard_refresh_lock(db, dashboard_id=1)
        monkeypatch.setattr(refresh_locks, "_utc_now", lambda: now + timedelta(seconds=301))
        refresh_locks.reconcile_expired_refresh_lock(db, dashboard_id=1)
        dashboard = db.get(Dashboard, 1)
        assert dashboard.refresh_in_progress is False
        assert dashboard.refresh_lock_token is None
    finally:
        db.close()
        Dashboard.__table__.drop(bind=engine)
        engine.dispose()


def test_only_current_owner_can_renew_an_unexpired_lock(monkeypatch):
    db, engine = _db()
    try:
        now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        monkeypatch.setattr(refresh_locks, "_utc_now", lambda: now)
        token = refresh_locks.try_acquire_dashboard_refresh_lock(db, dashboard_id=1)
        assert token
        monkeypatch.setattr(refresh_locks, "_utc_now", lambda: now + timedelta(seconds=100))
        assert refresh_locks.renew_dashboard_refresh_lock(db, dashboard_id=1, lock_token=token) is True
        assert refresh_locks.renew_dashboard_refresh_lock(db, dashboard_id=1, lock_token="stale-token") is False
    finally:
        db.close()
        Dashboard.__table__.drop(bind=engine)
        engine.dispose()
