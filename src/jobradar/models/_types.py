"""Reusable column types for models (docs/lld/database.md §1)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import mapped_column

from jobradar.core.ids import new_id

UuidPk = Annotated[UUID, mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)]
CreatedAt = Annotated[
    datetime, mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
]
UpdatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    ),
]
Timestamp = Annotated[datetime, mapped_column(DateTime(timezone=True), nullable=False)]
OptionalTimestamp = Annotated[datetime | None, mapped_column(DateTime(timezone=True))]
UserFk = Annotated[
    UUID,
    mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
]


def check_in(column: str, values: tuple[str, ...]) -> str:
    """SQL for a CHECK constraint limiting ``column`` to ``values`` (no Postgres ENUMs)."""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"
