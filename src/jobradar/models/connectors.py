"""Discovery tables (connectors domain): companies, source runs, alert inboxes and messages."""

from typing import Any, Final
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from jobradar.core.base import Base
from jobradar.models._types import (
    CreatedAt,
    OptionalTimestamp,
    Timestamp,
    UpdatedAt,
    UserFk,
    UuidPk,
    check_in,
)

COMPANY_ATS: Final = (
    "greenhouse",
    "lever",
    "ashby",
    "workable",
    "smartrecruiters",
    "workday",
    "other",
)
COMPANY_STATUSES: Final = ("active", "not_found", "disabled")
SUGGESTION_STATUSES: Final = ("pending", "accepted", "rejected")
RUN_STATUSES: Final = ("running", "ok", "partial", "failed", "degraded")
INBOX_KINDS: Final = ("gmail", "forwarding")
INBOX_STATUSES: Final = (
    "active",
    "reauth_required",
    "revoked",
)  # + pending_confirmation in Phase 11
MESSAGE_STATUSES: Final = ("parsed", "unparsed", "ignored")


class Company(Base):
    """A hiring company in the shared catalogue (no personal data)."""

    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(f"ats IS NULL OR {check_in('ats', COMPANY_ATS)}", name="ats"),
        CheckConstraint(check_in("status", COMPANY_STATUSES), name="status"),
        CheckConstraint(
            "quality_score IS NULL OR quality_score BETWEEN 0 AND 100", name="quality_score"
        ),
        Index(
            "uq_companies_normalized_name_domain",
            "normalized_name",
            "domain",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "uq_companies_ats_ats_slug",
            "ats",
            "ats_slug",
            unique=True,
            postgresql_where=text("ats_slug IS NOT NULL"),
        ),
        Index("ix_companies_countries", "countries", postgresql_using="gin"),
    )

    id: Mapped[UuidPk]
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(Text)
    ats: Mapped[str | None] = mapped_column(Text)
    ats_slug: Mapped[str | None] = mapped_column(Text)
    countries: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    sponsor_flags: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    quality_score: Mapped[int | None] = mapped_column(SmallInteger)
    verified_at: Mapped[OptionalTimestamp]
    consecutive_not_found: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class CompanySuggestion(Base):
    """An employer seen in a user's alerts, waiting for the user to accept or reject it."""

    __tablename__ = "company_suggestions"
    __table_args__ = (
        CheckConstraint(check_in("status", SUGGESTION_STATUSES), name="status"),
        Index("ix_company_suggestions_user_id_status", "user_id", "status"),
    )

    id: Mapped[UuidPk]
    user_id: Mapped[UserFk]
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    apply_host: Mapped[str] = mapped_column(Text, nullable=False)
    detected_ats: Mapped[str | None] = mapped_column(Text)
    detected_slug: Mapped[str | None] = mapped_column(Text)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    created_at: Mapped[CreatedAt]
    decided_at: Mapped[OptionalTimestamp]


class SourceRun(Base):
    """One connector run; ``user_id`` is set only for per-user alert ingestion."""

    __tablename__ = "source_runs"
    __table_args__ = (
        CheckConstraint(check_in("status", RUN_STATUSES), name="status"),
        Index("ix_source_runs_connector_started_at", "connector", "started_at"),
        Index(
            "ix_source_runs_company_id_started_at",
            "company_id",
            "started_at",
            postgresql_where=text("company_id IS NOT NULL"),
        ),
    )

    id: Mapped[UuidPk]
    connector: Mapped[str] = mapped_column(Text, nullable=False)
    company_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL")
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    started_at: Mapped[Timestamp]
    finished_at: Mapped[OptionalTimestamp]
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="running")
    jobs_found: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    jobs_new: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    jobs_updated: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    items_invalid: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    http_status_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    error_summary: Mapped[str | None] = mapped_column(Text)


class AlertInbox(Base):
    """A user's connected job-alert mailbox (Gmail read-only in Phase 2)."""

    __tablename__ = "alert_inboxes"
    __table_args__ = (
        CheckConstraint(check_in("kind", INBOX_KINDS), name="kind"),
        CheckConstraint(check_in("status", INBOX_STATUSES), name="status"),
        Index("ix_alert_inboxes_user_id", "user_id"),
    )

    id: Mapped[UuidPk]
    user_id: Mapped[UserFk]
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    oauth_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    sender_allowlist: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    last_synced_at: Mapped[OptionalTimestamp]
    consent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("consents.id", ondelete="RESTRICT"), nullable=False
    )


class AlertMessage(Base):
    """Bookkeeping for one processed alert email. The email body is never stored."""

    __tablename__ = "alert_messages"
    __table_args__ = (
        CheckConstraint(check_in("status", MESSAGE_STATUSES), name="status"),
        Index(
            "uq_alert_messages_inbox_id_provider_message_id",
            "inbox_id",
            "provider_message_id",
            unique=True,
        ),
        Index("ix_alert_messages_user_id_received_at", "user_id", "received_at"),
    )

    id: Mapped[UuidPk]
    user_id: Mapped[UserFk]
    inbox_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alert_inboxes.id", ondelete="CASCADE"), nullable=False
    )
    provider_message_id: Mapped[str] = mapped_column(Text, nullable=False)
    sender: Mapped[str] = mapped_column(Text, nullable=False)
    parser: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    jobs_parsed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    received_at: Mapped[Timestamp]
    processed_at: Mapped[Timestamp]
