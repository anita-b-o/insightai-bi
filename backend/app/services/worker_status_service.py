from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.worker_status import WorkerStatus

DASHBOARD_REFRESH_WORKER_NAME = "dashboard_refresh_worker"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _to_iso(value: datetime | None) -> str | None:
    normalized = _normalize_datetime(value)
    if normalized is None:
        return None
    return normalized.isoformat()


def get_or_create_worker_status(db: Session, *, worker_name: str = DASHBOARD_REFRESH_WORKER_NAME) -> WorkerStatus:
    status = db.get(WorkerStatus, worker_name)
    if status is None:
        status = WorkerStatus(worker_name=worker_name)
        db.add(status)
        db.flush()
    return status


def update_worker_status(
    db: Session,
    *,
    worker_name: str = DASHBOARD_REFRESH_WORKER_NAME,
    heartbeat_at: datetime | None = None,
    cycle_at: datetime | None = None,
    error_message: str | None = None,
    processed_count: int | None = None,
) -> WorkerStatus:
    status = get_or_create_worker_status(db, worker_name=worker_name)
    status.last_worker_heartbeat_at = heartbeat_at or _utc_now()
    if cycle_at is not None:
        status.last_worker_cycle_at = cycle_at
    if error_message is not None:
        status.last_worker_error = error_message[:500] or None
    elif cycle_at is not None:
        status.last_worker_error = None
    if processed_count is not None:
        status.last_worker_processed_count = max(0, processed_count)
    db.commit()
    db.refresh(status)
    return status


def get_worker_health_snapshot(
    db: Session,
    *,
    worker_name: str = DASHBOARD_REFRESH_WORKER_NAME,
) -> dict[str, Any]:
    status = db.get(WorkerStatus, worker_name)
    if status is None or status.last_worker_heartbeat_at is None:
        return {
            "status": "degraded",
            "worker_name": worker_name,
            "reason": "No worker heartbeat recorded yet",
            "heartbeat_timeout_seconds": settings.worker_heartbeat_timeout_seconds,
            "last_worker_heartbeat_at": None,
            "last_worker_cycle_at": None,
            "last_worker_error": None,
            "last_worker_processed_count": 0,
            "heartbeat_age_seconds": None,
            "recent_dashboards_processed": 0,
        }

    heartbeat_at = _normalize_datetime(status.last_worker_heartbeat_at)
    cycle_at = _normalize_datetime(status.last_worker_cycle_at)
    heartbeat_age_seconds = int((_utc_now() - heartbeat_at).total_seconds())
    is_stale = heartbeat_age_seconds > settings.worker_heartbeat_timeout_seconds
    has_error = bool(status.last_worker_error)
    worker_status = "degraded" if is_stale or has_error else "healthy"

    return {
        "status": worker_status,
        "worker_name": worker_name,
        "reason": "stale_heartbeat" if is_stale else ("last_cycle_error" if has_error else "ok"),
        "heartbeat_timeout_seconds": settings.worker_heartbeat_timeout_seconds,
        "last_worker_heartbeat_at": _to_iso(heartbeat_at),
        "last_worker_cycle_at": _to_iso(cycle_at),
        "last_worker_error": status.last_worker_error,
        "last_worker_processed_count": status.last_worker_processed_count,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "recent_dashboards_processed": status.last_worker_processed_count,
    }
