"""Job corpus persistence (shared tables; corpus role)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobradar.models import Job, JobSource

UpsertOutcome = Literal["new", "updated", "seen"]


@dataclass(frozen=True, slots=True)
class JobRecord:
    """Everything the repository stores for one sighting of a job."""

    source: str
    source_job_id: str
    company_id: UUID | None
    company_name: str
    title: str
    description: str
    url: str
    apply_url: str | None
    location_raw: str | None
    country: str | None
    city: str | None
    posted_at: datetime | None
    content_hash: bytes
    dedupe_hash: bytes
    raw: dict[str, Any]


class JobRepository:
    """Upserts jobs and their source sightings; one call per job inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open session (the caller owns the transaction)."""
        self._session = session

    async def upsert(
        self, record: JobRecord, *, source_run_id: UUID | None, now: datetime
    ) -> UpsertOutcome:
        """Store a sighting: ``new`` job, ``updated`` content, or ``seen`` again / elsewhere."""
        sighting = await self._session.scalar(
            select(JobSource).where(
                JobSource.source == record.source,
                JobSource.source_job_id == record.source_job_id,
            )
        )
        if sighting is not None:
            sighting.last_seen_at = now
            sighting.raw = record.raw
            sighting.source_run_id = source_run_id
            return await self._refresh(sighting.job_id, record, now)

        existing_id = await self._session.scalar(
            select(Job.id).where(Job.dedupe_hash == record.dedupe_hash)
        )
        if existing_id is not None:
            self._add_sighting(existing_id, record, source_run_id, now)
            await self._touch(existing_id, now)
            return "seen"

        job = self._new_job(record, now)
        self._session.add(job)
        await self._session.flush()
        self._add_sighting(job.id, record, source_run_id, now)
        return "new"

    async def _refresh(self, job_id: UUID, record: JobRecord, now: datetime) -> UpsertOutcome:
        job = await self._session.get(Job, job_id)
        if job is None:  # pragma: no cover - FK guarantees the job exists
            raise LookupError(job_id)
        job.last_seen_at = now
        if job.content_hash == record.content_hash:
            return "seen"
        job.title = record.title
        job.description = record.description
        job.apply_url = record.apply_url
        job.apply_host = _host(record.apply_url or record.url)
        job.location_raw = record.location_raw
        job.content_hash = record.content_hash
        return "updated"

    async def _touch(self, job_id: UUID, now: datetime) -> None:
        await self._session.execute(update(Job).where(Job.id == job_id).values(last_seen_at=now))

    def _add_sighting(
        self, job_id: UUID, record: JobRecord, source_run_id: UUID | None, now: datetime
    ) -> None:
        self._session.add(
            JobSource(
                job_id=job_id,
                source=record.source,
                source_job_id=record.source_job_id,
                source_run_id=source_run_id,
                raw=record.raw,
                first_seen_at=now,
                last_seen_at=now,
            )
        )

    @staticmethod
    def _new_job(record: JobRecord, now: datetime) -> Job:
        return Job(
            company_id=record.company_id,
            company_name_raw=record.company_name,
            title=record.title,
            description=record.description,
            url=record.url,
            apply_url=record.apply_url,
            apply_host=_host(record.apply_url or record.url),
            location_raw=record.location_raw,
            country=record.country,
            city=record.city,
            posted_at=record.posted_at,
            content_hash=record.content_hash,
            dedupe_hash=record.dedupe_hash,
            first_seen_at=now,
            last_seen_at=now,
        )


def _host(url: str) -> str | None:
    host = urlsplit(url).hostname
    return host.lower() if host else None
