"""Database engines and scoped sessions (docs/lld/database.md §4).

Every transaction first switches into a login-less role with ``SET LOCAL ROLE`` (superusers
bypass row-level security, so the login itself is never used for application queries):
``jobradar_app`` for user work, ``jobradar_corpus`` for the shared job corpus. User-scoped
transactions then set ``app.user_id`` with ``set_config(..., true)`` (transaction local), which
the RLS policies compare against. A transaction that never sets it sees no user-owned rows.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Final

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from jobradar.core.scope import SystemScope, UserScope
from jobradar.core.settings import Settings, get_settings

SET_USER_SQL: Final = text("SELECT set_config('app.user_id', :user_id, true)")


def _connect_args(settings: Settings) -> dict[str, object]:
    return {
        "connect_timeout": settings.db_connect_timeout_seconds,
        "options": (
            f"-c statement_timeout={settings.db_statement_timeout_ms}"
            f" -c lock_timeout={settings.db_lock_timeout_ms}"
        ),
    }


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide synchronous engine (health checks, migrations)."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"connect_timeout": settings.health_check_timeout_seconds},
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    """Return the process-wide async engine with statement and lock timeouts."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url, connect_args=_connect_args(settings), pool_pre_ping=True
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory."""
    return async_sessionmaker(get_async_engine(), expire_on_commit=False)


async def set_role(session: AsyncSession, role: str) -> None:
    """Switch the current transaction into a database role (validated name, not user input)."""
    await session.execute(text(f'SET LOCAL ROLE "{role}"'))


async def set_user(session: AsyncSession, scope: UserScope) -> None:
    """Bind the current transaction to the scope's user for row-level security."""
    await session.execute(SET_USER_SQL, {"user_id": str(scope.user_id)})


@asynccontextmanager
async def user_session(
    scope: UserScope, *, factory: async_sessionmaker[AsyncSession] | None = None
) -> AsyncIterator[AsyncSession]:
    """Open one transaction bound to ``scope``'s user; commits on success, rolls back on error."""
    async with (factory or get_sessionmaker())() as session, session.begin():
        await set_role(session, get_settings().db_app_role)
        await set_user(session, scope)
        yield session


@asynccontextmanager
async def system_session(
    scope: SystemScope, *, factory: async_sessionmaker[AsyncSession] | None = None
) -> AsyncIterator[AsyncSession]:
    """Open one transaction for shared-corpus work; no user is bound, so RLS hides user rows."""
    del scope  # the scope documents intent; correlation is bound in the log context
    async with (factory or get_sessionmaker())() as session, session.begin():
        await set_role(session, get_settings().db_corpus_role)
        yield session
