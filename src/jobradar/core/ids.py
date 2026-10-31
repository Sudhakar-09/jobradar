"""Time-ordered UUIDv7 identifiers (docs/lld/database.md §1)."""

import secrets
import time
from typing import Final
from uuid import UUID

_TIMESTAMP_BITS: Final = 48
_RAND_A_BITS: Final = 12
_RAND_B_BITS: Final = 62
_VERSION: Final = 0x7
_VARIANT: Final = 0b10


def new_id(*, unix_ms: int | None = None) -> UUID:
    """Return a new UUIDv7 (RFC 9562): 48-bit Unix milliseconds followed by random bits.

    Args:
        unix_ms: Timestamp to embed; defaults to now. Only tests should pass it.
    """
    timestamp = (time.time_ns() // 1_000_000 if unix_ms is None else unix_ms) & (
        (1 << _TIMESTAMP_BITS) - 1
    )
    rand_a = secrets.randbits(_RAND_A_BITS)
    rand_b = secrets.randbits(_RAND_B_BITS)
    value = (
        (timestamp << 80) | (_VERSION << 76) | (rand_a << 64) | (_VARIANT << _RAND_B_BITS) | rand_b
    )
    return UUID(int=value)
