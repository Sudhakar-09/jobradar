"""Injectable clock so domain logic never calls ``datetime.now()`` directly."""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Source of the current time (timezone-aware UTC)."""

    def now(self) -> datetime:
        """Return the current instant in UTC."""
        ...


class SystemClock:
    """The real clock."""

    def now(self) -> datetime:
        """Return the current instant in UTC."""
        return datetime.now(UTC)


class FrozenClock:
    """A clock that only moves when told to (tests, replays)."""

    def __init__(self, instant: datetime) -> None:
        """Start at ``instant``, which must be timezone-aware."""
        if instant.tzinfo is None:
            raise ValueError("FrozenClock needs a timezone-aware datetime")
        self._instant = instant.astimezone(UTC)

    def now(self) -> datetime:
        """Return the frozen instant."""
        return self._instant

    def advance(self, delta: timedelta) -> None:
        """Move the clock forward."""
        self._instant += delta
