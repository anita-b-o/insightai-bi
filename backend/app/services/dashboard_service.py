from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget
from app.models.dataset import Dataset
from app.models.dataset_insight_run import DatasetInsightRun
from app.models.query_history import QueryHistory
from app.models.user import User
from app.schemas.ai import AIInsight, AIQueryResponse
from app.schemas.dashboard import (
    DashboardBulkSnapshotRefreshResponse,
    DashboardCreateRequest,
    DashboardDetail,
    DashboardLayout,
    DashboardRefreshSettingsRequest,
    DashboardSnapshotModeRequest,
    DashboardSnapshotRefreshFailure,
    DashboardSummary,
    DashboardUpdateRequest,
    DashboardWidgetCreateRequest,
    DashboardWidgetRead,
    DashboardWidgetReorderItem,
    DashboardWidgetResolvedSource,
    DashboardWidgetUpdateRequest,
)
from app.services.dashboard_freshness_service import compute_freshness_status, compute_next_refresh_at


def _to_iso8601(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _get_owned_dashboard(db: Session, *, dashboard_id: int, user_id: int) -> Dashboard | None:
    statement = (
        select(Dashboard)
        .options(joinedload(Dashboard.widgets))
        .where(Dashboard.id == dashboard_id, Dashboard.user_id == user_id)
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _get_owned_widget(
    db: Session,
    *,
    dashboard_id: int,
    widget_id: int,
    user_id: int,
) -> tuple[Dashboard, DashboardWidget] | None:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=user_id)
    if dashboard is None:
        return None
    widget = next((item for item in dashboard.widgets if item.id == widget_id), None)
    if widget is None:
        return None
    return dashboard, widget


def _layout_from_widget(widget: DashboardWidget) -> DashboardLayout:
    layout = widget.layout or {}
    return DashboardLayout(
        column_span=int(layout.get("column_span", 1)),
        order=int(layout.get("order", 0)),
        use_snapshot=bool(layout.get("use_snapshot", False)),
        x=int(layout.get("x", 0)),
        y=int(layout.get("y", 0)),
        width=int(layout.get("width", 6)),
        height=int(layout.get("height", 4)),
    )


def _title_from_widget(widget: DashboardWidget) -> str | None:
    title = widget.title
    if isinstance(title, str) and title.strip():
        return title.strip()
    layout = widget.layout or {}
    title = layout.get("title")
    return str(title) if isinstance(title, str) and title.strip() else None


def _insight_index_from_widget(widget: DashboardWidget) -> int | None:
    layout = widget.layout or {}
    index = layout.get("insight_index")
    return int(index) if isinstance(index, int) and index >= 0 else None


def _build_widget_layout(
    existing: dict[str, object] | None,
    *,
    layout: DashboardLayout | None,
    insight_index: int | None,
) -> dict[str, object]:
    payload = dict(existing or {})
    if layout is not None:
        payload.update(layout.model_dump(mode="json"))
    if insight_index is not None or "insight_index" in payload:
        if insight_index is None:
            payload.pop("insight_index", None)
        else:
            payload["insight_index"] = insight_index
    return payload


def _storage_source_type(source_type: str) -> str:
    return "query" if source_type == "ask_ai" else source_type


def _default_execution_type(source_type: str) -> str:
    if source_type == "query":
        return "query"
    if source_type == "insight":
        return "insight"
    return "snapshot"


def _validate_dataset_access(db: Session, *, current_user: User, dataset_id: int | None) -> None:
    if dataset_id is None:
        return
    statement = select(Dataset.id).where(Dataset.id == dataset_id, Dataset.owner_id == current_user.id)
    if db.execute(statement).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")


def _query_response_from_record(record: QueryHistory) -> AIQueryResponse | None:
    if not record.result or not record.result.result_json:
        return None
    return AIQueryResponse.model_validate(record.result.result_json)


def _insight_from_run(run: DatasetInsightRun, insight_index: int) -> AIInsight | None:
    items = run.insights_json or []
    if insight_index >= len(items):
        return None
    return AIInsight.model_validate(items[insight_index])


def _snapshot_payload_from_widget_source(
    *,
    query: AIQueryResponse | None = None,
    insight: AIInsight | None = None,
) -> dict[str, object] | None:
    if query is not None:
        return {"query": query.model_dump(mode="json")}
    if insight is not None:
        return {"insight": insight.model_dump(mode="json")}
    return None


def _build_source_maps(db: Session, *, user: User, widgets: list[DashboardWidget]) -> tuple[dict[int, QueryHistory], dict[int, DatasetInsightRun]]:
    query_ids = [widget.source_id for widget in widgets if widget.source_type == "query" and widget.source_id is not None]
    insight_run_ids = [widget.source_id for widget in widgets if widget.source_type == "insight" and widget.source_id is not None]

    query_map: dict[int, QueryHistory] = {}
    if query_ids:
        statement = (
            select(QueryHistory)
            .options(joinedload(QueryHistory.result))
            .where(
                QueryHistory.user_id == user.id,
                QueryHistory.id.in_(query_ids),
                QueryHistory.deleted_at.is_(None),
            )
        )
        query_map = {item.id: item for item in db.execute(statement).unique().scalars().all()}

    insight_run_map: dict[int, DatasetInsightRun] = {}
    if insight_run_ids:
        statement = (
            select(DatasetInsightRun)
            .options(joinedload(DatasetInsightRun.dataset))
            .where(DatasetInsightRun.user_id == user.id, DatasetInsightRun.id.in_(insight_run_ids))
        )
        insight_run_map = {item.id: item for item in db.execute(statement).unique().scalars().all()}

    return query_map, insight_run_map


def _serialize_widget(
    *,
    widget: DashboardWidget,
    query_map: dict[int, QueryHistory],
    insight_run_map: dict[int, DatasetInsightRun],
) -> DashboardWidgetRead:
    source = DashboardWidgetResolvedSource()
    layout = _layout_from_widget(widget)
    snapshot_payload = widget.snapshot_json or {}
    snapshot_created_at = widget.snapshot_created_at
    using_snapshot = False
    source_changed = False

    if widget.source_type == "query":
        live_record = query_map.get(widget.source_id)
        live_query = _query_response_from_record(live_record) if live_record is not None else None
        snapshot_query = (
            AIQueryResponse.model_validate(snapshot_payload["query"])
            if isinstance(snapshot_payload.get("query"), dict)
            else None
        )
        if live_record is not None and snapshot_created_at is not None:
            source_changed = live_record.updated_at > snapshot_created_at
        elif live_record is None and snapshot_query is not None:
            source_changed = True
        if layout.use_snapshot and snapshot_query is not None:
            source.query = snapshot_query
            using_snapshot = True
        else:
            source.query = live_query or snapshot_query
            using_snapshot = live_query is None and snapshot_query is not None
    elif widget.source_type == "insight":
        insight_index = _insight_index_from_widget(widget) or 0
        live_run = insight_run_map.get(widget.source_id)
        live_insight = _insight_from_run(live_run, insight_index) if live_run is not None else None
        snapshot_insight = (
            AIInsight.model_validate(snapshot_payload["insight"])
            if isinstance(snapshot_payload.get("insight"), dict)
            else None
        )
        if live_run is not None and live_run.dataset is not None:
            source_changed = live_run.dataset.updated_at > live_run.dataset_updated_at_snapshot
        elif live_run is None and snapshot_insight is not None:
            source_changed = True
        if layout.use_snapshot and snapshot_insight is not None:
            source.insight = snapshot_insight
            using_snapshot = True
        else:
            source.insight = live_insight or snapshot_insight
            using_snapshot = live_insight is None and snapshot_insight is not None

    return DashboardWidgetRead(
        id=widget.id,
        dashboard_id=widget.dashboard_id,
        type=widget.type,
        widget_type=widget.type,
        source_type=widget.source_type,
        source_id=widget.source_id,
        execution_type=widget.execution_type or _default_execution_type(widget.source_type),
        execution_status=widget.execution_status or "never_run",
        chart_type=widget.chart_type or ("table" if widget.type != "chart" else None),
        query_sql=widget.query_sql,
        layout=layout,
        title=_title_from_widget(widget),
        config_json=widget.config_json,
        data_json=widget.data_json,
        last_run_at=_to_iso8601(widget.last_run_at) if widget.last_run_at else None,
        error_message=widget.error_message,
        insight_index=_insight_index_from_widget(widget),
        has_snapshot=widget.snapshot_json is not None,
        using_snapshot=using_snapshot,
        snapshot_created_at=_to_iso8601(widget.snapshot_created_at) if widget.snapshot_created_at else None,
        source_changed=source_changed,
        created_at=_to_iso8601(widget.created_at),
        source=source,
    )


def _serialize_dashboard(db: Session, *, user: User, dashboard: Dashboard) -> DashboardDetail:
    widgets = sorted(dashboard.widgets, key=lambda widget: (_layout_from_widget(widget).order, widget.created_at))
    query_map, insight_run_map = _build_source_maps(db, user=user, widgets=widgets)
    freshness_status = compute_freshness_status(dashboard)
    next_refresh_at = compute_next_refresh_at(dashboard)
    dashboard.freshness_status = freshness_status
    dashboard.next_refresh_at = next_refresh_at
    return DashboardDetail(
        id=dashboard.id,
        name=dashboard.name,
        dataset_id=dashboard.dataset_id,
        auto_refresh_enabled=bool(getattr(dashboard, "auto_refresh_enabled", False)),
        refresh_interval_minutes=getattr(dashboard, "refresh_interval_minutes", None),
        last_successful_refresh_at=(
            _to_iso8601(dashboard.last_successful_refresh_at) if getattr(dashboard, "last_successful_refresh_at", None) else None
        ),
        next_refresh_at=_to_iso8601(next_refresh_at) if next_refresh_at else None,
        freshness_status=freshness_status,  # type: ignore[arg-type]
        created_at=_to_iso8601(dashboard.created_at),
        updated_at=_to_iso8601(dashboard.updated_at),
        widgets=[
            _serialize_widget(widget=widget, query_map=query_map, insight_run_map=insight_run_map)
            for widget in widgets
        ],
    )


def _serialize_single_widget(
    db: Session,
    *,
    user: User,
    widget: DashboardWidget,
) -> DashboardWidgetRead:
    query_map, insight_run_map = _build_source_maps(db, user=user, widgets=[widget])
    return _serialize_widget(widget=widget, query_map=query_map, insight_run_map=insight_run_map)


def create_dashboard(db: Session, *, current_user: User, payload: DashboardCreateRequest) -> DashboardDetail:
    _validate_dataset_access(db, current_user=current_user, dataset_id=payload.dataset_id)
    dashboard = Dashboard(
        user_id=current_user.id,
        dataset_id=payload.dataset_id,
        name=payload.name,
        auto_refresh_enabled=payload.auto_refresh_enabled,
        refresh_interval_minutes=payload.refresh_interval_minutes if payload.auto_refresh_enabled else None,
        freshness_status="never_refreshed",
    )
    dashboard.next_refresh_at = compute_next_refresh_at(dashboard)
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard.id, user_id=current_user.id) or dashboard
    return _serialize_dashboard(db, user=current_user, dashboard=dashboard)


