import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from jobradar.core.aio import loop_factory, run
from jobradar.core.clock import FrozenClock, SystemClock
from jobradar.core.errors import (
    BudgetExceededError,
    ConsentRequiredError,
    ExternalServiceError,
    GuardFailedError,
    JobRadarError,
    NotFoundError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitedError,
    SchemaDriftError,
)
from jobradar.core.ids import new_id
from jobradar.core.scope import ClientKind, Role, UserScope, system_scope


def test_new_id_is_uuid_version_7_with_rfc_variant() -> None:
    value = new_id()

    assert value.version == 7
    assert value.variant == "specified in RFC 4122"


def test_new_ids_sort_by_creation_time() -> None:
    earlier = new_id(unix_ms=1_700_000_000_000)
    later = new_id(unix_ms=1_700_000_000_001)

    assert earlier < later
    assert earlier.int >> 80 == 1_700_000_000_000


def test_new_ids_are_unique() -> None:
    assert len({new_id() for _ in range(1_000)}) == 1_000


def test_frozen_clock_moves_only_when_advanced() -> None:
    clock = FrozenClock(datetime(2026, 10, 30, 8, 0, tzinfo=UTC))

    clock.advance(timedelta(hours=2))

    assert clock.now() == datetime(2026, 10, 30, 10, 0, tzinfo=UTC)


def test_frozen_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FrozenClock(datetime(2026, 10, 30))  # noqa: DTZ001 -- the naive value is the point


def test_system_clock_is_timezone_aware() -> None:
    assert SystemClock().now().tzinfo is UTC


def test_errors_carry_codes_keys_and_params() -> None:
    resets = datetime(2026, 10, 31, tzinfo=UTC)

    assert NotFoundError().code == "not_found"
    assert GuardFailedError("cap_reached").detail_key == "guard.cap_reached"
    assert QuotaExceededError("applications.auto", resets).params["resets_at"] == resets.isoformat()
    assert BudgetExceededError("llm.tokens", resets).code == "budget_exceeded"
    assert ConsentRequiredError("gmail_alerts").params == {"source": "gmail_alerts"}
    assert isinstance(SchemaDriftError("greenhouse"), ExternalServiceError)
    assert SchemaDriftError("greenhouse").retryable is False
    assert RateLimitedError("adzuna", 3.0).retryable is True
    assert issubclass(PermissionDeniedError, JobRadarError)


def _scope(via: ClientKind, scopes: frozenset[str] = frozenset()) -> UserScope:
    return UserScope(
        user_id=UUID(int=1), roles=frozenset({Role.USER}), via=via, token_scopes=scopes
    )


def test_user_scope_roles_and_token_scopes() -> None:
    web = _scope(ClientKind.WEB)
    extension = _scope(ClientKind.EXTENSION, frozenset({"ext:assist"}))

    assert web.has_role(Role.USER)
    assert not web.has_role(Role.ADMIN, Role.OWNER)
    web.require_token_scope("anything")
    extension.require_token_scope("ext:assist")
    with pytest.raises(PermissionDeniedError):
        extension.require_token_scope("ext:record_proof")


def test_system_scope_gets_a_correlation_id() -> None:
    scope = system_scope("discover_all")

    assert scope.task == "discover_all"
    assert scope.correlation_id.version == 7


def test_loop_factory_uses_selector_loop_on_windows_only() -> None:
    assert loop_factory("win32") is asyncio.SelectorEventLoop
    assert loop_factory("linux") is None


def test_run_executes_a_coroutine() -> None:
    async def answer() -> int:
        return 42

    assert run(answer()) == 42
