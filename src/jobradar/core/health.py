"""Dependency checks used by the readiness endpoint."""

import socket

from sqlalchemy import text

from jobradar.core.db import get_engine
from jobradar.core.queue import celery_app
from jobradar.core.settings import get_settings


def check_database() -> None:
    """Raise if the database cannot run a trivial query."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def check_redis() -> None:
    """Raise if Redis does not answer PING within the health-check timeout."""
    settings = get_settings()
    with socket.create_connection(
        (settings.redis_host, settings.redis_port),
        timeout=settings.health_check_timeout_seconds,
    ) as connection:
        connection.sendall(b"*1\r\n$4\r\nPING\r\n")
        response = connection.recv(64)
    if response != b"+PONG\r\n":
        raise ConnectionError("Redis returned an unexpected health-check response")


def check_queue() -> None:
    """Raise if the Celery broker connection cannot be established."""
    with celery_app.connection_for_read() as connection:
        connection.ensure_connection(max_retries=0)
