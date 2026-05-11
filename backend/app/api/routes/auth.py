import logging
from collections import defaultdict
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.observability import log_event
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app.auth")
_attempt_window_started_at = monotonic()
_attempt_counts: defaultdict[str, int] = defaultdict(int)
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_ATTEMPTS = 10


def _consume_auth_attempt(key: str) -> None:
    global _attempt_window_started_at
    now = monotonic()
    if now - _attempt_window_started_at >= _RATE_LIMIT_WINDOW_SECONDS:
        _attempt_counts.clear()
        _attempt_window_started_at = now
    _attempt_counts[key] += 1
    if _attempt_counts[key] > _RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait and try again.",
        )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> User:
    request_id = getattr(request.state, "request_id", "unknown")
    rate_limit_key = f"register:{request.client.host if request.client else 'unknown'}:{payload.email.lower()}"
    _consume_auth_attempt(rate_limit_key)
    log_event(
        logger,
        logging.INFO,
        "auth_register_attempt",
        request_id=request_id,
        email=payload.email,
    )
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        log_event(
            logger,
            logging.WARNING,
            "auth_register_rejected",
            request_id=request_id,
            email=payload.email,
            error_code="email_already_registered",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_event(
        logger,
        logging.INFO,
        "auth_register_succeeded",
        request_id=request_id,
        user_id=user.id,
        email=user.email,
    )
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    request_id = getattr(request.state, "request_id", "unknown")
    rate_limit_key = f"login:{request.client.host if request.client else 'unknown'}:{payload.email.lower()}"
    _consume_auth_attempt(rate_limit_key)
    log_event(
        logger,
        logging.INFO,
        "auth_login_attempt",
        request_id=request_id,
        email=payload.email,
    )
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        log_event(
            logger,
            logging.WARNING,
            "auth_login_failed",
            request_id=request_id,
            email=payload.email,
            error_code="invalid_credentials",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    log_event(
        logger,
        logging.INFO,
        "auth_login_succeeded",
        request_id=request_id,
        user_id=user.id,
        email=user.email,
    )
    return Token(access_token=create_access_token(subject=str(user.id)))
