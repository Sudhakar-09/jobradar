import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar.core.db import system_session, user_session
from jobradar.core.logging import QUIET_LIBRARY_LOGGERS, REDACTED, quiet_library_loggers, redact_pii
from jobradar.core.scope import ClientKind, Role, UserScope, system_scope

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_redact_pii_drops_personal_keys_and_masks_emails() -> None:
    event = {
        "event": "notify.digest_sent",
        "email": "asha@example.org",
        "Full_Name": "Asha",
        "detail": "sent to asha@example.org at 08:00",
        "nested": {"phone": "+971500000000", "count": 3, "note": "cc b@example.com"},
        "items": ["x@example.com", 5],
        "user_id": "0192f1d2-0000-7000-8000-000000000000",
    }

    result = redact_pii(None, "info", event)

    assert result["email"] == REDACTED
    assert result["Full_Name"] == REDACTED
    assert result["detail"] == f"sent to {REDACTED} at 08:00"
    assert result["nested"] == {"phone": REDACTED, "count": 3, "note": f"cc {REDACTED}"}
    assert result["items"] == [REDACTED, 5]
    assert result["user_id"] == "0192f1d2-0000-7000-8000-000000000000"
    assert result["event"] == "notify.digest_sent"


class FakeSession:
    def __init__(self) -> None:
        self.executed: list[tuple[str, dict[str, Any]]] = []
        self.committed = False

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        self.executed.append((str(statement), params or {}))

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[None]:
        yield
        self.committed = True


def fake_factory(session: FakeSession) -> async_sessionmaker[AsyncSession]:
    @asynccontextmanager
    async def open_session() -> AsyncIterator[FakeSession]:
        yield session

    return cast(async_sessionmaker[AsyncSession], open_session)


async def test_user_session_binds_the_user_for_row_level_security() -> None:
    session = FakeSession()
    scope = UserScope(user_id=UUID(int=7), roles=frozenset({Role.USER}), via=ClientKind.WEB)

    async with user_session(scope, factory=fake_factory(session)):
        pass

    assert session.executed[0][0] == 'SET LOCAL ROLE "jobradar_app"'
    statement, params = session.executed[1]
    assert "set_config('app.user_id'" in statement
    assert params == {"user_id": str(UUID(int=7))}
    assert session.committed


async def test_system_session_uses_corpus_role_and_binds_no_user() -> None:
    session = FakeSession()

    async with system_session(system_scope("discover_all"), factory=fake_factory(session)):
        pass

    assert session.executed == [('SET LOCAL ROLE "jobradar_corpus"', {})]
    assert session.committed


def test_library_loggers_that_print_full_urls_are_quiet() -> None:
    quiet_library_loggers(logging.DEBUG)

    for name in QUIET_LIBRARY_LOGGERS:
        library_logger = logging.getLogger(name)  # noqa: TID251 -- inspecting a library logger
        assert library_logger.getEffectiveLevel() >= logging.WARNING
