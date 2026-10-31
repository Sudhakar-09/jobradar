"""Exception hierarchy for domain errors (docs/coding-standards.md §5, docs/api.md §4).

Every error has a stable ``code`` (mapped to an API problem type) and an optional i18n
``detail_key`` with ``params`` for user-facing messages. Messages never contain personal data.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import ClassVar


class JobRadarError(Exception):
    """Base class for all expected, domain-level failures."""

    code: ClassVar[str] = "internal_error"

    def __init__(
        self,
        message: str = "",
        *,
        detail_key: str | None = None,
        params: Mapping[str, object] | None = None,
    ) -> None:
        """Create an error with an optional i18n message key and parameters."""
        super().__init__(message or self.code)
        self.detail_key = detail_key
        self.params: dict[str, object] = dict(params or {})


class NotFoundError(JobRadarError):
    """The resource does not exist or belongs to another tenant (never reveal which)."""

    code = "not_found"


class ValidationFailedError(JobRadarError):
    """Input failed domain validation."""

    code = "validation_failed"


class UnsafeUrlError(ValidationFailedError):
    """An outbound URL was refused: wrong scheme, or it resolves to a non-public address."""


class PermissionDeniedError(JobRadarError):
    """The caller lacks a scope or role for this action on its own data."""

    code = "forbidden"


class PolicyDeniedError(PermissionDeniedError):
    """The source policy does not allow this access mode on this host (ADR-0022)."""


class ConflictError(JobRadarError):
    """The action conflicts with the current state (duplicate, unique violation)."""

    code = "conflict"


class ConcurrencyConflictError(ConflictError):
    """The resource changed since the caller read it."""

    code = "concurrency_conflict"


class InvalidTransitionError(ConflictError):
    """The application state transition is not allowed (state-machine.md §4)."""

    code = "invalid_transition"


class GuardFailedError(JobRadarError):
    """A safety guard blocked the action (state-machine.md §7)."""

    code = "guard_failed"

    def __init__(self, guard: str, message: str = "") -> None:
        """Create an error for the named guard code."""
        super().__init__(message or guard, detail_key=f"guard.{guard}")
        self.guard = guard


class QuotaExceededError(JobRadarError):
    """A plan limit or global ceiling was reached."""

    code = "quota_exceeded"

    def __init__(self, metric: str, resets_at: datetime) -> None:
        """Create an error for a quota metric and its reset time."""
        super().__init__(
            metric,
            detail_key=f"quota.{metric}",
            params={"metric": metric, "resets_at": resets_at.isoformat()},
        )
        self.metric = metric
        self.resets_at = resets_at


class BudgetExceededError(QuotaExceededError):
    """The user's or deployment's LLM budget is exhausted."""

    code = "budget_exceeded"


class ConsentRequiredError(JobRadarError):
    """The user has not consented to this data source."""

    code = "consent_required"

    def __init__(self, source: str) -> None:
        """Create an error for the consent source that is missing."""
        super().__init__(source, detail_key="consent.required", params={"source": source})
        self.source = source


class ExternalServiceError(JobRadarError):
    """A call to an external service failed."""

    code = "upstream_error"

    def __init__(
        self, service: str, message: str = "", *, retryable: bool, status_code: int | None = None
    ) -> None:
        """Create an error for a named service; ``retryable`` drives retries."""
        super().__init__(message or service, params={"service": service})
        self.service = service
        self.retryable = retryable
        self.status_code = status_code


class RateLimitedError(ExternalServiceError):
    """The external service asked us to slow down (HTTP 429)."""

    code = "upstream_unavailable"

    def __init__(self, service: str, retry_after: float | None) -> None:
        """Create a retryable error carrying the server's Retry-After, if any."""
        super().__init__(service, "rate limited", retryable=True)
        self.retry_after = retry_after


class SchemaDriftError(ExternalServiceError):
    """An external response no longer matches the expected schema."""

    def __init__(self, service: str, message: str = "") -> None:
        """Create a non-retryable schema-drift error."""
        super().__init__(service, message or "schema drift", retryable=False)


class LlmOutputInvalidError(JobRadarError):
    """The LLM output failed schema validation after the repair retry."""

    code = "upstream_error"
