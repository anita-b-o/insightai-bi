from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.observability import log_event
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget
from app.models.dataset import Dataset
from app.models.dataset_insight_run import DatasetInsightRun
from app.models.query_history import QueryHistory
from app.models.user import User
from app.schemas.ai import AIInsight, AIQueryResponse
from app.schemas.dashboard import DashboardDetail
from app.services.dashboard_freshness_service import compute_freshness_status, compute_next_refresh_at, is_refresh_lock_active
from app.services.ai_service import build_visualization_suggestion
from app.services.dashboard_service import _get_owned_dashboard, _get_owned_widget, _insight_index_from_widget, _serialize_single_widget, get_dashboard_detail
from app.services.insight_service import generate_and_save_insights
from app.services.query_executor import ensure_dataset_queryable, execute_dataset_query
from app.services.sql_analysis_service import analyze_sql

logger = logging.getLogger("app.dashboard.execution")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _refresh_lock_expires_at(now: datetime | None = None) -> datetime:
    current = now or _utc_now()
    return current + timedelta(seconds=settings.dashboard_refresh_lock_timeout_seconds)


def try_acquire_dashboard_refresh_lock(db: Session, *, dashboard_id: int) -> bool:
    now = _utc_now()
    result = db.execute(
        update(Dashboard)
        .where(
            Dashboard.id == dashboard_id,
            or_(
                Dashboard.refresh_in_progress.is_(False)
                , Dashboard.refresh_lock_expires_at.is_(None)
                , Dashboard.refresh_lock_expires_at <= now
            ),
        )
        .values(
            refresh_in_progress=True,
            refresh_started_at=now,
            refresh_finished_at=None,
            refresh_lock_expires_at=_refresh_lock_expires_at(now),
            last_refresh_attempt_at=now,
        )
    )
    db.commit()
    return bool(result.rowcount)


def release_dashboard_refresh_lock(
    db: Session,
    *,
    dashboard_id: int,
    error_message: str | None = None,
) -> None:
    db.execute(
        update(Dashboard)
        .where(Dashboard.id == dashboard_id)
        .values(
            refresh_in_progress=False,
            refresh_finished_at=_utc_now(),
            refresh_lock_expires_at=None,
            last_refresh_error=error_message[:500] if error_message else None,
        )
    )
    db.commit()


def reconcile_expired_refresh_lock(db: Session, *, dashboard_id: int) -> None:
    now = _utc_now()
    db.execute(
        update(Dashboard)
        .where(
            Dashboard.id == dashboard_id,
            Dashboard.refresh_in_progress.is_(True),
            Dashboard.refresh_lock_expires_at.is_not(None),
            Dashboard.refresh_lock_expires_at <= now,
        )
        .values(
            refresh_in_progress=False,
            refresh_finished_at=now,
            refresh_lock_expires_at=None,
            last_refresh_error="Refresh lock expired before completion",
        )
    )
    db.commit()


