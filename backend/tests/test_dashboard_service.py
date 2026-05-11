from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest

from app.schemas.ai import AIInsight, AIQueryResponse
from app.schemas.dashboard import (
    DashboardCreateRequest,
    DashboardLayout,
    DashboardRefreshSettingsRequest,
    DashboardSnapshotModeRequest,
    DashboardUpdateRequest,
    DashboardWidgetCreateRequest,
    DashboardWidgetReorderItem,
    DashboardWidgetUpdateRequest,
)
from app.services import dashboard_service


def mock_return(value):
    return lambda *args, **kwargs: value


def _widget(widget_id: int = 1, *, source_type: str = "query", source_id: int = 7, use_snapshot: bool = False):
    return SimpleNamespace(
        id=widget_id,
        dashboard_id=3,
        type="chart" if source_type == "query" else "insight",
        source_type=source_type,
        source_id=source_id,
        title="Widget title",
        chart_type="bar" if source_type == "query" else "table",
        config_json={"x": "month", "y": "revenue"},
        data_json=[{"month": "Jan", "revenue": 10}],
        layout={"column_span": 1, "order": widget_id - 1, "use_snapshot": use_snapshot},
        snapshot_json={"query": {"answer": "old"}} if source_type == "query" else {"insight": {"type": "trend", "title": "Old", "description": "Old", "columns": [], "rows": [], "visualization_suggestion": None}},
        snapshot_created_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


def _dashboard(*widgets):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=3,
        user_id=1,
        name="Exec",
        created_at=now,
        updated_at=now,
        widgets=list(widgets),
    )


