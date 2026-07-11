from types import SimpleNamespace
from unittest.mock import MagicMock

from app.workers import dashboard_refresh_worker


def _dashboard(dashboard_id: int, *, user_id: int = 1):
    return SimpleNamespace(id=dashboard_id, user_id=user_id)


def test_run_cycle_processes_due_dashboards(monkeypatch):
    db = MagicMock()
    dashboards = [_dashboard(1), _dashboard(2)]
    refreshed: list[int] = []

    monkeypatch.setattr(dashboard_refresh_worker, "find_dashboards_due_for_refresh", lambda db: dashboards)
    monkeypatch.setattr(dashboard_refresh_worker, "_try_mark_refresh_in_progress", lambda db, dashboard_id: True)
    monkeypatch.setattr(dashboard_refresh_worker, "_recover_expired_locks", lambda db: 0)
    monkeypatch.setattr(dashboard_refresh_worker, "_clear_refresh_in_progress", lambda db, dashboard_id, error_message=None: None)
    monkeypatch.setattr(
        dashboard_refresh_worker,
        "refresh_dashboard",
        lambda db, current_user, dashboard_id, lock_acquired=False: refreshed.append(dashboard_id),
    )

    result = dashboard_refresh_worker.run_dashboard_refresh_cycle(db)

    assert refreshed == [1, 2]
    assert result == {
        "due": 2,
        "processed": 2,
        "succeeded": 2,
        "failed": 0,
        "skipped_locked": 0,
        "recovered_expired_locks": 0,
    }


def test_run_cycle_ignores_when_no_dashboards_are_due(monkeypatch):
    db = MagicMock()

    monkeypatch.setattr(dashboard_refresh_worker, "find_dashboards_due_for_refresh", lambda db: [])
    monkeypatch.setattr(dashboard_refresh_worker, "_try_mark_refresh_in_progress", lambda db, dashboard_id: True)
    monkeypatch.setattr(dashboard_refresh_worker, "_recover_expired_locks", lambda db: 0)
    monkeypatch.setattr(dashboard_refresh_worker, "_clear_refresh_in_progress", lambda db, dashboard_id, error_message=None: None)

    result = dashboard_refresh_worker.run_dashboard_refresh_cycle(db)

    assert result == {
        "due": 0,
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped_locked": 0,
        "recovered_expired_locks": 0,
    }


def test_run_cycle_continues_after_dashboard_failure(monkeypatch):
    db = MagicMock()
    dashboards = [_dashboard(1), _dashboard(2)]
    refreshed: list[int] = []

    monkeypatch.setattr(dashboard_refresh_worker, "find_dashboards_due_for_refresh", lambda db: dashboards)
    monkeypatch.setattr(dashboard_refresh_worker, "_try_mark_refresh_in_progress", lambda db, dashboard_id: True)
    monkeypatch.setattr(dashboard_refresh_worker, "_recover_expired_locks", lambda db: 0)
    monkeypatch.setattr(dashboard_refresh_worker, "_clear_refresh_in_progress", lambda db, dashboard_id, error_message=None: None)

    def refresh(db, current_user, dashboard_id, lock_acquired=False):
        if dashboard_id == 1:
            raise RuntimeError("boom")
        refreshed.append(dashboard_id)

    monkeypatch.setattr(dashboard_refresh_worker, "refresh_dashboard", refresh)

    result = dashboard_refresh_worker.run_dashboard_refresh_cycle(db)

    assert refreshed == [2]
    assert result == {
        "due": 2,
        "processed": 2,
        "succeeded": 1,
        "failed": 1,
        "skipped_locked": 0,
        "recovered_expired_locks": 0,
    }
    db.rollback.assert_called()


def test_run_cycle_respects_refresh_in_progress_lock(monkeypatch):
    db = MagicMock()
    dashboards = [_dashboard(1), _dashboard(2)]
    refreshed: list[int] = []

    monkeypatch.setattr(dashboard_refresh_worker, "find_dashboards_due_for_refresh", lambda db: dashboards)
    monkeypatch.setattr(
        dashboard_refresh_worker,
        "_try_mark_refresh_in_progress",
        lambda db, dashboard_id: dashboard_id != 1,
    )
    monkeypatch.setattr(dashboard_refresh_worker, "_recover_expired_locks", lambda db: 0)
    monkeypatch.setattr(dashboard_refresh_worker, "_clear_refresh_in_progress", lambda db, dashboard_id, error_message=None: None)
    monkeypatch.setattr(
        dashboard_refresh_worker,
        "refresh_dashboard",
        lambda db, current_user, dashboard_id, lock_acquired=False: refreshed.append(dashboard_id),
    )

    result = dashboard_refresh_worker.run_dashboard_refresh_cycle(db)

    assert refreshed == [2]
    assert result == {
        "due": 2,
        "processed": 1,
        "succeeded": 1,
        "failed": 0,
        "skipped_locked": 1,
        "recovered_expired_locks": 0,
    }
