from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.observability import log_event
from app.models.dashboard import Dashboard
from app.models.dashboard_share_link import DashboardShareLink
from app.models.dashboard_widget import DashboardWidget
from app.models.user import User
from app.schemas.dashboard import (
    DashboardShareLinkCreateRequest,
    DashboardShareLinkCreateResponse,
    DashboardShareLinkRead,
    DashboardNarrative,
    DashboardLayout,
    SharedDashboardRead,
    SharedDashboardWidgetRead,
)
from app.services.dashboard_freshness_service import compute_freshness_status, compute_next_refresh_at
from app.services.dashboard_narrative_service import generate_dashboard_narrative
from app.services.dashboard_service import _get_owned_dashboard

logger = logging.getLogger("app.dashboard.share")


def _to_iso8601(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _parse_expires_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expires_at must be a valid ISO datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _share_signature(share_link: DashboardShareLink) -> str:
    if share_link.created_at is None:
        raise RuntimeError("Share link must have created_at before generating a token")
    payload = f"{share_link.id}:{share_link.dashboard_id}:{share_link.created_by_user_id}:{_to_iso8601(share_link.created_at)}"
    return hmac.new(settings.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_public_token(share_link: DashboardShareLink) -> str:
    return f"{share_link.id}.{_share_signature(share_link)}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_share_url(token: str) -> str:
    return f"/public/dashboards/{quote(token, safe='.')}"


def _serialize_share_link(share_link: DashboardShareLink) -> DashboardShareLinkRead:
    token = _build_public_token(share_link)
    return DashboardShareLinkRead(
        id=share_link.id,
        dashboard_id=share_link.dashboard_id,
        expires_at=_to_iso8601(share_link.expires_at) if share_link.expires_at else None,
        revoked_at=_to_iso8601(share_link.revoked_at) if share_link.revoked_at else None,
        created_at=_to_iso8601(share_link.created_at),
        share_url=_build_share_url(token),
    )


def _serialize_shared_widget(widget: DashboardWidget) -> SharedDashboardWidgetRead:
    layout = widget.layout or {}
    return SharedDashboardWidgetRead(
        id=widget.id,
        dashboard_id=widget.dashboard_id,
        type=widget.type,
        widget_type=widget.type,
        source_type=widget.source_type,
        execution_type=widget.execution_type or "snapshot",
        execution_status=widget.execution_status or "never_run",
        chart_type=widget.chart_type,
        layout=DashboardLayout(
            column_span=int(layout.get("column_span", 1)),
            order=int(layout.get("order", 0)),
            use_snapshot=bool(layout.get("use_snapshot", False)),
            x=int(layout.get("x", 0)),
            y=int(layout.get("y", 0)),
            width=int(layout.get("width", 6)),
            height=int(layout.get("height", 4)),
        ),
        title=widget.title,
        config_json=widget.config_json,
        data_json=widget.data_json,
        last_run_at=_to_iso8601(widget.last_run_at) if widget.last_run_at else None,
        error_message=widget.error_message,
        created_at=_to_iso8601(widget.created_at),
    )


def _serialize_shared_dashboard(dashboard: Dashboard) -> SharedDashboardRead:
    widgets = sorted(
        list(getattr(dashboard, "widgets", []) or []),
        key=lambda widget: ((widget.layout or {}).get("order", 0), widget.created_at),
    )
    narrative: DashboardNarrative = generate_dashboard_narrative(dashboard, widgets)
    freshness_status = compute_freshness_status(dashboard)
    next_refresh_at = compute_next_refresh_at(dashboard)
    return SharedDashboardRead(
        id=dashboard.id,
        name=dashboard.name,
        freshness_status=freshness_status,  # type: ignore[arg-type]
        last_successful_refresh_at=_to_iso8601(dashboard.last_successful_refresh_at) if dashboard.last_successful_refresh_at else None,
        next_refresh_at=_to_iso8601(next_refresh_at) if next_refresh_at else None,
        narrative=narrative,
        widgets=[_serialize_shared_widget(widget) for widget in widgets],
    )


def create_dashboard_share_link(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    payload: DashboardShareLinkCreateRequest,
) -> DashboardShareLinkCreateResponse:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    share_link = DashboardShareLink(
        dashboard_id=dashboard.id,
        created_by_user_id=current_user.id,
        expires_at=_parse_expires_at(payload.expires_at),
        token_hash=_hash_token(f"pending:{current_user.id}:{datetime.now(timezone.utc).isoformat()}"),
    )
    db.add(share_link)
    db.flush()
    db.refresh(share_link)
    token = _build_public_token(share_link)
    share_link.token_hash = _hash_token(token)
    db.add(share_link)
    db.commit()
    db.refresh(share_link)
    serialized = _serialize_share_link(share_link)
    log_event(
        logger,
        logging.INFO,
        "dashboard_share_link_created",
        dashboard_id=dashboard.id,
        user_id=current_user.id,
        share_id=share_link.id,
    )
    return DashboardShareLinkCreateResponse(**serialized.model_dump(), token=token)


def list_dashboard_share_links(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
) -> list[DashboardShareLinkRead]:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    statement = (
        select(DashboardShareLink)
        .where(DashboardShareLink.dashboard_id == dashboard.id)
        .order_by(DashboardShareLink.created_at.desc(), DashboardShareLink.id.desc())
    )
    return [_serialize_share_link(item) for item in db.execute(statement).scalars().all()]


def revoke_dashboard_share_link(
    db: Session,
    *,
    current_user: User,
    dashboard_id: int,
    share_id: int,
) -> None:
    dashboard = _get_owned_dashboard(db, dashboard_id=dashboard_id, user_id=current_user.id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    statement = select(DashboardShareLink).where(
        DashboardShareLink.id == share_id,
        DashboardShareLink.dashboard_id == dashboard.id,
    )
    share_link = db.execute(statement).scalar_one_or_none()
    if share_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    share_link.revoked_at = datetime.now(timezone.utc)
    db.add(share_link)
    db.commit()
    log_event(
        logger,
        logging.INFO,
        "dashboard_share_link_revoked",
        dashboard_id=dashboard.id,
        user_id=current_user.id,
        share_id=share_link.id,
    )


def get_shared_dashboard_by_token(db: Session, *, token: str) -> SharedDashboardRead:
    try:
        share_id_raw, _ = token.split(".", 1)
        share_id = int(share_id_raw)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared dashboard not found")

    statement = (
        select(DashboardShareLink)
        .options(joinedload(DashboardShareLink.dashboard).joinedload(Dashboard.widgets))
        .where(DashboardShareLink.id == share_id)
    )
    share_link = db.execute(statement).unique().scalar_one_or_none()
    if share_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared dashboard not found")

    expected_token = _build_public_token(share_link)
    if not hmac.compare_digest(share_link.token_hash, _hash_token(token)) or not hmac.compare_digest(expected_token, token):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared dashboard not found")
    if share_link.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared dashboard not found")
    if share_link.expires_at is not None and share_link.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared dashboard not found")

    log_event(
        logger,
        logging.INFO,
        "shared_dashboard_viewed",
        dashboard_id=share_link.dashboard_id,
        share_id=share_link.id,
    )
    return _serialize_shared_dashboard(share_link.dashboard)