def update_dashboard(db: Session, *, current_user: User, dashboard_id: int, payload: DashboardUpdateRequest) -> DashboardDetail:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    if payload.dataset_id is not None:
        _validate_dataset_access(db, current_user=current_user, dataset_id=payload.dataset_id)
        dashboard.dataset_id = payload.dataset_id
    if payload.name is not None:
        dashboard.name = payload.name
    if payload.auto_refresh_enabled is not None:
        dashboard.auto_refresh_enabled = payload.auto_refresh_enabled
    if payload.refresh_interval_minutes is not None or payload.auto_refresh_enabled is False:
        dashboard.refresh_interval_minutes = payload.refresh_interval_minutes if dashboard.auto_refresh_enabled else None
    dashboard.next_refresh_at = compute_next_refresh_at(dashboard)
    dashboard.freshness_status = compute_freshness_status(dashboard)
    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(dashboard)
    db.commit()
    return get_dashboard_detail(db, current_user=current_user, dashboard_id=dashboard.id)


def delete_dashboard(db: Session, *, current_user: User, dashboard_id: int) -> None:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    db.delete(dashboard)
    db.commit()


def list_dashboards(db: Session, *, current_user: User) -> list[DashboardSummary]:
    statement = (
        select(Dashboard)
        .options(joinedload(Dashboard.widgets))
        .where(Dashboard.user_id == current_user.id)
        .order_by(Dashboard.updated_at.desc(), Dashboard.id.desc())
    )
    dashboards = db.execute(statement).unique().scalars().all()
    return [
        DashboardSummary(
            id=dashboard.id,
            name=dashboard.name,
            dataset_id=dashboard.dataset_id,
            auto_refresh_enabled=bool(getattr(dashboard, "auto_refresh_enabled", False)),
            refresh_interval_minutes=getattr(dashboard, "refresh_interval_minutes", None),
            last_successful_refresh_at=(
                _to_iso8601(dashboard.last_successful_refresh_at) if getattr(dashboard, "last_successful_refresh_at", None) else None
            ),
            next_refresh_at=(
                _to_iso8601(compute_next_refresh_at(dashboard)) if compute_next_refresh_at(dashboard) is not None else None
            ),
            freshness_status=compute_freshness_status(dashboard),  # type: ignore[arg-type]
            created_at=_to_iso8601(dashboard.created_at),
            updated_at=_to_iso8601(dashboard.updated_at),
            widget_count=len(dashboard.widgets),
        )
        for dashboard in dashboards
    ]


