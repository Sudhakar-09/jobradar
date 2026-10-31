"""User rows (operator path for the owner bootstrap)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobradar.models import User


class UserRepository:
    """Users visible to the session."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an open session."""
        self._session = session

    async def owner_id(self) -> UUID | None:
        """The id of the owner account, if any."""
        return await self._session.scalar(select(User.id).where(User.role == "owner"))

    async def add_owner(self, email: str, timezone: str) -> UUID:
        """Insert the owner account and return its id."""
        user = User(email=email, role="owner", timezone=timezone)
        self._session.add(user)
        await self._session.flush()
        return user.id
