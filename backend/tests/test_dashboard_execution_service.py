from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.services import dashboard_execution_service


def _widget(*, widget_id: int = 7, execution_type: str = "query", source_type: str = "query"):
    return SimpleNamespace(
        id=widget_id,
        dashboard_id=3,
        type="chart",
        source_type=source_type,
        source_id=9,
        execution_type=execution_type,
        title="Revenue",
        chart_type="bar",
        query_sql="select * from dataset",
        config_json={"x": "month", "y": "revenue"},
        data_json=[{"month": "Jan", "revenue": 10}],
        layout={"order": 0},
        snapshot_json=None,
        snapshot_created_at=None,
        last_run_at=None,
        execution_status="never_run",
        error_message=None,
        created_at=datetime.now(timezone.utc),
    )


def _dashboard(widget):
    return SimpleNamespace(
        id=3,
        user_id=1,
        dataset_id=12,
        name="Ops",
        auto_refresh_enabled=True,
        refresh_interval_minutes=30,
        last_successful_refresh_at=None,
        next_refresh_at=None,
        freshness_status="never_refreshed",
        widgets=[widget],
        updated_at=datetime.now(timezone.utc),
    )


def test_execute_widget_refresh_success_updates_data_and_timestamp(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    dashboard = _dashboard(widget)

    def refresh_query(*args, **kwargs):
        target = kwargs["widget"]
        target.data_json = [{"month": "Feb", "revenue": 14}]
        target.chart_type = "line"
        target.config_json = {"x": "month", "y": "revenue"}

    monkeypatch.setattr(dashboard_execution_service, "_refresh_query_widget", refresh_query)

    result = dashboard_execution_service.execute_widget(
        db,
        widget=widget,
        dashboard=dashboard,
        current_user=current_user,
    )

    assert result.data_json == [{"month": "Feb", "revenue": 14}]
    assert result.chart_type == "line"
    assert result.last_run_at is not None
    assert result.execution_status == "success"
    assert result.error_message is None


def test_execute_widget_failure_keeps_previous_data(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    dashboard = _dashboard(widget)
    previous_data = list(widget.data_json)

    def fail_refresh(*args, **kwargs):
        raise HTTPException(status_code=400, detail="Broken SQL")

    monkeypatch.setattr(dashboard_execution_service, "_refresh_query_widget", fail_refresh)

    result = dashboard_execution_service.execute_widget(
        db,
        widget=widget,
        dashboard=dashboard,
        current_user=current_user,
    )

    assert result.data_json == previous_data
    assert result.error_message == "Broken SQL"
    assert result.execution_status == "failed"
    assert result.last_run_at is None


def test_refresh_dashboard_updates_timestamp_even_with_partial_failures(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    first = _widget(widget_id=7)
    second = _widget(widget_id=8, execution_type="snapshot", source_type="manual")
    dashboard = _dashboard(first)
    dashboard.widgets = [first, second]
    previous_updated_at = dashboard.updated_at

    monkeypatch.setattr(dashboard_execution_service, "_get_owned_dashboard", lambda *args, **kwargs: dashboard)

    def execute(db, *, widget, dashboard, current_user):
        if widget.id == first.id:
            widget.data_json = [{"month": "Mar", "revenue": 18}]
            widget.last_run_at = datetime.now(timezone.utc)
            widget.execution_status = "success"
            widget.error_message = None
        else:
            widget.execution_status = "failed"
            widget.error_message = "Snapshot widget has no saved data"
        return widget

    monkeypatch.setattr(dashboard_execution_service, "execute_widget", execute)
    monkeypatch.setattr(
        dashboard_execution_service,
        "get_dashboard_detail",
        lambda *args, **kwargs: SimpleNamespace(id=dashboard.id, widgets=dashboard.widgets, updated_at=dashboard.updated_at),
    )

    result = dashboard_execution_service.refresh_dashboard(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
    )

    assert result.id == dashboard.id
    assert dashboard.updated_at >= previous_updated_at
    assert first.last_run_at is not None
    assert first.execution_status == "success"
    assert second.execution_status == "failed"
    assert second.error_message == "Snapshot widget has no saved data"
    assert dashboard.last_successful_refresh_at is not None
    assert dashboard.freshness_status == "stale"


def test_refresh_dashboard_success_sets_freshness_to_fresh(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget(widget_id=7)
    dashboard = _dashboard(widget)

    monkeypatch.setattr(dashboard_execution_service, "_get_owned_dashboard", lambda *args, **kwargs: dashboard)

    def execute(db, *, widget, dashboard, current_user):
        widget.last_run_at = datetime.now(timezone.utc)
        widget.execution_status = "success"
        widget.error_message = None
        return widget

    monkeypatch.setattr(dashboard_execution_service, "execute_widget", execute)
    monkeypatch.setattr(
        dashboard_execution_service,
        "get_dashboard_detail",
        lambda *args, **kwargs: SimpleNamespace(id=dashboard.id, freshness_status=dashboard.freshness_status),
    )

    result = dashboard_execution_service.refresh_dashboard(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
    )

    assert dashboard.last_successful_refresh_at is not None
    assert dashboard.next_refresh_at is not None
    assert dashboard.freshness_status == "fresh"
    assert result.freshness_status == "fresh"


def test_refresh_dashboard_all_failures_sets_freshness_to_failed(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget(widget_id=7)
    dashboard = _dashboard(widget)

    monkeypatch.setattr(dashboard_execution_service, "_get_owned_dashboard", lambda *args, **kwargs: dashboard)

    def execute(db, *, widget, dashboard, current_user):
        widget.execution_status = "failed"
        widget.error_message = "Broken SQL"
        return widget

    monkeypatch.setattr(dashboard_execution_service, "execute_widget", execute)
    monkeypatch.setattr(
        dashboard_execution_service,
        "get_dashboard_detail",
        lambda *args, **kwargs: SimpleNamespace(id=dashboard.id, freshness_status=dashboard.freshness_status),
    )

    result = dashboard_execution_service.refresh_dashboard(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
    )

    assert dashboard.last_successful_refresh_at is None
    assert dashboard.freshness_status == "failed"
    assert result.freshness_status == "failed"


def test_refresh_dashboard_widget_success(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    dashboard = _dashboard(widget)

    monkeypatch.setattr(dashboard_execution_service, "_get_owned_widget", lambda *args, **kwargs: (dashboard, widget))

    def execute(db, *, widget, dashboard, current_user):
        widget.data_json = [{"month": "Apr", "revenue": 21}]
        widget.last_run_at = datetime.now(timezone.utc)
        widget.execution_status = "success"
        widget.error_message = None
        return widget

    monkeypatch.setattr(dashboard_execution_service, "execute_widget", execute)

    result = dashboard_execution_service.refresh_dashboard_widget(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        widget_id=widget.id,
    )

    assert result.data_json == [{"month": "Apr", "revenue": 21}]
    assert result.execution_status == "success"
    assert result.last_run_at is not None


def test_refresh_dashboard_widget_failure_keeps_previous_data(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    dashboard = _dashboard(widget)
    previous_data = list(widget.data_json)

    monkeypatch.setattr(dashboard_execution_service, "_get_owned_widget", lambda *args, **kwargs: (dashboard, widget))

    def execute(db, *, widget, dashboard, current_user):
        widget.error_message = "Broken SQL"
        widget.execution_status = "failed"
        return widget

    monkeypatch.setattr(dashboard_execution_service, "execute_widget", execute)

    result = dashboard_execution_service.refresh_dashboard_widget(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        widget_id=widget.id,
    )

    assert result.data_json == previous_data
    assert result.execution_status == "failed"
    assert result.error_message == "Broken SQL"


def test_refresh_dashboard_widget_rejects_widget_from_other_dashboard(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    monkeypatch.setattr(dashboard_execution_service, "_get_owned_widget", lambda *args, **kwargs: None)

    try:
        dashboard_execution_service.refresh_dashboard_widget(
            db=db,
            current_user=current_user,
            dashboard_id=3,
            widget_id=99,
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Dashboard widget not found"
