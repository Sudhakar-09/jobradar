"""Account tables (accounts domain; Phase 2 creates the minimal ``users`` table)."""

from typing import Any, Final

from sqlalchemy import CheckConstraint, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from jobradar.core.base import Base
from jobradar.models._types import CreatedAt, OptionalTimestamp, UpdatedAt, UuidPk, check_in

USER_ROLES: Final = ("user", "admin", "owner")
USER_STATUSES: Final = ("active", "suspended", "pending_deletion")


class User(Base):
    """A JobRadar account. Columns for sign-in arrive in Phase 4 (database.md §9)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(check_in("role", USER_ROLES), name="role"),
        CheckConstraint(check_in("status", USER_STATUSES), name="status"),
    )

    id: Mapped[UuidPk]
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="user")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="Asia/Kolkata")
    comparison_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="INR"
    )
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]
    last_login_at: Mapped[OptionalTimestamp]

    def __repr__(self) -> str:
        """Represent without personal data."""
        return f"User(id={self.id})"
