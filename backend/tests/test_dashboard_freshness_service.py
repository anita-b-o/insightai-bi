from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.db.base import Base  # noqa: F401
from app.services import dashboard_freshness_service


def _dashboard(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "id": 3,
        "auto_refresh_enabled": False,
        "refresh_in_progress": False,
        "refresh_interval_minutes": None,
        "last_successful_refresh_at": None,
        "next_refresh_at": None,
        "freshness_status": "never_refreshed",
        "widgets": [],
        "updated_at": now,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_new_dashboard_defaults_to_never_refreshed():
    dashboard = _dashboard()

    assert dashboard_freshness_service.compute_freshness_status(dashboard) == "never_refreshed"


def test_dashboard_with_future_next_refresh_is_fresh():
    now = datetime.now(timezone.utc)
    dashboard = _dashboard(
        auto_refresh_enabled=True,
        refresh_interval_minutes=30,
        last_successful_refresh_at=now,
        next_refresh_at=now + timedelta(minutes=30),
        freshness_status="fresh",
    )

    assert dashboard_freshness_service.compute_freshness_status(dashboard) == "fresh"


def test_dashboard_with_past_next_refresh_is_stale():
    now = datetime.now(timezone.utc)
    dashboard = _dashboard(
        auto_refresh_enabled=True,
        refresh_interval_minutes=15,
        last_successful_refresh_at=now - timedelta(minutes=20),
        next_refresh_at=now - timedelta(minutes=5),
        freshness_status="fresh",
    )

    assert dashboard_freshness_service.compute_freshness_status(dashboard) == "stale"


def test_failed_dashboard_stays_failed():
    dashboard = _dashboard(
        last_successful_refresh_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        freshness_status="failed",
    )

    assert dashboard_freshness_service.compute_freshness_status(dashboard) == "failed"


def test_next_refresh_is_based_on_last_successful_refresh():
    last_refresh = datetime(2026, 4, 30, 15, 0, tzinfo=timezone.utc)
    dashboard = _dashboard(
        auto_refresh_enabled=True,
        refresh_interval_minutes=45,
        last_successful_refresh_at=last_refresh,
    )

    assert dashboard_freshness_service.compute_next_refresh_at(dashboard) == last_refresh + timedelta(minutes=45)


def test_find_dashboards_due_for_refresh_returns_only_due_records():
    due_dashboard = _dashboard(id=1, next_refresh_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    db = MagicMock()
    db.execute.return_value.unique.return_value.scalars.return_value.all.return_value = [due_dashboard]

    result = dashboard_freshness_service.find_dashboards_due_for_refresh(db)

    assert [item.id for item in result] == [1]
