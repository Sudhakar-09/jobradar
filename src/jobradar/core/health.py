import socket

from sqlalchemy import text

from jobradar.core.db import get_engine
from jobradar.core.settings import get_settings
from jobradar.tasks.celery_app import celery_app


def check_database() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def check_redis() -> None:
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
    with celery_app.connection_for_read() as connection:
        connection.ensure_connection(max_retries=0)