import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger("app.users")


def mask_authorization_header(value: str | None) -> str:
    if not value:
        return "missing"
    if value.startswith("Bearer "):
        return "Bearer [REDACTED]"
    return "[REDACTED]"


@router.get("/me", response_model=UserRead)
def read_current_user(request: Request, current_user: User = Depends(get_current_user)) -> User:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "[AUTH ME] token=%s user_id=%s email=%s request_id=%s",
        mask_authorization_header(request.headers.get("authorization")),
        current_user.id,
        current_user.email,
        request_id,
    )
    return current_user
