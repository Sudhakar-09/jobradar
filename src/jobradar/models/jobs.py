"""Shared job corpus (normalizer domain).

Phase 2 creates the discovery columns only; normalized fields (seniority, salary, visa,
scores, …) are added by the Phase 3 migration (docs/lld/database.md §9).
"""

from datetime import datetime
from typing import Any, Final
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from jobradar.core.base import Base
from jobradar.models._types import CreatedAt, Timestamp, UpdatedAt, UuidPk, check_in

JOB_STATUSES: Final = ("active", "expired", "removed")


class Job(Base):
    """One deduplicated job posting (untrusted third-party text)."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(check_in("status", JOB_STATUSES), name="status"),
        Index("uq_jobs_dedupe_hash", "dedupe_hash", unique=True),
        Index("ix_jobs_country_status_last_seen_at", "country", "status", "last_seen_at"),
        Index("ix_jobs_first_seen_at", "first_seen_at"),
        Index("ix_jobs_apply_host", "apply_host"),
    )

    id: Mapped[UuidPk]
    company_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL")
    )
    company_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    apply_url: Mapped[str | None] = mapped_column(Text)
    apply_host: Mapped[str | None] = mapped_column(Text)
    location_raw: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    dedupe_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    first_seen_at: Mapped[Timestamp]
    last_seen_at: Mapped[Timestamp]
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class JobSource(Base):
    """Where and when a job was seen; one row per (source, source job id)."""

    __tablename__ = "job_sources"
    __table_args__ = (
        Index("uq_job_sources_source_source_job_id", "source", "source_job_id", unique=True),
        Index("ix_job_sources_job_id", "job_id"),
    )

    id: Mapped[UuidPk]
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_job_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_runs.id", ondelete="SET NULL")
    )
    raw: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    first_seen_at: Mapped[Timestamp]
    last_seen_at: Mapped[Timestamp]
