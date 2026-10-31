"""Consent records (privacy domain, ADR-0018)."""

from sqlalchemy import Index, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from jobradar.core.base import Base
from jobradar.models._types import OptionalTimestamp, Timestamp, UserFk, UuidPk


class Consent(Base):
    """One grant of consent for one data source; revoking sets ``revoked_at``."""

    __tablename__ = "consents"
    __table_args__ = (
        Index("ix_consents_user_id_source", "user_id", "source"),
        Index(
            "uq_consents_user_id_source_active",
            "user_id",
            "source",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UuidPk]
    user_id: Mapped[UserFk]
    source: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    text_version: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[Timestamp]
    revoked_at: Mapped[OptionalTimestamp]
