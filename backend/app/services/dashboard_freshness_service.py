from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.dashboard import Dashboard


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_refresh_lock_active(dashboard: Dashboard) -> bool:
    if not getattr(dashboard, "refresh_in_progress", False):
        return False
    lock_expires_at = getattr(dashboard, "refresh_lock_expires_at", None)
    if lock_expires_at is None:
        return True
    expires_at = lock_expires_at if lock_expires_at.tzinfo is not None else lock_expires_at.replace(tzinfo=timezone.utc)
    return expires_at > _utc_now()


def compute_next_refresh_at(dashboard: Dashboard) -> datetime | None:
    if not getattr(dashboard, "auto_refresh_enabled", False):
        return None

    interval = getattr(dashboard, "refresh_interval_minutes", None)
    if not isinstance(interval, int) or interval <= 0:
        return None

    last_successful_refresh_at = getattr(dashboard, "last_successful_refresh_at", None)
    if last_successful_refresh_at is None:
        return _utc_now() + timedelta(minutes=interval)

    anchor = (
        last_successful_refresh_at
        if last_successful_refresh_at.tzinfo is not None
        else last_successful_refresh_at.replace(tzinfo=timezone.utc)
    )
    return anchor + timedelta(minutes=interval)


def compute_freshness_status(dashboard: Dashboard) -> str:
    current_status = str(getattr(dashboard, "freshness_status", "") or "")
    last_successful_refresh_at = getattr(dashboard, "last_successful_refresh_at", None)
    next_refresh_at = getattr(dashboard, "next_refresh_at", None)

    if last_successful_refresh_at is None:
        return "failed" if current_status == "failed" else "never_refreshed"

    if current_status == "failed":
        return "failed"
    if current_status == "stale":
        return "stale"

    if next_refresh_at is not None:
        next_due = next_refresh_at if next_refresh_at.tzinfo is not None else next_refresh_at.replace(tzinfo=timezone.utc)
        if next_due <= _utc_now():
            return "stale"

    return "fresh"


def find_dashboards_due_for_refresh(db: Session) -> list[Dashboard]:
    now = _utc_now()
    statement = (
        select(Dashboard)
        .options(joinedload(Dashboard.widgets))
        .where(
            Dashboard.auto_refresh_enabled.is_(True),
            Dashboard.next_refresh_at.is_not(None),
            Dashboard.next_refresh_at <= now,
        )
        .order_by(Dashboard.next_refresh_at.asc(), Dashboard.id.asc())
    )
    dashboards = db.execute(statement).unique().scalars().all()
    return [dashboard for dashboard in dashboards if not is_refresh_lock_active(dashboard)]
