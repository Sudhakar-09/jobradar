"""Alert-email ingestion (US-2.5): messages → parsers → shared job corpus, per user.

Bodies stay in memory only. Each message is recorded by ID so a re-run never processes it twice,
and a board whose emails stop yielding jobs marks the run degraded (format changed).
"""

# Postponed annotations: connectors and normalizer depend on each other (RawJob / ingest).
from __future__ import annotations

from collections import Counter
from collections.abc import AsyncIterable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import normalizer, privacy
from jobradar.connectors.alerts import (
    LinkCardParser,
    build_parsers,
    load_alert_senders,
    pick_parser,
)
from jobradar.connectors.gmail import (
    GmailAlertInbox,
    GmailAuthError,
    GmailSettings,
    load_inboxes_file,
    load_oauth_client,
)
from jobradar.connectors.health import evaluate_health
from jobradar.connectors.repository import (
    AlertInboxRepository,
    AlertMessageRepository,
    SourceRunRepository,
)
from jobradar.connectors.schemas import InboundMessage, RawJob, SourceRunResult
from jobradar.connectors.service.catalogue import record_suggestions
from jobradar.core.clock import Clock, SystemClock
from jobradar.core.crypto import SecretBox
from jobradar.core.db import user_session
from jobradar.core.errors import ExternalServiceError, NotFoundError, ValidationFailedError
from jobradar.core.http import PoliteClient
from jobradar.core.scope import UserScope, system_scope
from jobradar.core.settings import get_settings
from jobradar.core.source_policies import SourcePolicyRegistry

CONSENT_SOURCE: Final = {"gmail": "gmail_alerts", "forwarding": "forwarding_inbox"}
logger = structlog.get_logger(__name__)
Factory = async_sessionmaker[AsyncSession] | None
ClientFactory = Callable[[SourcePolicyRegistry], PoliteClient]


@lru_cache(maxsize=1)
def configured_parsers() -> tuple[LinkCardParser, ...]:
    """Parsers for every board in `config/alert_senders.yaml`."""
    return tuple(
        build_parsers(load_alert_senders(get_settings().config_dir / "alert_senders.yaml"))
    )


def alert_sender_addresses() -> list[str]:
    """Every configured alert sender address (the Gmail query allowlist)."""
    return sorted(
        {address for parser in configured_parsers() for address in parser.config.sender_addresses}
    )


async def create_alert_inbox(
    scope: UserScope,
    *,
    kind: Literal["gmail", "forwarding"],
    oauth_token_enc: bytes | None = None,
    factory: Factory = None,
) -> UUID:
    """Connect an alert inbox for the user; requires their active consent for that kind.

    Raises:
        ConsentRequiredError: no active consent for the inbox kind.
    """
    consent_source = CONSENT_SOURCE[kind]
    await privacy.require_consent(scope, consent_source, factory=factory)
    consent_id = await privacy.active_consent_id(scope, consent_source, factory=factory)
    async with user_session(scope, factory=factory) as session:
        return await AlertInboxRepository(session).create(
            user_id=scope.user_id,
            kind=kind,
            sender_allowlist=alert_sender_addresses(),
            consent_id=consent_id,
            oauth_token_enc=oauth_token_enc,
        )


@dataclass(slots=True)
class _Tally:
    jobs: list[RawJob] = field(default_factory=list)
    invalid: int = 0
    messages: int = 0
    unparsed: Counter[str] = field(default_factory=Counter)
    fetch_error: ExternalServiceError | None = None