def get_dashboard_detail(db: Session, *, current_user: User, dashboard_id: int) -> DashboardDetail:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return _serialize_dashboard(db, user=current_user, dashboard=dashboard)


def _resolve_source_for_widget_creation(
    db: Session,
    *,
    current_user: User,
    payload: DashboardWidgetCreateRequest,
) -> tuple[AIQueryResponse | None, AIInsight | None]:
    if payload.source_type == "manual":
        return None, None
    if _storage_source_type(payload.source_type) == "query":
        statement = (
            select(QueryHistory)
            .options(joinedload(QueryHistory.result))
            .where(
                QueryHistory.user_id == current_user.id,
                QueryHistory.id == payload.source_id,
                QueryHistory.deleted_at.is_(None),
            )
        )
        query_record = db.execute(statement).unique().scalar_one_or_none()
        if query_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query history entry not found")
        return _query_response_from_record(query_record), None

    statement = (
        select(DatasetInsightRun)
        .options(joinedload(DatasetInsightRun.dataset))
        .where(DatasetInsightRun.user_id == current_user.id, DatasetInsightRun.id == payload.source_id)
    )
    run = db.execute(statement).unique().scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight run not found")
    insight_index = payload.insight_index or 0
    insight = _insight_from_run(run, insight_index)
    if insight is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insight index is out of range")
    return None, insight


