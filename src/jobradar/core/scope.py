"""Caller scopes: every service call states whose data it may touch (ADR-0017)."""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from jobradar.core.errors import PermissionDeniedError
from jobradar.core.ids import new_id


class Role(StrEnum):
    """Account roles."""

    USER = "user"
    ADMIN = "admin"
    OWNER = "owner"


class ClientKind(StrEnum):
    """Which client made the request."""

    WEB = "web"
    EXTENSION = "extension"
    TELEGRAM = "telegram"
    RUNNER = "runner"
    SYSTEM = "system"
    ADMIN_API = "admin_api"


@dataclass(frozen=True, slots=True)
class UserScope:
    """Acting on behalf of exactly one user; repositories filter by ``user_id``."""

    user_id: UUID
    roles: frozenset[Role]
    via: ClientKind
    token_scopes: frozenset[str] = frozenset()  # empty for web sessions (full user rights)
    correlation_id: UUID = field(default_factory=new_id)

    def has_role(self, *roles: Role) -> bool:
        """Return whether the caller holds any of the given roles."""
        return bool(self.roles.intersection(roles))

    def require_token_scope(self, scope: str) -> None:
        """Raise unless a client token carries ``scope`` (web sessions always pass)."""
        if self.via is not ClientKind.WEB and scope not in self.token_scopes:
            raise PermissionDeniedError(f"missing token scope {scope}")


@dataclass(frozen=True, slots=True)
class SystemScope:
    """Shared-corpus work (discovery, normalization); never touches user-owned tables."""

    task: str
    correlation_id: UUID = field(default_factory=new_id)


def system_scope(task: str) -> SystemScope:
    """Create a system scope for a named background task."""
    return SystemScope(task=task)
