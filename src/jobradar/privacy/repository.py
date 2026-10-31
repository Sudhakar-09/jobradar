"""Consent rows (user-owned; RLS)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobradar.models import Consent


class ConsentRepository:
    """Consents of the user bound to the session (RLS filters other users out)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open user session."""
        self._session = session

    async def active(self, source: str) -> Consent | None:
        """The current (not revoked) consent for a source."""
        return await self._session.scalar(
            select(Consent).where(Consent.source == source, Consent.revoked_at.is_(None))
        )

    async def add(
        self,
        *,
        user_id: UUID,
        source: str,
        purpose: str,
        technical_scope: list[str],
        text_version: str,
        granted_at: datetime,
    ) -> UUID:
        """Insert a consent and return its id."""
        consent = Consent(
            user_id=user_id,
            source=source,
            purpose=purpose,
            scope=technical_scope,
            text_version=text_version,
            granted_at=granted_at,
        )
        self._session.add(consent)
        await self._session.flush()
        return consent.id