def test_refresh_snapshot_success(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    dashboard = _dashboard(widget)

    monkeypatch.setattr(dashboard_service, "_get_owned_widget", mock_return((dashboard, widget)))
    monkeypatch.setattr(
        dashboard_service,
        "_resolve_live_source_for_widget",
        lambda *args, **kwargs: (
            AIQueryResponse(
                answer="live",
                sql="select 1",
                rows=[{"value": 1}],
                columns=["value"],
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        dashboard_service,
        "_serialize_single_widget",
        lambda *args, **kwargs: SimpleNamespace(id=widget.id, snapshot_created_at="2026-04-29T20:00:00+00:00"),
    )

    result = dashboard_service.refresh_dashboard_widget_snapshot(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        widget_id=widget.id,
    )

    assert widget.snapshot_json["query"]["answer"] == "live"
    assert widget.snapshot_created_at is not None
    assert result.id == widget.id


def test_refresh_snapshot_failure_keeps_previous_snapshot(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    previous_snapshot = dict(widget.snapshot_json)
    dashboard = _dashboard(widget)

    monkeypatch.setattr(dashboard_service, "_get_owned_widget", mock_return((dashboard, widget)))
    monkeypatch.setattr(
        dashboard_service,
        "_resolve_live_source_for_widget",
        lambda *args, **kwargs: (_ for _ in ()).throw(HTTPException(status_code=404, detail="Query history entry not found")),
    )

    with pytest.raises(HTTPException):
        dashboard_service.refresh_dashboard_widget_snapshot(
            db=db,
            current_user=current_user,
            dashboard_id=dashboard.id,
            widget_id=widget.id,
        )

    assert widget.snapshot_json == previous_snapshot


def test_bulk_toggle_updates_all_widgets(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widgets = [_widget(1), _widget(2, source_type="insight")]
    dashboard = _dashboard(*widgets)

    monkeypatch.setattr(dashboard_service, "_get_owned_dashboard", mock_return(dashboard))
    monkeypatch.setattr(
        dashboard_service,
        "get_dashboard_detail",
        mock_return(SimpleNamespace(id=dashboard.id, widgets=[SimpleNamespace(layout=SimpleNamespace(use_snapshot=True))])),
    )

    result = dashboard_service.set_dashboard_snapshot_mode(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        payload=DashboardSnapshotModeRequest(use_snapshot=True),
    )

    assert widgets[0].layout["use_snapshot"] is True
    assert widgets[1].layout["use_snapshot"] is True
    assert result.id == dashboard.id


def test_bulk_refresh_returns_partial_failures(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    first = _widget(1)
    second = _widget(2)
    dashboard = _dashboard(first, second)

    monkeypatch.setattr(dashboard_service, "_get_owned_dashboard", mock_return(dashboard))

    def resolve(*args, widget, **kwargs):
        if widget.id == 1:
            return (
                AIQueryResponse(answer="fresh", sql="select 1", rows=[{"value": 1}], columns=["value"]),
                None,
            )
        raise HTTPException(status_code=404, detail="Query history entry not found")

    monkeypatch.setattr(dashboard_service, "_resolve_live_source_for_widget", resolve)
    monkeypatch.setattr(
        dashboard_service,
        "get_dashboard_detail",
        mock_return(
            SimpleNamespace(
                id=dashboard.id,
                name=dashboard.name,
                dataset_id=None,
                created_at=dashboard.created_at.isoformat(),
                updated_at=dashboard.updated_at.isoformat(),
                widgets=[],
            )
        ),
    )

    result = dashboard_service.refresh_all_dashboard_widget_snapshots(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
    )

    assert result.refreshed_count == 1
    assert result.failed_count == 1
    assert result.failures[0].widget_id == 2


def test_create_dashboard_persists_dataset_id(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    created = {}

    def capture_add(instance):
        created["dashboard"] = instance
        instance.id = 11
        instance.created_at = datetime.now(timezone.utc)
        instance.updated_at = instance.created_at
        instance.widgets = []

    db.add.side_effect = capture_add
    monkeypatch.setattr(dashboard_service, "_validate_dataset_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard_service, "_get_owned_dashboard", lambda *args, **kwargs: created["dashboard"])
    monkeypatch.setattr(
        dashboard_service,
        "_serialize_dashboard",
        lambda *args, **kwargs: SimpleNamespace(id=11, dataset_id=9, name="Ops"),
    )

    result = dashboard_service.create_dashboard(
        db=db,
        current_user=current_user,
        payload=DashboardCreateRequest(name="Ops", dataset_id=9),
    )

    assert created["dashboard"].user_id == 1
    assert created["dashboard"].dataset_id == 9
    assert created["dashboard"].freshness_status == "never_refreshed"
    assert result.dataset_id == 9


def test_list_dashboards_returns_only_user_dashboards():
    db = MagicMock()
    current_user = SimpleNamespace(id=3)
    first = _dashboard(_widget(1))
    first.id = 10
    first.dataset_id = 5
    second = _dashboard(_widget(2))
    second.id = 11
    second.dataset_id = None
    db.execute.return_value.unique.return_value.scalars.return_value.all.return_value = [first, second]

    result = dashboard_service.list_dashboards(db=db, current_user=current_user)

    assert [item.id for item in result] == [10, 11]
    assert result[0].dataset_id == 5
    assert result[0].widget_count == 1


def test_create_dashboard_widget_persists_explicit_widget_fields(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    dashboard = _dashboard()
    captured = {}

    def capture_add(instance):
        if getattr(instance, "dashboard_id", None) == dashboard.id:
            captured["widget"] = instance

    db.add.side_effect = capture_add
    monkeypatch.setattr(dashboard_service, "_get_owned_dashboard", mock_return(dashboard))
    monkeypatch.setattr(
        dashboard_service,
        "_resolve_source_for_widget_creation",
        lambda *args, **kwargs: (AIQueryResponse(answer="live", sql="select 1", rows=[], columns=[]), None),
    )
    monkeypatch.setattr(
        dashboard_service,
        "get_dashboard_detail",
        mock_return(SimpleNamespace(id=dashboard.id, widgets=[])),
    )

    payload = DashboardWidgetCreateRequest(
        widget_type="chart",
        source_type="ask_ai",
        source_id=22,
        chart_type="bar",
        title="Revenue by month",
        config_json={"x": "month", "y": "revenue"},
        data_json=[{"month": "Jan", "revenue": 10}],
        layout=DashboardLayout(x=2, y=1, width=8, height=5, column_span=2, order=0),
    )
    result = dashboard_service.create_dashboard_widget(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        payload=payload,
    )

    assert captured["widget"].source_type == "query"
    assert captured["widget"].title == "Revenue by month"
    assert captured["widget"].chart_type == "bar"
    assert captured["widget"].config_json == {"x": "month", "y": "revenue"}
    assert captured["widget"].layout["x"] == 2
    assert captured["widget"].layout["height"] == 5
    assert result.id == dashboard.id


def test_update_dashboard_widget_updates_layout_and_chart_fields(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    dashboard = _dashboard(widget)

    monkeypatch.setattr(dashboard_service, "_get_owned_widget", mock_return((dashboard, widget)))
    monkeypatch.setattr(
        dashboard_service,
        "get_dashboard_detail",
        mock_return(SimpleNamespace(id=dashboard.id, widgets=[])),
    )

    result = dashboard_service.update_dashboard_widget(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        widget_id=widget.id,
        payload=DashboardWidgetUpdateRequest(
            chart_type="line",
            title="Updated revenue",
            config_json={"x": "week", "y": "revenue"},
            layout=DashboardLayout(x=4, y=3, width=10, height=6, column_span=2, order=7),
        ),
    )

    assert widget.chart_type == "line"
    assert widget.title == "Updated revenue"
    assert widget.config_json == {"x": "week", "y": "revenue"}
    assert widget.layout["x"] == 4
    assert widget.layout["order"] == 7
    assert result.id == dashboard.id


def test_delete_dashboard_widget_removes_widget(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    widget = _widget()
    dashboard = _dashboard(widget)

    monkeypatch.setattr(dashboard_service, "_get_owned_widget", mock_return((dashboard, widget)))

    dashboard_service.delete_dashboard_widget(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        widget_id=widget.id,
    )

    db.delete.assert_called_once_with(widget)
    assert dashboard.updated_at is not None


def test_get_dashboard_detail_rejects_other_user_dashboard(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    monkeypatch.setattr(dashboard_service, "_get_owned_dashboard", mock_return(None))

    with pytest.raises(HTTPException) as exc_info:
        dashboard_service.get_dashboard_detail(db=db, current_user=current_user, dashboard_id=999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Dashboard not found"


def test_update_dashboard_persists_new_name_and_dataset(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    dashboard = _dashboard()
    dashboard.dataset_id = None

    monkeypatch.setattr(dashboard_service, "_get_owned_dashboard", mock_return(dashboard))
    monkeypatch.setattr(dashboard_service, "_validate_dataset_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard_service,
        "get_dashboard_detail",
        mock_return(SimpleNamespace(id=dashboard.id, name="Finance", dataset_id=8)),
    )

    result = dashboard_service.update_dashboard(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        payload=DashboardUpdateRequest(name="Finance", dataset_id=8),
    )

    assert dashboard.name == "Finance"
    assert dashboard.dataset_id == 8
    assert result.dataset_id == 8


def test_update_dashboard_refresh_settings_sets_schedule(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    dashboard = _dashboard()
    dashboard.auto_refresh_enabled = False
    dashboard.refresh_interval_minutes = None
    dashboard.last_successful_refresh_at = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    dashboard.next_refresh_at = None
    dashboard.freshness_status = "fresh"

    monkeypatch.setattr(dashboard_service, "_get_owned_dashboard", mock_return(dashboard))
    monkeypatch.setattr(
        dashboard_service,
        "get_dashboard_detail",
        mock_return(SimpleNamespace(id=dashboard.id, auto_refresh_enabled=True, refresh_interval_minutes=60)),
    )

    result = dashboard_service.update_dashboard_refresh_settings(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard.id,
        payload=DashboardRefreshSettingsRequest(auto_refresh_enabled=True, refresh_interval_minutes=60),
    )

    assert dashboard.auto_refresh_enabled is True
    assert dashboard.refresh_interval_minutes == 60
    assert dashboard.next_refresh_at is not None
    assert result.refresh_interval_minutes == 60
