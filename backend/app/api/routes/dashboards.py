from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardBulkSnapshotRefreshResponse,
    DashboardCreateRequest,
    DashboardDetail,
    DashboardNarrative,
    DashboardRefreshSettingsRequest,
    DashboardShareLinkCreateRequest,
    DashboardShareLinkCreateResponse,
    DashboardShareLinkRead,
    DashboardSnapshotModeRequest,
    DashboardSummary,
    DashboardUpdateRequest,
    DashboardWidgetCreateRequest,
    DashboardWidgetRead,
    DashboardWidgetReorderItem,
    DashboardWidgetUpdateRequest,
)
from app.services.dashboard_service import (
    create_dashboard,
    create_dashboard_widget,
    delete_dashboard,
    delete_dashboard_widget,
    refresh_all_dashboard_widget_snapshots,
    refresh_dashboard_widget_snapshot,
    get_dashboard_detail,
    list_dashboards,
    reorder_dashboard_widgets,
    set_dashboard_snapshot_mode,
    update_dashboard,
    update_dashboard_refresh_settings,
    update_dashboard_widget,
)
from app.services.dashboard_execution_service import refresh_dashboard, refresh_dashboard_widget_read
from app.services.dashboard_narrative_service import get_dashboard_narrative
from app.services.dashboard_share_service import (
    create_dashboard_share_link,
    list_dashboard_share_links,
    revoke_dashboard_share_link,
)

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.post("", response_model=DashboardDetail, status_code=status.HTTP_201_CREATED)
def create_dashboard_route(
    payload: DashboardCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return create_dashboard(db=db, current_user=current_user, payload=payload)


@router.get("", response_model=list[DashboardSummary])
def list_dashboards_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DashboardSummary]:
    return list_dashboards(db=db, current_user=current_user)


@router.get("/{dashboard_id}", response_model=DashboardDetail)
def get_dashboard_route(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return get_dashboard_detail(db=db, current_user=current_user, dashboard_id=dashboard_id)


@router.get("/{dashboard_id}/narrative", response_model=DashboardNarrative)
def get_dashboard_narrative_route(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardNarrative:
    return get_dashboard_narrative(db=db, current_user=current_user, dashboard_id=dashboard_id)


@router.post("/{dashboard_id}/share-links", response_model=DashboardShareLinkCreateResponse, status_code=status.HTTP_201_CREATED)
def create_dashboard_share_link_route(
    dashboard_id: int,
    payload: DashboardShareLinkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardShareLinkCreateResponse:
    return create_dashboard_share_link(db=db, current_user=current_user, dashboard_id=dashboard_id, payload=payload)


@router.get("/{dashboard_id}/share-links", response_model=list[DashboardShareLinkRead])
def list_dashboard_share_links_route(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DashboardShareLinkRead]:
    return list_dashboard_share_links(db=db, current_user=current_user, dashboard_id=dashboard_id)


@router.delete("/{dashboard_id}/share-links/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_share_link_route(
    dashboard_id: int,
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    revoke_dashboard_share_link(db=db, current_user=current_user, dashboard_id=dashboard_id, share_id=share_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{dashboard_id}", response_model=DashboardDetail)
def update_dashboard_route(
    dashboard_id: int,
    payload: DashboardUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return update_dashboard(db=db, current_user=current_user, dashboard_id=dashboard_id, payload=payload)


@router.patch("/{dashboard_id}/refresh-settings", response_model=DashboardDetail)
def update_dashboard_refresh_settings_route(
    dashboard_id: int,
    payload: DashboardRefreshSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return update_dashboard_refresh_settings(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard_id,
        payload=payload,
    )


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_route(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_dashboard(db=db, current_user=current_user, dashboard_id=dashboard_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{dashboard_id}/widgets", response_model=DashboardDetail, status_code=status.HTTP_201_CREATED)
def create_dashboard_widget_route(
    dashboard_id: int,
    payload: DashboardWidgetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return create_dashboard_widget(db=db, current_user=current_user, dashboard_id=dashboard_id, payload=payload)


@router.patch("/{dashboard_id}/widgets/reorder", response_model=DashboardDetail)
def reorder_dashboard_widgets_route(
    dashboard_id: int,
    payload: list[DashboardWidgetReorderItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return reorder_dashboard_widgets(db=db, current_user=current_user, dashboard_id=dashboard_id, items=payload)


@router.patch("/{dashboard_id}/widgets/snapshot-mode", response_model=DashboardDetail)
def set_dashboard_snapshot_mode_route(
    dashboard_id: int,
    payload: DashboardSnapshotModeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return set_dashboard_snapshot_mode(db=db, current_user=current_user, dashboard_id=dashboard_id, payload=payload)


@router.post("/{dashboard_id}/widgets/snapshots/refresh", response_model=DashboardBulkSnapshotRefreshResponse)
def refresh_all_dashboard_widget_snapshots_route(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardBulkSnapshotRefreshResponse:
    return refresh_all_dashboard_widget_snapshots(db=db, current_user=current_user, dashboard_id=dashboard_id)


@router.post("/{dashboard_id}/refresh", response_model=DashboardDetail)
def refresh_dashboard_route(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return refresh_dashboard(db=db, current_user=current_user, dashboard_id=dashboard_id)


@router.patch("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardDetail)
def update_dashboard_widget_route(
    dashboard_id: int,
    widget_id: int,
    payload: DashboardWidgetUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardDetail:
    return update_dashboard_widget(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard_id,
        widget_id=widget_id,
        payload=payload,
    )


@router.post("/{dashboard_id}/widgets/{widget_id}/snapshot/refresh", response_model=DashboardWidgetRead)
def refresh_dashboard_widget_snapshot_route(
    dashboard_id: int,
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardWidgetRead:
    return refresh_dashboard_widget_snapshot(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard_id,
        widget_id=widget_id,
    )


@router.post("/{dashboard_id}/widgets/{widget_id}/refresh", response_model=DashboardWidgetRead)
def refresh_dashboard_widget_route(
    dashboard_id: int,
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardWidgetRead:
    return refresh_dashboard_widget_read(
        db=db,
        current_user=current_user,
        dashboard_id=dashboard_id,
        widget_id=widget_id,
    )


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_widget_route(
    dashboard_id: int,
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_dashboard_widget(db=db, current_user=current_user, dashboard_id=dashboard_id, widget_id=widget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
