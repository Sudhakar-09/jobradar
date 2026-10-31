"""FastAPI application: middleware and health/readiness endpoints."""

from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from jobradar.core.health import check_database, check_queue, check_redis
from jobradar.core.logging import configure_logging
from jobradar.core.settings import get_settings

configure_logging(get_settings().log_level)
logger = structlog.get_logger(__name__)
app = FastAPI(title=get_settings().app_name)


@app.middleware("http")
async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Bind a correlation ID to the request's log context and echo it in the response."""
    request_id = request.headers.get("X-Correlation-ID")
    try:
        correlation_id = str(UUID(request_id)) if request_id else str(uuid4())
    except ValueError:
        correlation_id = str(uuid4())

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.clear_contextvars()
    response.headers["X-Correlation-ID"] = correlation_id
    return response


def _check_dependency(name: str, check: Callable[[], None]) -> str:
    try:
        check()
    except Exception:
        logger.exception("health.check_failed", dependency=name)
        return "unavailable"
    return "ok"


@app.get("/health", tags=["health"])
def health() -> JSONResponse:
    """Report that the process is alive."""
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.get("/ready", tags=["health"])
def ready() -> JSONResponse:
    """Report whether the database, Redis and the queue are reachable."""
    checks: dict[str, str] = {
        "database": _check_dependency("database", check_database),
        "redis": _check_dependency("redis", check_redis),
        "queue": _check_dependency("queue", check_queue),
    }
    healthy = all(status == "ok" for status in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )
