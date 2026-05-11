from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.core.observability import log_event
from app.core.sentry import init_sentry
from app.db import base as _models_registry  # noqa: F401
from app.db.session import SessionLocal
from app.models.dashboard import Dashboard
from app.services.dashboard_execution_service import (
    refresh_dashboard,
    release_dashboard_refresh_lock,
    reconcile_expired_refresh_lock,
    try_acquire_dashboard_refresh_lock,
)
from app.services.dashboard_freshness_service import find_dashboards_due_for_refresh
from app.services.worker_status_service import DASHBOARD_REFRESH_WORKER_NAME, update_worker_status

logger = logging.getLogger("app.workers.dashboard_refresh")
init_sentry("dashboard_refresh_worker")


def _try_mark_refresh_in_progress(db: Session, *, dashboard_id: int) -> bool:
    return try_acquire_dashboard_refresh_lock(db, dashboard_id=dashboard_id)


def _clear_refresh_in_progress(db: Session, *, dashboard_id: int, error_message: str | None = None) -> None:
    release_dashboard_refresh_lock(db, dashboard_id=dashboard_id, error_message=error_message)


def _recover_expired_locks(db: Session) -> int:
    now = datetime.now(timezone.utc)
    expired = (
        db.query(Dashboard)
        .filter(
            Dashboard.refresh_in_progress.is_(True),
            Dashboard.refresh_lock_expires_at.is_not(None),
            Dashboard.refresh_lock_expires_at <= now,
        )
        .all()
    )
    recovered = 0
    for dashboard in expired:
        reconcile_expired_refresh_lock(db, dashboard_id=dashboard.id)
        recovered += 1
    return recovered


def run_dashboard_refresh_cycle(db: Session) -> dict[str, int]:
    recovered_expired_locks = _recover_expired_locks(db)
    dashboards = find_dashboards_due_for_refresh(db)
    processed = 0
    succeeded = 0
    failed = 0
    skipped_locked = 0

    for dashboard in dashboards:
        if not _try_mark_refresh_in_progress(db, dashboard_id=dashboard.id):
            skipped_locked += 1
            log_event(
                logger,
                logging.INFO,
                "dashboard_refresh_worker_skipped_locked",
                dashboard_id=dashboard.id,
            )
            continue

        processed += 1
        started_at = time.perf_counter()
        refresh_error: str | None = None
        try:
            refresh_dashboard(
                db=db,
                current_user=SimpleNamespace(id=dashboard.user_id),
                dashboard_id=dashboard.id,
                lock_acquired=True,
            )
            succeeded += 1
        except Exception:
            failed += 1
            refresh_error = "Dashboard refresh failed during worker cycle"
            logger.exception(
                "dashboard_refresh_worker_dashboard_failed dashboard_id=%s user_id=%s",
                dashboard.id,
                dashboard.user_id,
            )
            db.rollback()
        finally:
            try:
                _clear_refresh_in_progress(db, dashboard_id=dashboard.id, error_message=refresh_error)
                log_event(
                    logger,
                    logging.INFO,
                    "dashboard_refresh_worker_dashboard_finished",
                    dashboard_id=dashboard.id,
                    user_id=dashboard.user_id,
                    duration_ms=int((time.perf_counter() - started_at) * 1000),
                    status="failed" if refresh_error else "success",
                )
            except Exception:
                db.rollback()
                logger.exception(
                    "dashboard_refresh_worker_clear_lock_failed",
                    extra={"dashboard_id": dashboard.id},
                )

    log_event(
        logger,
        logging.INFO,
        "dashboard_refresh_worker_cycle_complete",
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        skipped_locked=skipped_locked,
        due=len(dashboards),
        recovered_expired_locks=recovered_expired_locks,
    )
    return {
        "due": len(dashboards),
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "skipped_locked": skipped_locked,
        "recovered_expired_locks": recovered_expired_locks,
    }


def main() -> int:
    started_at = time.time()
    db = SessionLocal()
    try:
        update_worker_status(db, worker_name=DASHBOARD_REFRESH_WORKER_NAME)
        summary = run_dashboard_refresh_cycle(db)
        update_worker_status(
            db,
            worker_name=DASHBOARD_REFRESH_WORKER_NAME,
            cycle_at=datetime.now(timezone.utc),
            processed_count=summary["processed"],
            error_message=None,
        )
        log_event(
            logger,
            logging.INFO,
            "dashboard_refresh_worker_run_finished",
            duration_ms=int((time.time() - started_at) * 1000),
            summary=summary,
        )
        return 0
    except Exception as exc:
        db.rollback()
        update_worker_status(
            db,
            worker_name=DASHBOARD_REFRESH_WORKER_NAME,
            cycle_at=datetime.now(timezone.utc),
            processed_count=0,
            error_message=str(exc),
        )
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