async def ingest_alert_messages(
    scope: UserScope,
    inbox_id: UUID,
    messages: AsyncIterable[InboundMessage],
    *,
    parsers: tuple[LinkCardParser, ...] | None = None,
    clock: Clock | None = None,
    factory: Factory = None,
) -> SourceRunResult:
    """Parse new alert emails from one of the user's inboxes and store the jobs they contain.

    Employers the catalogue does not know become company suggestions for the user to review.

    Raises:
        NotFoundError: the inbox does not exist or belongs to another user.
        ConsentRequiredError: the user has not consented to this inbox kind.
    """
    clock = clock or SystemClock()
    parsers = parsers if parsers is not None else configured_parsers()
    async with user_session(scope, factory=factory) as session:
        inbox = await AlertInboxRepository(session).get(inbox_id)
        if inbox is None:
            raise NotFoundError("alert inbox not found")
        connector = f"alerts:{inbox.kind}"
        consent_source = CONSENT_SOURCE[inbox.kind]
    await privacy.require_consent(scope, consent_source, factory=factory)
    async with user_session(scope, factory=factory) as session:
        run_id = await SourceRunRepository(session).start(
            connector, None, clock.now(), user_id=scope.user_id
        )

    tally = _Tally()
    try:
        async for message in messages:
            await _process(
                scope, inbox_id, message, parsers=parsers, tally=tally, clock=clock, factory=factory
            )
    except ExternalServiceError as exc:  # the mailbox failed mid-run: keep what was parsed
        tally.fetch_error = exc

    counts = await normalizer.ingest(
        system_scope(connector), tally.jobs, source_run_id=run_id, clock=clock, factory=factory
    )
    await record_suggestions(scope, tally.jobs, factory=factory)
    return await _finish(
        scope,
        inbox_id,
        connector=connector,
        run_id=run_id,
        tally=tally,
        counts=counts,
        clock=clock,
        factory=factory,
    )


async def _process(  # noqa: PLR0913 -- one message plus the run's shared state
    scope: UserScope,
    inbox_id: UUID,
    message: InboundMessage,
    *,
    parsers: tuple[LinkCardParser, ...],
    tally: _Tally,
    clock: Clock,
    factory: Factory,
) -> None:
    async with user_session(scope, factory=factory) as session:
        bookkeeping = AlertMessageRepository(session)
        if await bookkeeping.seen(inbox_id, message.provider_message_id):
            return
        parser = pick_parser(list(parsers), message)
        status: Literal["parsed", "unparsed", "ignored"] = "ignored"
        jobs: list[RawJob] = []
        if parser is not None:
            jobs, invalid = parser.parse(message)
            tally.invalid += invalid
            status = "parsed" if jobs else "unparsed"
            if not jobs:
                tally.unparsed[parser.code] += 1
        tally.jobs.extend(jobs)
        tally.messages += 1
        await bookkeeping.record(
            user_id=scope.user_id,
            inbox_id=inbox_id,
            provider_message_id=message.provider_message_id,
            sender=message.sender,
            parser=parser.code if parser else None,
            status=status,
            jobs_parsed=len(jobs),
            received_at=message.received_at,
            processed_at=clock.now(),
        )


async def _finish(  # noqa: PLR0913 -- assembles one run's outcome from its parts
    scope: UserScope,
    inbox_id: UUID,
    *,
    connector: str,
    run_id: UUID,
    tally: _Tally,
    counts: normalizer.IngestResult,
    clock: Clock,
    factory: Factory,
) -> SourceRunResult:
    now = clock.now()
    found = len(tally.jobs)
    error = None
    status: Literal["ok", "partial", "failed", "degraded"] = evaluate_health(
        found, tally.invalid, None
    )
    if tally.unparsed:
        status = "degraded"  # a board's emails no longer yield jobs: its format changed
        error = "no jobs found in: " + ", ".join(
            f"{code} ({count})" for code, count in sorted(tally.unparsed.items())
        )
    if tally.fetch_error is not None:
        status = "failed"
        error = f"mailbox error: {tally.fetch_error}"
    async with user_session(scope, factory=factory) as session:
        if isinstance(tally.fetch_error, GmailAuthError):
            await AlertInboxRepository(session).set_status(inbox_id, "reauth_required")
            logger.warning("connectors.gmail_reauth_required", inbox_id=str(inbox_id))
        await SourceRunRepository(session).finish(
            run_id,
            status=status,
            found=found,
            new=counts.new,
            updated=counts.updated,
            invalid=tally.invalid,
            http_status_counts={},
            error=error,
            now=now,
        )
        inbox = await AlertInboxRepository(session).get(inbox_id)
        if inbox is not None:
            inbox.last_synced_at = now
    logger.info(
        "connectors.alerts_ingested",
        connector=connector,
        messages=tally.messages,
        found=found,
        new=counts.new,
        unparsed=sum(tally.unparsed.values()),
        status=status,
    )
    return SourceRunResult(
        run_id=run_id,
        connector=connector,
        company_id=None,
        company_name=None,
        status=status,
        jobs_found=found,
        jobs_new=counts.new,
        jobs_updated=counts.updated,
        items_invalid=tally.invalid,
        http_status_counts={},
        error=error,
    )