def _load_query_history_record(
    db: Session,
    *,
    current_user: User,
    source_id: int | None,
) -> QueryHistory | None:
    if source_id is None:
        return None
    statement = (
        select(QueryHistory)
        .options(joinedload(QueryHistory.result), joinedload(QueryHistory.dataset))
        .where(
            QueryHistory.user_id == current_user.id,
            QueryHistory.id == source_id,
            QueryHistory.deleted_at.is_(None),
        )
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _resolve_live_source_for_widget(
    db: Session,
    *,
    current_user: User,
    widget: DashboardWidget,
) -> tuple[AIQueryResponse | None, AIInsight | None]:
    if widget.source_type == "manual":
        return None, None
    if widget.source_type == "query":
        statement = (
            select(QueryHistory)
            .options(joinedload(QueryHistory.result))
            .where(
                QueryHistory.user_id == current_user.id,
                QueryHistory.id == widget.source_id,
                QueryHistory.deleted_at.is_(None),
            )
        )
        query_record = db.execute(statement).unique().scalar_one_or_none()
        if query_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query history entry not found")
        query = _query_response_from_record(query_record)
        if query is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query result is no longer available")
        return query, None

    statement = (
        select(DatasetInsightRun)
        .options(joinedload(DatasetInsightRun.dataset))
        .where(DatasetInsightRun.user_id == current_user.id, DatasetInsightRun.id == widget.source_id)
    )
    run = db.execute(statement).unique().scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight run not found")
    insight_index = _insight_index_from_widget(widget) or 0
    insight = _insight_from_run(run, insight_index)
    if insight is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insight is no longer available")
    return None, insight


def create_dashboard_widget(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    payload: DashboardWidgetCreateRequest,
) -> DashboardDetail:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    query, insight = _resolve_source_for_widget_creation(db, current_user=current_user, payload=payload)
    stored_source_type = _storage_source_type(payload.source_type)
    query_record = (
        _load_query_history_record(db, current_user=current_user, source_id=payload.source_id)
        if stored_source_type == "query"
        else None
    )
    snapshot_payload = (
        _snapshot_payload_from_widget_source(query=query, insight=insight)
        if payload.save_snapshot
        else None
    )
    snapshot_created_at = datetime.now(timezone.utc) if snapshot_payload is not None else None

    widget = DashboardWidget(
        dashboard_id=dashboard.id,
        type=payload.type,
        source_type=stored_source_type,
        source_id=payload.source_id,
        execution_type=payload.execution_type or _default_execution_type(stored_source_type),
        title=payload.title,
        chart_type=payload.chart_type,
        query_sql=payload.query_sql or (query.sql if query is not None and query.sql else query_record.generated_sql if query_record is not None else None),
        config_json=payload.config_json,
        data_json=payload.data_json,
        layout=_build_widget_layout(
            None,
            layout=payload.layout,
            insight_index=payload.insight_index,
        ),
        snapshot_json=snapshot_payload,
        snapshot_created_at=snapshot_created_at,
    )
    db.add(widget)
    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(dashboard)
    db.commit()
    return get_dashboard_detail(db, current_user=current_user, dashboard_id=dashboard.id)


def update_dashboard_widget(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    widget_id: int,
    payload: DashboardWidgetUpdateRequest,
) -> DashboardDetail:
    owned = _get_owned_widget(db, dashboard_id=dashboard_id, widget_id=widget_id, user_id=current_user.id)
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard widget not found")
    dashboard, widget = owned

    if payload.type is not None:
        widget.type = payload.type
    if payload.execution_type is not None:
        widget.execution_type = payload.execution_type
    if payload.chart_type is not None:
        widget.chart_type = payload.chart_type
    if payload.query_sql is not None:
        widget.query_sql = payload.query_sql
    if payload.config_json is not None:
        widget.config_json = payload.config_json
    if payload.data_json is not None:
        widget.data_json = payload.data_json
    if payload.title is not None:
        widget.title = payload.title
    if payload.layout is not None or payload.title is not None or payload.insight_index is not None:
        widget.layout = _build_widget_layout(
            widget.layout,
            layout=payload.layout,
            insight_index=payload.insight_index if payload.insight_index is not None else _insight_index_from_widget(widget),
        )
    if payload.save_snapshot is True:
        query = None
        insight = None
        create_payload = DashboardWidgetCreateRequest(
            type=widget.type,
            source_type=widget.source_type,
            source_id=widget.source_id,
            chart_type=widget.chart_type,
            layout=_layout_from_widget(widget),
            title=widget.title,
            config_json=widget.config_json,
            data_json=widget.data_json,
            insight_index=_insight_index_from_widget(widget),
            save_snapshot=True,
        )
        query, insight = _resolve_source_for_widget_creation(db, current_user=current_user, payload=create_payload)
        widget.snapshot_json = _snapshot_payload_from_widget_source(query=query, insight=insight)
        widget.snapshot_created_at = datetime.now(timezone.utc) if widget.snapshot_json is not None else None

    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(widget)
    db.add(dashboard)
    db.commit()
    return get_dashboard_detail(db, current_user=current_user, dashboard_id=dashboard.id)


def refresh_dashboard_widget_snapshot(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    widget_id: int,
) -> DashboardWidgetRead:
    owned = _get_owned_widget(db, dashboard_id=dashboard_id, widget_id=widget_id, user_id=current_user.id)
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard widget not found")
    dashboard, widget = owned

    query, insight = _resolve_live_source_for_widget(db, current_user=current_user, widget=widget)
    snapshot_payload = _snapshot_payload_from_widget_source(query=query, insight=insight)
    if snapshot_payload is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Widget source could not be snapshotted")

    widget.snapshot_json = snapshot_payload
    widget.snapshot_created_at = datetime.now(timezone.utc)
    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(widget)
    db.add(dashboard)
    db.commit()
    db.refresh(widget)
    return _serialize_single_widget(db, user=current_user, widget=widget)


def set_dashboard_snapshot_mode(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    payload: DashboardSnapshotModeRequest,
) -> DashboardDetail:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    for widget in dashboard.widgets:
        widget.layout = _build_widget_layout(
            widget.layout,
            layout=DashboardLayout(
                column_span=_layout_from_widget(widget).column_span,
                order=_layout_from_widget(widget).order,
                use_snapshot=payload.use_snapshot,
                x=_layout_from_widget(widget).x,
                y=_layout_from_widget(widget).y,
                width=_layout_from_widget(widget).width,
                height=_layout_from_widget(widget).height,
            ),
            insight_index=_insight_index_from_widget(widget),
        )
        db.add(widget)

    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(dashboard)
    db.commit()
    return get_dashboard_detail(db, current_user=current_user, dashboard_id=dashboard.id)


def refresh_all_dashboard_widget_snapshots(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
) -> DashboardBulkSnapshotRefreshResponse:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    refreshed_count = 0
    failures: list[DashboardSnapshotRefreshFailure] = []

    for widget in dashboard.widgets:
        try:
            query, insight = _resolve_live_source_for_widget(db, current_user=current_user, widget=widget)
            snapshot_payload = _snapshot_payload_from_widget_source(query=query, insight=insight)
            if snapshot_payload is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Widget source could not be snapshotted")
            widget.snapshot_json = snapshot_payload
            widget.snapshot_created_at = datetime.now(timezone.utc)
            db.add(widget)
            refreshed_count += 1
        except HTTPException as exc:
            failures.append(DashboardSnapshotRefreshFailure(widget_id=widget.id, reason=str(exc.detail)))
        except Exception as exc:
            failures.append(DashboardSnapshotRefreshFailure(widget_id=widget.id, reason=str(exc)))

    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(dashboard)
    db.commit()

    return DashboardBulkSnapshotRefreshResponse(
        refreshed_count=refreshed_count,
        failed_count=len(failures),
        failures=failures,
        dashboard=get_dashboard_detail(db, current_user=current_user, dashboard_id=dashboard.id),
    )


def reorder_dashboard_widgets(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    items: list[DashboardWidgetReorderItem],
) -> DashboardDetail:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    widget_map = {widget.id: widget for widget in dashboard.widgets}
    if set(widget_map) != {item.widget_id for item in items}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reorder payload must include all dashboard widgets")

    for item in items:
        widget = widget_map[item.widget_id]
        widget.layout = _build_widget_layout(
            widget.layout,
            layout=DashboardLayout(
                column_span=_layout_from_widget(widget).column_span,
                order=item.order,
                use_snapshot=_layout_from_widget(widget).use_snapshot,
                x=_layout_from_widget(widget).x,
                y=_layout_from_widget(widget).y,
                width=_layout_from_widget(widget).width,
                height=_layout_from_widget(widget).height,
            ),
            insight_index=_insight_index_from_widget(widget),
        )
        db.add(widget)

    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(dashboard)
    db.commit()
    return get_dashboard_detail(db, current_user=current_user, dashboard_id=dashboard.id)


def delete_dashboard_widget(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    widget_id: int,
) -> None:
    owned = _get_owned_widget(db, dashboard_id=dashboard_id, widget_id=widget_id, user_id=current_user.id)
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard widget not found")
    dashboard, widget = owned
    db.delete(widget)
    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(dashboard)
    db.commit()


def update_dashboard_refresh_settings(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    payload: DashboardRefreshSettingsRequest,
) -> DashboardDetail:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    dashboard.auto_refresh_enabled = payload.auto_refresh_enabled
    dashboard.refresh_interval_minutes = payload.refresh_interval_minutes if payload.auto_refresh_enabled else None
    dashboard.next_refresh_at = compute_next_refresh_at(dashboard)
    dashboard.freshness_status = compute_freshness_status(dashboard)
    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(dashboard)
    db.commit()
    return get_dashboard_detail(db=db, current_user=current_user, dashboard_id=dashboard.id)
