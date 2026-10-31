"""Integration test database: a throwaway pgvector Postgres migrated to head.

By default a container is started with testcontainers. If Docker is unavailable to
testcontainers (fallback for Windows), set JOBRADAR_TEST_DATABASE_URL to an empty database on the
compose services, e.g. ``postgresql+psycopg://jobradar:local_dev_only@localhost:5433/jobradar_test``.
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from alembic import command

ROOT = Path(__file__).resolve().parents[2]
POSTGRES_IMAGE = "pgvector/pgvector:0.8.0-pg16"
TRUNCATE_TABLES = (
    "alert_messages, alert_inboxes, company_suggestions, consents, settings_flags, audit_log, "
    "dead_letters, job_sources, jobs, source_runs, companies, users"
)


def alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session")
def make_alembic_config() -> Callable[[str], Config]:
    return alembic_config


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    override = os.environ.get("JOBRADAR_TEST_DATABASE_URL")
    if override:
        yield override
        return
    try:
        container = PostgresContainer(POSTGRES_IMAGE, driver="psycopg").start()
    except Exception as exc:  # noqa: BLE001 -- any Docker failure means: skip with the reason
        pytest.skip(
            f"Docker unavailable for testcontainers ({exc}); set JOBRADAR_TEST_DATABASE_URL"
        )
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture(scope="session")
def migrated_url(database_url: str) -> str:
    command.upgrade(alembic_config(database_url), "head")
    return database_url


@pytest.fixture(scope="session")
def admin_engine(migrated_url: str) -> Iterator[Engine]:
    """Superuser connection for seeding and inspection (bypasses RLS on purpose)."""
    engine = create_engine(migrated_url)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(admin_engine: Engine) -> None:
    with admin_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {TRUNCATE_TABLES} CASCADE"))


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, Any]]:
    options: dict[str, Any] = {}
    if sys.platform == "win32":  # psycopg async cannot use the Proactor loop
        options["loop_factory"] = asyncio.SelectorEventLoop
    return ("asyncio", options)


@pytest.fixture
async def session_factory(migrated_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_url)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()
