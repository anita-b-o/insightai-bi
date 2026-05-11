from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import SharedDashboardRead
from app.services.dashboard_share_service import get_shared_dashboard_by_token

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/dashboards/{token}", response_model=SharedDashboardRead)
def get_shared_dashboard_route(
    token: str,
    db: Session = Depends(get_db),
) -> SharedDashboardRead:
    return get_shared_dashboard_by_token(db=db, token=token)
