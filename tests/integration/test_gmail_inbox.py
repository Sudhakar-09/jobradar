"""Gmail inbox end to end against the test database, with a fake Google API."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import accounts, connectors, privacy
from jobradar.core.clock import FrozenClock
from jobradar.core.crypto import generate_key
from jobradar.core.http import PoliteClient
from jobradar.core.scope import UserScope
from jobradar.core.settings import get_settings
from jobradar.core.source_policies import SourcePolicyRegistry
from tests.support.alerts import ALERT_FIXTURES
from tests.support.fake_gmail import FakeGoogle
from tests.support.fake_http import polite_client

pytestmark = [pytest.mark.integration, pytest.mark.anyio]
CLOCK = FrozenClock(datetime(2026, 10, 30, 8, 0, tzinfo=UTC))


@pytest.fixture
def gmail_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    client = tmp_path / "google_oauth_client.json"
    client.write_text(json.dumps({"installed": {"client_id": "c", "client_secret": "s"}}))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_FILE", str(client))
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", generate_key())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def scalar(engine: Engine, sql: str) -> object:
    with engine.connect() as connection:
        return connection.execute(text(sql)).scalar()


async def connected_owner(factory: async_sessionmaker[AsyncSession]) -> UserScope:
    owner = await accounts.bootstrap_owner("owner@example.org", factory=factory)
    scope = owner.scope()
    await privacy.grant_consent(
        scope,
        privacy.consent_text("gmail_alerts"),
        technical_scope=["gmail.readonly"],
        clock=CLOCK,
        factory=factory,
    )
    await connectors.connect_gmail_inbox(scope, refresh_token="refresh-xyz", factory=factory)
    return scope


def client_for(fake: FakeGoogle):  # type: ignore[no-untyped-def]
    def make(policies: SourcePolicyRegistry) -> PoliteClient:
        return polite_client(fake, policies)

    return make


async def test_gmail_alerts_are_ingested_and_the_token_is_encrypted(
    gmail_settings: None, session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    scope = await connected_owner(session_factory)
    fake = FakeGoogle(ALERT_FIXTURES)

    results = await connectors.ingest_alerts(
        scope, clock=CLOCK, client_factory=client_for(fake), factory=session_factory
    )

    assert [(r.connector, r.status, r.jobs_new) for r in results] == [("alerts:gmail", "ok", 11)]
    stored = scalar(admin_engine, "SELECT oauth_token_enc FROM alert_inboxes")
    assert isinstance(stored, bytes)
    assert b"refresh-xyz" not in stored
    assert scalar(admin_engine, "SELECT count(*) FROM alert_messages") == 7
    assert (
        scalar(admin_engine, "SELECT count(*) FROM alert_inboxes WHERE last_synced_at IS NOT NULL")
        == 1
    )


async def test_revoked_grant_marks_the_inbox_for_reconnection(
    gmail_settings: None, session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    scope = await connected_owner(session_factory)
    fake = FakeGoogle(ALERT_FIXTURES, token_status=400)

    results = await connectors.ingest_alerts(
        scope, clock=CLOCK, client_factory=client_for(fake), factory=session_factory
    )

    assert results[0].status == "failed"
    assert results[0].error is not None
    assert results[0].error.startswith("mailbox error")
    assert scalar(admin_engine, "SELECT status FROM alert_inboxes") == "reauth_required"
    assert scalar(admin_engine, "SELECT count(*) FROM source_runs WHERE status = 'running'") == 0
    again = await connectors.ingest_alerts(
        scope, clock=CLOCK, client_factory=client_for(fake), factory=session_factory
    )
    assert again == []  # inactive inboxes are not polled until reconnected


async def test_disconnect_revokes_deletes_token_and_ends_consent(
    gmail_settings: None, session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    scope = await connected_owner(session_factory)
    inbox = (await connectors.list_inboxes(scope, factory=session_factory))[0]
    fake = FakeGoogle([])

    await connectors.disconnect_inbox(
        scope, inbox.id, client_factory=client_for(fake), factory=session_factory
    )

    assert fake.revoked == ["refresh-xyz"]
    assert scalar(admin_engine, "SELECT status FROM alert_inboxes") == "revoked"
    assert scalar(admin_engine, "SELECT oauth_token_enc FROM alert_inboxes") is None
    assert not await privacy.has_consent(scope, "gmail_alerts", factory=session_factory)
    assert await connectors.ingest_alerts(scope, factory=session_factory) == []


async def test_reprocess_reads_only_unparsed_emails_again(
    gmail_settings: None, session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    scope = await connected_owner(session_factory)
    # First run: the paused-alert email matches LinkedIn but holds no jobs -> unparsed.
    await connectors.ingest_alerts(
        scope,
        clock=CLOCK,
        client_factory=client_for(FakeGoogle(["linkedin_no_jobs", "bayt"])),
        factory=session_factory,
    )
    assert (
        scalar(admin_engine, "SELECT count(*) FROM alert_messages WHERE status = 'unparsed'") == 1
    )
    # After a "parser fix" the same Gmail ID now serves a readable email.
    fixed = FakeGoogle(["linkedin_card_links"])
    fixed.names = ["linkedin_card_links"]

    def serve_fixed(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/gm-linkedin_no_jobs"):
            request = httpx.Request(
                request.method,
                str(request.url).replace("gm-linkedin_no_jobs", "gm-linkedin_card_links"),
                headers=request.headers,
            )
        return fixed(request)

    def factory(policies: SourcePolicyRegistry) -> PoliteClient:
        return polite_client(serve_fixed, policies)

    results = await connectors.reprocess_unparsed(
        scope, clock=CLOCK, client_factory=factory, factory=session_factory
    )

    assert [(r.status, r.jobs_found) for r in results] == [("ok", 6)]
    fetched = [r.url.path for r in fixed.requests if "/messages/" in r.url.path]
    assert fetched == ["/gmail/v1/users/me/messages/gm-linkedin_card_links"]  # only that one
    assert not any(r.url.path.endswith("/messages") for r in fixed.requests)  # no listing
    assert (
        scalar(admin_engine, "SELECT count(*) FROM alert_messages WHERE status = 'unparsed'") == 0
    )
    assert scalar(admin_engine, "SELECT count(*) FROM alert_messages") == 2
    again = await connectors.reprocess_unparsed(
        scope, clock=CLOCK, client_factory=factory, factory=session_factory
    )
    assert again == []
