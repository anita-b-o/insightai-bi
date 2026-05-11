from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget
from app.models.user import User
from app.schemas.dashboard import DashboardNarrative
from app.services.dashboard_service import _get_owned_dashboard
from app.services.openai_service import request_openai_text

logger = logging.getLogger(__name__)


def _widget_title(widget: DashboardWidget) -> str:
    title = getattr(widget, "title", None)
    if isinstance(title, str) and title.strip():
        return title.strip()
    return f"Widget #{getattr(widget, 'id', '?')}"


def _widget_rows(widget: DashboardWidget) -> list[dict[str, object]]:
    data = getattr(widget, "data_json", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _has_usable_data(widget: DashboardWidget) -> bool:
    rows = _widget_rows(widget)
    if rows:
        return True
    data = getattr(widget, "data_json", None)
    return isinstance(data, dict) and len(data) > 0


def _is_stale_or_failed(widget: DashboardWidget) -> bool:
    return bool(
        getattr(widget, "execution_status", "never_run") in {"failed", "never_run"}
        or getattr(widget, "source_changed", False)
        or (getattr(widget, "execution_type", "snapshot") == "query" and not getattr(widget, "query_sql", None))
        or not _has_usable_data(widget)
    )


def _truncate(items: Iterable[str], *, limit: int = 5) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        results.append(normalized)
        seen.add(normalized)
        if len(results) >= limit:
            break
    return results


def _build_summary(dashboard: Dashboard, widgets: list[DashboardWidget]) -> str:
    if not widgets:
        return f"The dashboard {dashboard.name} is ready, but it does not contain widgets yet."

    successful_widgets = [widget for widget in widgets if getattr(widget, "execution_status", "never_run") == "success"]
    failed_widgets = [widget for widget in widgets if getattr(widget, "execution_status", "never_run") == "failed"]
    empty_widgets = [widget for widget in widgets if not _has_usable_data(widget)]

    parts = [f"The dashboard {dashboard.name} contains {len(widgets)} widgets."]
    if successful_widgets:
        parts.append(f"{len(successful_widgets)} widget{'s' if len(successful_widgets) != 1 else ''} are providing usable results.")
    if failed_widgets:
        parts.append(f"{len(failed_widgets)} widget{'s' if len(failed_widgets) != 1 else ''} currently failed to execute.")
    if empty_widgets and len(empty_widgets) != len(widgets):
        parts.append(f"{len(empty_widgets)} widget{'s' if len(empty_widgets) != 1 else ''} are present but still empty.")
    return " ".join(parts)


def _build_key_findings(widgets: list[DashboardWidget]) -> list[str]:
    findings: list[str] = []
    for widget in widgets:
        if getattr(widget, "execution_status", "never_run") != "success":
            continue
        title = _widget_title(widget)
        chart_type = getattr(widget, "chart_type", None) or getattr(widget, "type", "widget")
        rows = _widget_rows(widget)
        row_count = len(rows)
        source_type = getattr(widget, "source_type", "manual")
        findings.append(
            f"{title} is active as a {chart_type} {source_type} widget with {row_count} row{'s' if row_count != 1 else ''} of current data."
        )
    return _truncate(findings, limit=5)


def _build_risks_or_caveats(widgets: list[DashboardWidget]) -> list[str]:
    caveats: list[str] = []
    failed_widgets = [widget for widget in widgets if getattr(widget, "execution_status", "never_run") == "failed"]
    if failed_widgets:
        caveats.append(
            f"{len(failed_widgets)} widget{'s' if len(failed_widgets) != 1 else ''} failed to refresh and may be showing stale information."
        )

    never_run_widgets = [widget for widget in widgets if getattr(widget, "execution_status", "never_run") == "never_run"]
    if never_run_widgets:
        caveats.append(
            f"{len(never_run_widgets)} widget{'s' if len(never_run_widgets) != 1 else ''} have never been executed yet."
        )

    empty_widgets = [widget for widget in widgets if not _has_usable_data(widget)]
    if empty_widgets:
        caveats.append(
            f"{len(empty_widgets)} widget{'s' if len(empty_widgets) != 1 else ''} currently have no usable data to display."
        )

    query_without_sql = [
        widget for widget in widgets if getattr(widget, "execution_type", "snapshot") == "query" and not getattr(widget, "query_sql", None)
    ]
    if query_without_sql:
        caveats.append(
            f"{len(query_without_sql)} query widget{'s' if len(query_without_sql) != 1 else ''} cannot be refreshed because SQL is missing."
        )

    return _truncate(caveats, limit=4)


def _build_recommended_next_actions(widgets: list[DashboardWidget]) -> list[str]:
    actions: list[str] = []
    if any(getattr(widget, "execution_status", "never_run") == "failed" for widget in widgets):
        actions.append("Review failed widgets and retry their refresh to restore complete dashboard coverage.")
    if any(getattr(widget, "execution_status", "never_run") == "never_run" for widget in widgets):
        actions.append("Run the dashboard refresh so every widget has an initial execution state.")
    if any(getattr(widget, "execution_type", "snapshot") == "query" and not getattr(widget, "query_sql", None) for widget in widgets):
        actions.append("Update query widgets that are missing SQL so they can be refreshed automatically.")
    if any(not _has_usable_data(widget) for widget in widgets):
        actions.append("Inspect empty widgets and confirm their source data still returns records.")
    if any(getattr(widget, "source_type", "manual") == "insight" for widget in widgets):
        actions.append("Refresh insight widgets after major dataset changes to keep the dashboard narrative aligned with current findings.")
    if not actions:
        actions.append("Refresh the dashboard regularly and review the highest-signal widgets first.")
    return _truncate(actions, limit=4)


def _build_stale_or_failed_widgets(widgets: list[DashboardWidget]) -> list[str]:
    messages: list[str] = []
    for widget in widgets:
        if not _is_stale_or_failed(widget):
            continue
        title = _widget_title(widget)
        if getattr(widget, "execution_status", "never_run") == "failed":
            reason = getattr(widget, "error_message", None) or "Execution failed"
            messages.append(f"{title}: {reason}")
        elif getattr(widget, "execution_status", "never_run") == "never_run":
            messages.append(f"{title}: widget has not been executed yet")
        elif getattr(widget, "source_changed", False):
            messages.append(f"{title}: source changed since the last saved state")
        elif getattr(widget, "execution_type", "snapshot") == "query" and not getattr(widget, "query_sql", None):
            messages.append(f"{title}: query SQL is missing")
        else:
            messages.append(f"{title}: widget has no usable data")
    return _truncate(messages, limit=6)


def _polish_summary(narrative: DashboardNarrative) -> DashboardNarrative:
    if not settings.openai_api_key or not narrative.summary.strip():
        return narrative
    try:
        polished = asyncio.run(
            request_openai_text(
                system_prompt=(
                    "You are a BI analyst. Rewrite the provided dashboard summary as one concise executive paragraph. "
                    "Preserve facts. Do not invent findings. Do not use markdown."
                ),
                user_prompt=(
                    f"Summary: {narrative.summary}\n"
                    f"Key findings: {narrative.key_findings}\n"
                    f"Caveats: {narrative.risks_or_caveats}\n"
                    f"Actions: {narrative.recommended_next_actions}"
                ),
                error_prefix="Could not polish dashboard narrative",
            )
        ).strip()
    except Exception:
        logger.exception("dashboard_narrative_polish_failed")
        return narrative
    if polished:
        narrative.summary = polished
    return narrative


def generate_dashboard_narrative(dashboard: Dashboard, widgets: list[DashboardWidget]) -> DashboardNarrative:
    narrative = DashboardNarrative(
        summary=_build_summary(dashboard, widgets),
        key_findings=_build_key_findings(widgets),
        risks_or_caveats=_build_risks_or_caveats(widgets),
        recommended_next_actions=_build_recommended_next_actions(widgets),
        stale_or_failed_widgets=_build_stale_or_failed_widgets(widgets),
    )
    return _polish_summary(narrative)


def get_dashboard_narrative(db: Session, *, current_user: User, dashboard_id: int) -> DashboardNarrative:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    widgets = list(getattr(dashboard, "widgets", []) or [])
    return generate_dashboard_narrative(dashboard, widgets)
