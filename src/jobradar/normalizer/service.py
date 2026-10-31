"""Ingest raw jobs into the shared corpus with deduplication (US-2.3)."""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar.connectors import RawJob
from jobradar.core.clock import Clock, SystemClock
from jobradar.core.db import system_session
from jobradar.core.scope import SystemScope
from jobradar.core.settings import get_settings
from jobradar.normalizer.repository import JobRecord, JobRepository
from jobradar.normalizer.rules import (
    LocationAliases,
    content_hash,
    dedupe_hash,
    detect_location,
    load_location_aliases,
)


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Counts for one ingest batch."""

    new: int
    updated: int
    seen: int


@lru_cache(maxsize=1)
def location_aliases() -> LocationAliases:
    """The process-wide location alias table (`config/locations.yaml`)."""
    return load_location_aliases(get_settings().config_dir / "locations.yaml")


def job_country(raw: RawJob) -> str | None:
    """ISO country code of a raw job from its location text and source hints, or None."""
    aliases = location_aliases()
    return detect_location(
        raw.location_raw, aliases, country_hint=raw.country_code, city_hint=raw.city
    ).country


def to_record(raw: RawJob, aliases: LocationAliases) -> JobRecord:
    """Turn a raw job into what the corpus stores, computing location and hashes."""
    location = detect_location(
        raw.location_raw, aliases, country_hint=raw.country_code, city_hint=raw.city
    )
    apply_url = str(raw.apply_url) if raw.apply_url else None
    return JobRecord(
        source=raw.source,
        source_job_id=raw.source_job_id,
        company_id=raw.company_id,
        company_name=raw.company_name,
        title=raw.title,
        description=raw.description or "",
        url=str(raw.url),
        apply_url=apply_url,
        location_raw=raw.location_raw,
        country=location.country,
        city=location.city,
        posted_at=raw.posted_at,
        content_hash=content_hash(
            title=raw.title,
            description=raw.description,
            location_raw=raw.location_raw,
            apply_url=apply_url,
        ),
        dedupe_hash=dedupe_hash(raw.company_name, raw.title, location),
        raw=dict(raw.raw),
    )


async def ingest(
    scope: SystemScope,
    jobs: Sequence[RawJob],
    *,
    source_run_id: UUID | None,
    clock: Clock | None = None,
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> IngestResult:
    """Store a batch of raw jobs in one transaction, deduplicating across sources.

    Re-ingesting the same jobs is idempotent apart from ``last_seen_at``.
    """
    now = (clock or SystemClock()).now()
    aliases = location_aliases()
    counts = {"new": 0, "updated": 0, "seen": 0}
    async with system_session(scope, factory=factory) as session:
        repository = JobRepository(session)
        for raw in jobs:
            outcome = await repository.upsert(
                to_record(raw, aliases), source_run_id=source_run_id, now=now
            )
            counts[outcome] += 1
            await session.flush()
    return IngestResult(**counts)
