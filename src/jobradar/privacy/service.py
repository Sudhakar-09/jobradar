"""Consent records per data source (ADR-0018; minimal Phase 2 slice of docs/lld/privacy.md)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar.core.clock import Clock, SystemClock
from jobradar.core.db import user_session
from jobradar.core.errors import ConsentRequiredError, NotFoundError
from jobradar.core.scope import UserScope
from jobradar.core.settings import get_settings
from jobradar.privacy.repository import ConsentRepository

CONSENT_DIR: Final = "consents"
Factory = async_sessionmaker[AsyncSession] | None


@dataclass(frozen=True, slots=True)
class ConsentText:
    """The exact text a user agrees to, with its version."""

    source: str
    version: str
    text: str


def consent_text(source: str, version: str = "v1") -> ConsentText:
    """Load the consent text shown for a source (`config/consents/<source>.<version>.md`)."""
    path = Path(get_settings().config_dir) / CONSENT_DIR / f"{source}.{version}.md"
    if not path.is_file():
        raise NotFoundError(f"no consent text for {source} {version}")
    return ConsentText(source=source, version=version, text=path.read_text(encoding="utf-8"))


async def grant_consent(
    scope: UserScope,
    text: ConsentText,
    *,
    technical_scope: list[str],
    clock: Clock | None = None,
    factory: Factory = None,
) -> UUID:
    """Record the user's consent for a source; returns the (possibly existing) consent id."""
    now: datetime = (clock or SystemClock()).now()
    async with user_session(scope, factory=factory) as session:
        consents = ConsentRepository(session)
        existing = await consents.active(text.source)
        if existing is not None and existing.text_version == text.version:
            return existing.id
        if existing is not None:
            existing.revoked_at = now  # superseded by the new text version
            await session.flush()
        return await consents.add(
            user_id=scope.user_id,
            source=text.source,
            purpose=f"consent.{text.source}",
            technical_scope=technical_scope,
            text_version=text.version,
            granted_at=now,
        )


async def revoke_consent(
    scope: UserScope, source: str, *, clock: Clock | None = None, factory: Factory = None
) -> bool:
    """Revoke the active consent for a source; returns whether there was one."""
    async with user_session(scope, factory=factory) as session:
        existing = await ConsentRepository(session).active(source)
        if existing is None:
            return False
        existing.revoked_at = (clock or SystemClock()).now()
        return True


async def has_consent(scope: UserScope, source: str, *, factory: Factory = None) -> bool:
    """Whether the user currently consents to a source."""
    async with user_session(scope, factory=factory) as session:
        return await ConsentRepository(session).active(source) is not None


async def require_consent(scope: UserScope, source: str, *, factory: Factory = None) -> None:
    """Raise ConsentRequiredError unless the user currently consents to a source."""
    if not await has_consent(scope, source, factory=factory):
        raise ConsentRequiredError(source)


async def active_consent_id(scope: UserScope, source: str, *, factory: Factory = None) -> UUID:
    """The id of the user's active consent for a source (raises if there is none)."""
    async with user_session(scope, factory=factory) as session:
        consent = await ConsentRepository(session).active(source)
    if consent is None:
        raise ConsentRequiredError(source)
    return consent.id
