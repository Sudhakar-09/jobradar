"""Persistence for the company catalogue and connector runs (shared tables; corpus role)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from jobradar.connectors.health import RunStatus
from jobradar.connectors.schemas import CompanyEntry, CompanyRef
from jobradar.models import AlertInbox, AlertMessage, Company, SourceRun

NOT_FOUND_LIMIT: Final = 3  # consecutive 404s before a company is marked not_found
HEALTH_STATUSES: Final = ("ok", "partial", "degraded")


def _normalized_name(name: str) -> str:
    return " ".join(name.casefold().split())


@dataclass(frozen=True, slots=True)
class SyncCounts:
    """Result of syncing the curated catalogue into the database."""

    created: int
    updated: int


class CompanyRepository:
    """Company catalogue rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open session (the caller owns the transaction)."""
        self._session = session

    async def sync(self, entries: list[CompanyEntry]) -> SyncCounts:
        """Insert or update catalogue entries keyed by (ats, ats_slug)."""
        created = updated = 0
        for entry in entries:
            company = await self._session.scalar(
                select(Company).where(Company.ats == entry.ats, Company.ats_slug == entry.ats_slug)
            )
            if company is None:
                company = Company(ats=entry.ats, ats_slug=entry.ats_slug)
                self._session.add(company)
                created += 1
            else:
                updated += 1
            company.name = entry.name
            company.normalized_name = _normalized_name(entry.name)
            company.domain = entry.domain
            company.countries = list(entry.countries)
        await self._session.flush()
        return SyncCounts(created=created, updated=updated)

    async def for_discovery(
        self, *, ats: str | None = None, company_id: UUID | None = None
    ) -> list[CompanyRef]:
        """Active companies with an ATS board, optionally filtered."""
        query = select(Company).where(
            Company.status == "active", Company.ats.is_not(None), Company.ats_slug.is_not(None)
        )
        if ats is not None:
            query = query.where(Company.ats == ats)
        if company_id is not None:
            query = query.where(Company.id == company_id)
        rows = (await self._session.scalars(query.order_by(Company.name))).all()
        return [
            CompanyRef(id=row.id, name=row.name, ats=row.ats or "", ats_slug=row.ats_slug or "")
            for row in rows
        ]

    async def record_found(self, company_id: UUID, now: datetime) -> None:
        """The board answered: reset the not-found streak."""
        company = await self._session.get(Company, company_id)
        if company is not None:
            company.consecutive_not_found = 0
            company.verified_at = now

    async def record_not_found(self, company_id: UUID) -> str:
        """The board returned 404: extend the streak; after the limit mark it not_found."""
        company = await self._session.get(Company, company_id)
        if company is None:
            return "missing"
        company.consecutive_not_found += 1
        if company.consecutive_not_found >= NOT_FOUND_LIMIT:
            company.status = "not_found"
        return company.status


class SourceRunRepository:
    """Connector run records."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open session (the caller owns the transaction)."""
        self._session = session

    async def start(
        self, connector: str, company_id: UUID | None, now: datetime, *, user_id: UUID | None = None
    ) -> UUID:
        """Record that a run started (``user_id`` only for per-user alert runs); returns its id."""
        run = SourceRun(connector=connector, company_id=company_id, user_id=user_id, started_at=now)
        self._session.add(run)
        await self._session.flush()
        return run.id

    async def finish(  # noqa: PLR0913 -- one field per run outcome column
        self,
        run_id: UUID,
        *,
        status: RunStatus | str,
        found: int,
        new: int,
        updated: int,
        invalid: int,
        http_status_counts: dict[str, int],
        error: str | None,
        now: datetime,
    ) -> None:
        """Record the outcome of a run."""
        run = await self._session.get(SourceRun, run_id)
        if run is None:  # pragma: no cover - started in the same process
            raise LookupError(run_id)
        run.status = status
        run.finished_at = now
        run.jobs_found, run.jobs_new, run.jobs_updated = found, new, updated
        run.items_invalid = invalid
        run.http_status_counts = http_status_counts
        run.error_summary = error

    async def requests_since(self, connector: str, since: datetime) -> int:
        """HTTP requests a connector made since ``since`` (sum of its runs' status counts)."""
        total = await self._session.scalar(
            text(
                "SELECT coalesce(sum(counts.value::int), 0) FROM source_runs, "
                "jsonb_each_text(source_runs.http_status_counts) AS counts "
                "WHERE source_runs.connector = :connector AND source_runs.started_at >= :since"
            ),
            {"connector": connector, "since": since},
        )
        return int(total or 0)

    async def average_found(
        self, connector: str, company_id: UUID | None, since: datetime
    ) -> float | None:
        """Average jobs found by finished healthy runs since ``since`` (None without history)."""
        query = select(func.avg(SourceRun.jobs_found)).where(
            SourceRun.connector == connector,
            SourceRun.started_at >= since,
            SourceRun.status.in_(HEALTH_STATUSES),
        )
        query = query.where(
            SourceRun.company_id == company_id
            if company_id is not None
            else SourceRun.company_id.is_(None)
        )
        average = await self._session.scalar(query)
        return float(average) if average is not None else None


class AlertInboxRepository:
    """The user's connected alert inboxes (RLS-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open user session."""
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        kind: str,
        sender_allowlist: list[str],
        consent_id: UUID,
        oauth_token_enc: bytes | None = None,
    ) -> UUID:
        """Insert an inbox connection and return its id."""
        inbox = AlertInbox(
            user_id=user_id,
            kind=kind,
            sender_allowlist=sender_allowlist,
            consent_id=consent_id,
            oauth_token_enc=oauth_token_enc,
        )
        self._session.add(inbox)
        await self._session.flush()
        return inbox.id

    async def get(self, inbox_id: UUID) -> AlertInbox | None:
        """An inbox of the session's user, or None (another user's inbox is invisible)."""
        return await self._session.get(AlertInbox, inbox_id)

    async def active(self) -> list[AlertInbox]:
        """The user's active inboxes."""
        rows = await self._session.scalars(
            select(AlertInbox).where(AlertInbox.status == "active").order_by(AlertInbox.id)
        )
        return list(rows.all())


class AlertMessageRepository:
    """Bookkeeping for processed alert emails (IDs and counts only, never bodies)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open user session."""
        self._session = session

    async def seen(self, inbox_id: UUID, provider_message_id: str) -> bool:
        """Whether this message was already processed for this inbox."""
        found = await self._session.scalar(
            select(AlertMessage.id).where(
                AlertMessage.inbox_id == inbox_id,
                AlertMessage.provider_message_id == provider_message_id,
            )
        )
        return found is not None

    async def record(  # noqa: PLR0913 -- one argument per bookkeeping column
        self,
        *,
        user_id: UUID,
        inbox_id: UUID,
        provider_message_id: str,
        sender: str,
        parser: str | None,
        status: str,
        jobs_parsed: int,
        received_at: datetime,
        processed_at: datetime,
    ) -> None:
        """Record one processed message."""
        self._session.add(
            AlertMessage(
                user_id=user_id,
                inbox_id=inbox_id,
                provider_message_id=provider_message_id,
                sender=sender,
                parser=parser,
                status=status,
                jobs_parsed=jobs_parsed,
                received_at=received_at,
                processed_at=processed_at,
            )
        )