@lru_cache(maxsize=1)
def gmail_settings() -> GmailSettings:
    """Gmail endpoints from `config/inboxes.yaml`."""
    return load_inboxes_file(get_settings().config_dir / "inboxes.yaml").gmail


def _secret_box() -> SecretBox:
    key = get_settings().token_encryption_key
    return SecretBox(key.get_secret_value() if key else None)


def _oauth_client_path() -> Path:
    path = get_settings().google_oauth_client_file
    if path is None or not path.is_file():
        raise ValidationFailedError("GOOGLE_OAUTH_CLIENT_FILE is not set or the file is missing")
    return path


def _default_client(policies: SourcePolicyRegistry) -> PoliteClient:
    return PoliteClient(policies, get_settings())


async def connect_gmail_inbox(
    scope: UserScope, *, refresh_token: str, factory: Factory = None
) -> UUID:
    """Store an encrypted Gmail grant as the user's alert inbox (consent must already exist)."""
    sealed = _secret_box().encrypt(refresh_token.encode("utf-8"))
    return await create_alert_inbox(scope, kind="gmail", oauth_token_enc=sealed, factory=factory)


async def ingest_alerts(
    scope: UserScope,
    *,
    clock: Clock | None = None,
    client_factory: ClientFactory = _default_client,
    factory: Factory = None,
) -> list[SourceRunResult]:
    """Ingest new alert emails from every active Gmail inbox of the user.

    An inbox whose grant Google rejects is marked ``reauth_required`` and its run is recorded
    as failed; other inboxes still run.
    """
    async with user_session(scope, factory=factory) as session:
        inboxes = [
            (inbox.id, inbox.oauth_token_enc)
            for inbox in await AlertInboxRepository(session).active()
            if inbox.kind == "gmail"
        ]
    if not inboxes:
        return []
    from jobradar.connectors.config import policy_registry  # noqa: PLC0415 -- avoid an import cycle

    client = load_oauth_client(_oauth_client_path())
    box = _secret_box()
    results: list[SourceRunResult] = []
    async with client_factory(policy_registry()) as http:
        for inbox_id, sealed in inboxes:
            if sealed is None:
                continue
            gmail = GmailAlertInbox(
                http,
                gmail_settings(),
                client,
                box.decrypt(sealed).decode("utf-8"),
                alert_sender_addresses(),
            )
            results.append(
                await ingest_alert_messages(
                    scope, inbox_id, gmail.fetch_new(), clock=clock, factory=factory
                )
            )
    return results


async def disconnect_inbox(
    scope: UserScope,
    inbox_id: UUID,
    *,
    client_factory: ClientFactory = _default_client,
    factory: Factory = None,
) -> None:
    """Disconnect an inbox now: revoke at Google (best effort), delete the token, end consent."""
    async with user_session(scope, factory=factory) as session:
        inbox = await AlertInboxRepository(session).get(inbox_id)
        if inbox is None:
            raise NotFoundError("alert inbox not found")
        kind, sealed = inbox.kind, inbox.oauth_token_enc
    if kind == "gmail" and sealed is not None:
        from jobradar.connectors.config import policy_registry  # noqa: PLC0415 -- import cycle

        try:
            client = load_oauth_client(_oauth_client_path())
            token = _secret_box().decrypt(sealed).decode("utf-8")
            async with client_factory(policy_registry()) as http:
                await GmailAlertInbox(http, gmail_settings(), client, token, []).revoke()
        except (ExternalServiceError, ValidationFailedError):
            logger.warning("connectors.gmail_revoke_failed", inbox_id=str(inbox_id))
    async with user_session(scope, factory=factory) as session:
        await AlertInboxRepository(session).set_status(inbox_id, "revoked", clear_token=True)
    await privacy.revoke_consent(scope, CONSENT_SOURCE[kind], factory=factory)


@dataclass(frozen=True, slots=True)
class InboxInfo:
    """An alert inbox as shown to its owner (no token)."""

    id: UUID
    kind: str
    status: str
    last_synced_at: datetime | None


async def list_inboxes(scope: UserScope, *, factory: Factory = None) -> list[InboxInfo]:
    """The user's alert inboxes, including disconnected ones."""
    async with user_session(scope, factory=factory) as session:
        rows = await AlertInboxRepository(session).all()
    return [InboxInfo(row.id, row.kind, row.status, row.last_synced_at) for row in rows]
