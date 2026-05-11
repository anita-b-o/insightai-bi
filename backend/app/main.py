import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from app.api.routes import ai, auth, dashboards, datasets, public, users
from app.core.config import settings
from app.core.observability import log_event
from app.core.sentry import init_sentry
from app.db.session import engine
from app.db.session import SessionLocal
from app.services.worker_status_service import get_worker_health_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app.main")
init_sentry("backend")

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(datasets.router, prefix=settings.api_v1_prefix)
app.include_router(ai.router, prefix=settings.api_v1_prefix)
app.include_router(dashboards.router, prefix=settings.api_v1_prefix)
app.include_router(public.router, prefix=settings.api_v1_prefix)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()
    log_event(
        logger,
        logging.INFO,
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    try:
        response = await call_next(request)
    except Exception:
        log_event(
            logger,
            logging.ERROR,
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        raise
    response.headers["X-Request-ID"] = request_id
    log_event(
        logger,
        logging.INFO,
        "request_finished",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )
    return response


@app.exception_handler(RequestValidationError)
async def log_validation_error(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    log_event(
        logger,
        logging.WARNING,
        "request_validation_error",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        error_count=len(exc.errors()),
    )
    response = await request_validation_exception_handler(request, exc)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    return {"status": "ok", "environment": settings.app_env.lower()}


@app.get("/health/worker", tags=["health"])
def worker_healthcheck() -> dict[str, str | int | None]:
    db = SessionLocal()
    try:
        return get_worker_health_snapshot(db)
    finally:
        db.close()
