"""Global feature flags and their audit trail (operator path until `jobradar_admin` exists)."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobradar.models import AuditLog, SettingsFlag


class FlagRepository:
    """Global rows of `settings_flags`, written with an `audit_log` entry."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open session."""
        self._session = session

    async def get_global(self, key: str) -> SettingsFlag | None:
        """The global flag with this key, if set."""
        return await self._session.scalar(
            select(SettingsFlag).where(SettingsFlag.key == key, SettingsFlag.scope == "global")
        )

    async def all_global(self) -> list[SettingsFlag]:
        """Every global flag, by key."""
        query = select(SettingsFlag).where(SettingsFlag.scope == "global")
        return list((await self._session.scalars(query.order_by(SettingsFlag.key))).all())

    async def set_global(self, key: str, value: Any, actor: UUID | None) -> SettingsFlag:  # noqa: ANN401 -- JSON value
        """Insert or update a global flag."""
        flag = await self.get_global(key)
        if flag is None:
            flag = SettingsFlag(key=key, scope="global")
            self._session.add(flag)
        flag.value = value
        flag.updated_by = actor
        await self._session.flush()
        return flag

    async def audit(self, action: str, actor: UUID | None, detail: dict[str, Any]) -> None:
        """Append an audit entry (IDs and flag values only, never personal data)."""
        self._session.add(AuditLog(action=action, actor_user_id=actor, detail=detail))