def _get_owned_dataset(db: Session, *, user_id: int, dataset_id: int) -> Dataset | None:
    statement = (
        select(Dataset)
        .options(joinedload(Dataset.columns))
        .where(Dataset.id == dataset_id, Dataset.owner_id == user_id)
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _get_owned_query_history(db: Session, *, user_id: int, query_id: int) -> QueryHistory | None:
    statement = (
        select(QueryHistory)
        .options(joinedload(QueryHistory.result), joinedload(QueryHistory.dataset).joinedload(Dataset.columns))
        .where(
            QueryHistory.id == query_id,
            QueryHistory.user_id == user_id,
            QueryHistory.deleted_at.is_(None),
        )
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _get_owned_insight_run(db: Session, *, user_id: int, run_id: int) -> DatasetInsightRun | None:
    statement = (
        select(DatasetInsightRun)
        .options(joinedload(DatasetInsightRun.dataset).joinedload(Dataset.columns))
        .where(DatasetInsightRun.id == run_id, DatasetInsightRun.user_id == user_id)
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _config_from_visualization(response: AIQueryResponse | None = None, insight: AIInsight | None = None) -> dict[str, object] | None:
    suggestion = None
    if response is not None:
        suggestion = response.visualization_suggestion
    elif insight is not None:
        suggestion = insight.visualization_suggestion
    if suggestion is None:
        return None
    return {key: value for key, value in suggestion.model_dump(mode="json").items() if value is not None}


def _chart_type_from_query_response(response: AIQueryResponse) -> str:
    suggestion_type = response.visualization_suggestion.type if response.visualization_suggestion else response.chart_suggestion
    return suggestion_type if suggestion_type in {"bar", "line", "pie", "scatter", "table"} else "table"


def _chart_type_from_insight(insight: AIInsight) -> str:
    if insight.chart_type in {"bar", "line", "pie", "scatter", "table"}:
        return insight.chart_type
    if insight.chart_suggestion in {"bar", "line", "pie", "scatter", "table"}:
        return insight.chart_suggestion
    return "table"


def _match_insight(
    *,
    widget: DashboardWidget,
    previous_run: DatasetInsightRun | None,
    refreshed_insights: list[AIInsight],
) -> AIInsight | None:
    insight_index = _insight_index_from_widget(widget)
    previous_insight: AIInsight | None = None
    if previous_run is not None and insight_index is not None:
        items = previous_run.insights_json or []
        if 0 <= insight_index < len(items):
            previous_insight = AIInsight.model_validate(items[insight_index])

    if previous_insight is not None:
        for insight in refreshed_insights:
            if (
                insight.type == previous_insight.type
                and insight.metric == previous_insight.metric
                and insight.dimension == previous_insight.dimension
            ):
                return insight

    if insight_index is not None and 0 <= insight_index < len(refreshed_insights):
        return refreshed_insights[insight_index]

    if previous_insight is not None:
        for insight in refreshed_insights:
            if insight.type == previous_insight.type:
                return insight

    return refreshed_insights[0] if refreshed_insights else None


def _refresh_query_widget(db: Session, *, widget: DashboardWidget, dashboard: Dashboard, current_user: User) -> None:
    query_record = (
        _get_owned_query_history(db, user_id=current_user.id, query_id=widget.source_id)
        if widget.source_id is not None
        else None
    )
    dataset = None
    if query_record is not None:
        dataset = query_record.dataset
    elif dashboard.dataset_id is not None:
        dataset = _get_owned_dataset(db, user_id=current_user.id, dataset_id=dashboard.dataset_id)

    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found for query widget")
    sql = widget.query_sql or (query_record.generated_sql if query_record is not None else None)
    if not sql:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query widget has no SQL to execute")

    dataset = ensure_dataset_queryable(db=db, dataset=dataset)
    columns, rows = execute_dataset_query(db=db, dataset=dataset, sql=sql)
    sql_analysis = analyze_sql(sql)
    response = AIQueryResponse(
        answer=f"Refreshed {len(rows)} rows for dashboard widget.",
        sql=sql,
        rows=rows,
        columns=columns,
        sql_analysis=sql_analysis,
    )
    response.visualization_suggestion = build_visualization_suggestion(
        columns=columns,
        rows=rows,
        dataset=dataset,
        sql_analysis=sql_analysis,
    )
    response.chart_suggestion = _chart_type_from_query_response(response)

    widget.query_sql = sql
    widget.data_json = rows
    widget.chart_type = _chart_type_from_query_response(response)
    widget.config_json = _config_from_visualization(response=response)


def _refresh_insight_widget(db: Session, *, widget: DashboardWidget, dashboard: Dashboard, current_user: User) -> None:
    previous_run = (
        _get_owned_insight_run(db, user_id=current_user.id, run_id=widget.source_id)
        if widget.source_id is not None
        else None
    )
    dataset_id = previous_run.dataset_id if previous_run is not None else dashboard.dataset_id
    if dataset_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found for insight widget")

    refreshed_response = generate_and_save_insights(db=db, current_user=current_user, dataset_id=dataset_id)
    matched_insight = _match_insight(
        widget=widget,
        previous_run=previous_run,
        refreshed_insights=refreshed_response.insights,
    )
    if matched_insight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching insight available after refresh")

    widget.source_id = refreshed_response.run_id
    widget.data_json = matched_insight.rows or matched_insight.data
    widget.chart_type = _chart_type_from_insight(matched_insight)
    widget.config_json = _config_from_visualization(insight=matched_insight)


def _refresh_snapshot_widget(widget: DashboardWidget) -> None:
    if widget.data_json is None and widget.snapshot_json is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Snapshot widget has no saved data")


def execute_widget(db: Session, *, widget: DashboardWidget, dashboard: Dashboard, current_user: User) -> DashboardWidget:
    previous_data = widget.data_json
    previous_config = widget.config_json
    previous_chart_type = widget.chart_type
    previous_query_sql = widget.query_sql
    previous_source_id = widget.source_id
    previous_error = widget.error_message

    try:
        execution_type = widget.execution_type or (
            "query" if widget.source_type == "query" else "insight" if widget.source_type == "insight" else "snapshot"
        )
        if execution_type == "query":
            _refresh_query_widget(db, widget=widget, dashboard=dashboard, current_user=current_user)
        elif execution_type == "insight":
            _refresh_insight_widget(db, widget=widget, dashboard=dashboard, current_user=current_user)
        else:
            _refresh_snapshot_widget(widget)

        widget.last_run_at = datetime.now(timezone.utc)
        widget.error_message = None
        widget.execution_status = "success"
        return widget
    except HTTPException as exc:
        widget.data_json = previous_data
        widget.config_json = previous_config
        widget.chart_type = previous_chart_type
        widget.query_sql = previous_query_sql
        widget.source_id = previous_source_id
        widget.error_message = str(exc.detail)
        widget.execution_status = "failed"
        if previous_error and not widget.error_message:
            widget.error_message = previous_error
        return widget
    except Exception as exc:
        widget.data_json = previous_data
        widget.config_json = previous_config
        widget.chart_type = previous_chart_type
        widget.query_sql = previous_query_sql
        widget.source_id = previous_source_id
        widget.error_message = str(exc)
        widget.execution_status = "failed"
        if previous_error and not widget.error_message:
            widget.error_message = previous_error
        return widget


def refresh_dashboard_widget(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    widget_id: int,
) -> DashboardWidget:
    owned = _get_owned_widget(db, dashboard_id=dashboard_id, widget_id=widget_id, user_id=current_user.id)
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard widget not found")
    dashboard, widget = owned
    if is_refresh_lock_active(dashboard):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dashboard refresh already in progress. Retry when the current refresh completes.",
        )

    execute_widget(db, widget=widget, dashboard=dashboard, current_user=current_user)
    dashboard.updated_at = datetime.now(timezone.utc)
    db.add(widget)
    db.add(dashboard)
    db.commit()
    db.refresh(widget)
    return widget


def refresh_dashboard_widget_read(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    widget_id: int,
):
    widget = refresh_dashboard_widget(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard_id,
        widget_id=widget_id,
    )
    return _serialize_single_widget(db, user=current_user, widget=widget)


def refresh_dashboard(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    lock_acquired: bool = False,
) -> DashboardDetail:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    if not lock_acquired and not try_acquire_dashboard_refresh_lock(db, dashboard_id=dashboard.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dashboard refresh already in progress. Retry when the current refresh completes.",
        )

    success_count = 0
    failed_count = 0
    refresh_error: str | None = None
    started_at = _utc_now()

    try:
        for widget in dashboard.widgets:
            execute_widget(db, widget=widget, dashboard=dashboard, current_user=current_user)
            if getattr(widget, "execution_status", None) == "success":
                success_count += 1
            else:
                failed_count += 1
            db.add(widget)

        now = _utc_now()
        if success_count > 0:
            dashboard.last_successful_refresh_at = now
            dashboard.next_refresh_at = compute_next_refresh_at(dashboard)
            dashboard.freshness_status = "fresh" if failed_count == 0 else "stale"
        else:
            dashboard.freshness_status = "failed"
            dashboard.next_refresh_at = compute_next_refresh_at(dashboard)
        dashboard.freshness_status = compute_freshness_status(dashboard)
        dashboard.updated_at = now
        dashboard.last_refresh_error = None if failed_count == 0 else f"{failed_count} widget(s) failed during refresh"
        db.add(dashboard)
        db.commit()
        log_event(
            logger,
            logging.INFO,
            "dashboard_refresh_finished",
            dashboard_id=dashboard.id,
            user_id=current_user.id,
            status="success" if failed_count == 0 else "partial",
            duration_ms=int((_utc_now() - started_at).total_seconds() * 1000),
            success_count=success_count,
            failed_count=failed_count,
        )
        return get_dashboard_detail(db=db, current_user=current_user, dashboard_id=dashboard.id)
    except Exception as exc:
        db.rollback()
        refresh_error = str(getattr(exc, "detail", str(exc)))
        log_event(
            logger,
            logging.ERROR,
            "dashboard_refresh_failed",
            dashboard_id=dashboard.id,
            user_id=current_user.id,
            status="failed",
            duration_ms=int((_utc_now() - started_at).total_seconds() * 1000),
            error_code="dashboard_refresh_failed",
        )
        raise
    finally:
        try:
            if not lock_acquired:
                release_dashboard_refresh_lock(db, dashboard_id=dashboard.id, error_message=refresh_error)
        except Exception:
            db.rollback()
