import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import log_event
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")
logger = logging.getLogger("app.auth.deps")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    request_id = getattr(request.state, "request_id", "unknown")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            log_event(logger, logging.WARNING, "auth_token_invalid", request_id=request_id, error_code="missing_subject")
            raise credentials_exception
    except JWTError as exc:
        log_event(logger, logging.WARNING, "auth_token_invalid", request_id=request_id, error_code="decode_failed")
        raise credentials_exception from exc

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth_token_invalid",
            request_id=request_id,
            error_code="invalid_subject",
            subject=subject,
        )
        raise credentials_exception from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        log_event(
            logger,
            logging.WARNING,
            "auth_token_invalid",
            request_id=request_id,
            error_code="user_not_found" if user is None else "user_inactive",
            subject=subject,
        )
        raise credentials_exception
    log_event(logger, logging.INFO, "auth_token_resolved", request_id=request_id, user_id=user.id)
    return user
