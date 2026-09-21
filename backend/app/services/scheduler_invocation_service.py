from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.scheduler_invocation import SchedulerInvocation


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_scheduler_invocation(db: Session, *, invocation_id: str) -> tuple[SchedulerInvocation, bool]:
    """Create the durable idempotency record, returning whether this caller owns it."""
    invocation = SchedulerInvocation(invocation_id=invocation_id, status="running", started_at=_utc_now())
    db.add(invocation)
    try:
        db.commit()
        db.refresh(invocation)
        return invocation, True
    except IntegrityError:
        db.rollback()
        existing = db.query(SchedulerInvocation).filter_by(invocation_id=invocation_id).one()
        return existing, False


def complete_scheduler_invocation(
    db: Session, *, invocation: SchedulerInvocation, processed_count: int
) -> SchedulerInvocation:
    invocation.status = "completed"
    invocation.processed_count = max(0, processed_count)
    invocation.completed_at = _utc_now()
    invocation.error_message = None
    db.add(invocation)
    db.commit()
    db.refresh(invocation)
    return invocation


def fail_scheduler_invocation(db: Session, *, invocation: SchedulerInvocation, error_message: str) -> None:
    invocation.status = "failed"
    invocation.error_message = error_message[:500]
    invocation.completed_at = _utc_now()
    db.add(invocation)
    db.commit()
