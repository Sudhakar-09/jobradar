"""Owner account bootstrap (operator path; docs/lld/database.md §4)."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar.accounts.repository import UserRepository
from jobradar.core.db import operator_session
from jobradar.core.errors import ConflictError
from jobradar.core.scope import ClientKind, Role, UserScope

Factory = async_sessionmaker[AsyncSession] | None


@dataclass(frozen=True, slots=True)
class OwnerAccount:
    """The owner's account id (the email stays in the database, never in logs)."""

    user_id: UUID

    def scope(self) -> UserScope:
        """A scope that acts as the owner (CLI and scheduled work in Stage 1)."""
        return UserScope(user_id=self.user_id, roles=frozenset({Role.OWNER}), via=ClientKind.SYSTEM)


async def find_owner(*, factory: Factory = None) -> OwnerAccount | None:
    """The owner account, if it has been created."""
    async with operator_session(factory=factory) as session:
        owner_id = await UserRepository(session).owner_id()
    return OwnerAccount(user_id=owner_id) if owner_id else None


async def bootstrap_owner(
    email: str, *, timezone: str = "Asia/Kolkata", factory: Factory = None
) -> OwnerAccount:
    """Create the single owner account (Stage 1). Fails if an owner already exists."""
    async with operator_session(factory=factory) as session:
        users = UserRepository(session)
        if await users.owner_id() is not None:
            raise ConflictError("an owner account already exists")
        return OwnerAccount(user_id=await users.add_owner(email.strip(), timezone))
