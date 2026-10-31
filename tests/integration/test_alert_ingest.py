"""Alert-email ingestion against the test database (no Gmail: fixture messages)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import accounts, connectors, privacy
from jobradar.core.clock import FrozenClock
from jobradar.core.errors import ConflictError, ConsentRequiredError, NotFoundError
from jobradar.core.ids import new_id
from jobradar.core.scope import ClientKind, Role, UserScope
from tests.support.alerts import ALERT_FIXTURES, stream

pytestmark = [pytest.mark.integration, pytest.mark.anyio]
CLOCK = FrozenClock(datetime(2026, 10, 30, 8, 0, tzinfo=UTC))
ALL_MESSAGES = (*ALERT_FIXTURES, "linkedin_no_jobs")


def count(engine: Engine, sql: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(sql)).scalar() or 0)


async def owner_with_inbox(factory: async_sessionmaker[AsyncSession]) -> tuple[UserScope, UUID]:
    owner = await accounts.bootstrap_owner("owner@example.org", factory=factory)
    scope = owner.scope()
    gmail = privacy.consent_text("gmail_alerts")
    await privacy.grant_consent(
        scope, gmail, technical_scope=["gmail.readonly"], clock=CLOCK, factory=factory
    )
    inbox_id = await connectors.create_alert_inbox(scope, kind="gmail", factory=factory)
    return scope, inbox_id


async def test_owner_can_be_created_once(session_factory: async_sessionmaker[AsyncSession]) -> None:
    owner = await accounts.bootstrap_owner("owner@example.org", factory=session_factory)

    assert await accounts.find_owner(factory=session_factory) == owner
    with pytest.raises(ConflictError):
        await accounts.bootstrap_owner("second@example.org", factory=session_factory)


async def test_inbox_needs_consent(session_factory: async_sessionmaker[AsyncSession]) -> None:
    owner = await accounts.bootstrap_owner("owner@example.org", factory=session_factory)

    with pytest.raises(ConsentRequiredError):
        await connectors.create_alert_inbox(owner.scope(), kind="gmail", factory=session_factory)


async def test_alert_emails_become_jobs_and_bodies_are_not_stored(
    session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    scope, inbox_id = await owner_with_inbox(session_factory)

    result = await connectors.ingest_alert_messages(
        scope, inbox_id, stream(ALL_MESSAGES), clock=CLOCK, factory=session_factory
    )

    assert result.connector == "alerts:gmail"
    assert result.jobs_found == 11
    assert result.jobs_new == 11
    assert result.status == "degraded"  # the paused-alert email matched LinkedIn but had no jobs
    assert result.error == "no jobs found in: linkedin (1)"
    assert count(admin_engine, "SELECT count(*) FROM alert_messages") == 8
    assert count(admin_engine, "SELECT count(*) FROM alert_messages WHERE status = 'unparsed'") == 1
    assert count(admin_engine, "SELECT count(*) FROM jobs WHERE country = 'AE'") == 6
    assert count(admin_engine, "SELECT count(*) FROM jobs WHERE country = 'IN'") == 5
    assert count(admin_engine, "SELECT count(*) FROM source_runs WHERE user_id IS NOT NULL") == 1
    leaked = text(
        "SELECT count(*) FROM jobs j JOIN job_sources s ON s.job_id = j.id WHERE "
        "j.description LIKE '%' || :phrase || '%' OR s.raw::text LIKE '%' || :phrase || '%' "
        "OR j.url LIKE '%' || :phrase || '%'"
    )
    with admin_engine.connect() as connection:
        for phrase in ("Actively recruiting", "We paused your alert", "Unsubscribe", "trackingId"):
            assert connection.execute(leaked, {"phrase": phrase}).scalar() == 0


async def test_rerun_skips_messages_already_processed(
    session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    scope, inbox_id = await owner_with_inbox(session_factory)
    await connectors.ingest_alert_messages(
        scope, inbox_id, stream(ALERT_FIXTURES), clock=CLOCK, factory=session_factory
    )

    again = await connectors.ingest_alert_messages(
        scope, inbox_id, stream(ALERT_FIXTURES), clock=CLOCK, factory=session_factory
    )

    assert again.jobs_found == 0
    assert again.status == "ok"
    assert count(admin_engine, "SELECT count(*) FROM alert_messages") == 7
    assert count(admin_engine, "SELECT count(*) FROM jobs") == 11


async def test_revoked_consent_stops_ingestion(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope, inbox_id = await owner_with_inbox(session_factory)
    assert await privacy.revoke_consent(scope, "gmail_alerts", clock=CLOCK, factory=session_factory)

    with pytest.raises(ConsentRequiredError):
        await connectors.ingest_alert_messages(
            scope, inbox_id, stream(ALERT_FIXTURES), clock=CLOCK, factory=session_factory
        )


async def test_another_user_cannot_use_the_inbox(
    session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    _, inbox_id = await owner_with_inbox(session_factory)
    stranger_id = new_id()
    with admin_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, email) VALUES (:id, 'stranger@example.org')"),
            {"id": stranger_id},
        )
    stranger = UserScope(user_id=stranger_id, roles=frozenset({Role.USER}), via=ClientKind.WEB)

    with pytest.raises(NotFoundError):
        await connectors.ingest_alert_messages(
            stranger, inbox_id, stream(ALERT_FIXTURES), clock=CLOCK, factory=session_factory
        )


async def test_consent_text_versions_supersede_each_other(
    session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    owner = await accounts.bootstrap_owner("owner@example.org", factory=session_factory)
    scope = owner.scope()
    v1 = privacy.consent_text("gmail_alerts")
    v2 = privacy.ConsentText(source="gmail_alerts", version="v2", text="updated")

    first = await privacy.grant_consent(
        scope, v1, technical_scope=[], clock=CLOCK, factory=session_factory
    )
    same = await privacy.grant_consent(
        scope, v1, technical_scope=[], clock=CLOCK, factory=session_factory
    )
    second = await privacy.grant_consent(
        scope, v2, technical_scope=[], clock=CLOCK, factory=session_factory
    )

    assert first == same
    assert second != first
    assert count(admin_engine, "SELECT count(*) FROM consents WHERE revoked_at IS NULL") == 1
