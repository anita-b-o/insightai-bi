from __future__ import annotations

import hashlib
import hmac
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import log_event
from app.db.session import get_db
from app.services.scheduler_invocation_service import (
    complete_scheduler_invocation,
    create_scheduler_invocation,
    fail_scheduler_invocation,
)
from app.workers.dashboard_refresh_worker import run_scheduled_dashboard_refresh_job

logger = logging.getLogger("app.internal.scheduler")

router = APIRouter(prefix="/internal", tags=["internal"])


def _validate_scheduler_request(*, timestamp: str | None, invocation_id: str | None, signature: str | None) -> str:
    if not settings.scheduler_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Scheduler is not configured")
    if not timestamp or not invocation_id or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler authentication")
    try:
        parsed_timestamp = int(timestamp)
        UUID(invocation_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler authentication") from None
    if abs(int(time.time()) - parsed_timestamp) > settings.scheduler_request_max_age_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler authentication")

    message = f"{timestamp}.{invocation_id}".encode("utf-8")
    expected_signature = hmac.new(
        settings.scheduler_secret.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler authentication")
    return invocation_id


@router.post("/scheduled-refresh/run")
def run_scheduled_refresh(
    x_scheduler_timestamp: str | None = Header(default=None),
    x_scheduler_invocation_id: str | None = Header(default=None),
    x_scheduler_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    invocation_id = _validate_scheduler_request(
        timestamp=x_scheduler_timestamp,
        invocation_id=x_scheduler_invocation_id,
        signature=x_scheduler_signature,
    )
    invocation, created = create_scheduler_invocation(db, invocation_id=invocation_id)
    if not created:
        return {
            "status": "already_processed",
            "invocation_id": invocation_id,
            "processed_count": invocation.processed_count,
        }

    started_at = time.perf_counter()
    log_event(logger, logging.INFO, "scheduled_refresh_started", invocation_id=invocation_id)
    try:
        summary = run_scheduled_dashboard_refresh_job(db)
        complete_scheduler_invocation(db, invocation=invocation, processed_count=summary["processed"])
        log_event(
            logger,
            logging.INFO,
            "scheduled_refresh_finished",
            invocation_id=invocation_id,
            processed_count=summary["processed"],
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            status="completed",
        )
        return {"status": "completed", "invocation_id": invocation_id, "processed_count": summary["processed"]}
    except Exception:
        db.rollback()
        fail_scheduler_invocation(db, invocation=invocation, error_message="Scheduled refresh cycle failed")
        log_event(
            logger,
            logging.ERROR,
            "scheduled_refresh_failed",
            invocation_id=invocation_id,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            status="failed",
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scheduled refresh failed") from None
