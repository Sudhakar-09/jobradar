"""Cross-cutting tables: feature flags, audit log, dead letters."""

from typing import Any, Final
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from jobradar.core.base import Base
from jobradar.models._types import CreatedAt, OptionalTimestamp, UpdatedAt, UuidPk, check_in

FLAG_SCOPES: Final = ("global", "user")
DEAD_LETTER_STATUSES: Final = ("open", "replayed", "discarded")


class SettingsFlag(Base):
    """A runtime flag, global or for one user (canonical keys: docs/lld/README.md)."""

    __tablename__ = "settings_flags"
    __table_args__ = (
        CheckConstraint(check_in("scope", FLAG_SCOPES), name="scope"),
        CheckConstraint(
            "(scope = 'global' AND user_id IS NULL) OR (scope = 'user' AND user_id IS NOT NULL)",
            name="scope_user",
        ),
        Index(
            "uq_settings_flags_key_global",
            "key",
            unique=True,
            postgresql_where=text("scope = 'global'"),
        ),
        Index(
            "uq_settings_flags_key_user_id",
            "key",
            "user_id",
            unique=True,
            postgresql_where=text("scope = 'user'"),
        ),
    )

    id: Mapped[UuidPk]
    key: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[UpdatedAt]


class AuditLog(Base):
    """Append-only record of sensitive actions; no personal data beyond IDs."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_subject_user_id_created_at", "subject_user_id", "created_at"),
        Index("ix_audit_log_action_created_at", "action", "created_at"),
    )

    id: Mapped[UuidPk]
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    subject_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_at: Mapped[CreatedAt]


class DeadLetter(Base):
    """A task whose retries ran out; replayable from the admin console."""

    __tablename__ = "dead_letters"
    __table_args__ = (
        CheckConstraint(check_in("status", DEAD_LETTER_STATUSES), name="status"),
        Index("ix_dead_letters_status_created_at", "status", "created_at"),
    )

    id: Mapped[UuidPk]
    task_name: Mapped[str] = mapped_column(Text, nullable=False)
    task_args: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    error_type: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    created_at: Mapped[CreatedAt]
    resolved_at: Mapped[OptionalTimestamp]
    resolved_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
