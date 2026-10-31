"""Structured JSON logging configuration (structlog) with a personal-data filter."""

import logging
import re
from collections.abc import MutableMapping
from typing import Final

import structlog

REDACTED: Final = "[redacted]"
# Keys that must never carry a value into logs (docs/coding-standards.md §8).
PII_KEYS: Final = frozenset(
    {
        "address",
        "body",
        "cookie",
        "cookies",
        "date_of_birth",
        "dob",
        "email",
        "full_name",
        "name",
        "nationality",
        "password",
        "phone",
        "resume_text",
        "salary",
        "secret",
        "subject",
        "token",
        "authorization",
    }
)
EMAIL_PATTERN: Final = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAX_DEPTH: Final = 3


def _scrub(value: object, depth: int) -> object:
    if isinstance(value, str):
        return EMAIL_PATTERN.sub(REDACTED, value)
    if depth >= MAX_DEPTH:
        return value
    if isinstance(value, dict):
        return {
            key: REDACTED if str(key).lower() in PII_KEYS else _scrub(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_scrub(item, depth + 1) for item in value]
    return value


def redact_pii(
    _logger: object, _method: str, event_dict: MutableMapping[str, object]
) -> MutableMapping[str, object]:
    """Structlog processor: drop values of personal-data keys and mask email addresses."""
    for key in list(event_dict):
        if key.lower() in PII_KEYS:
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _scrub(event_dict[key], depth=0)
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog to emit JSON logs at the given level, with PII redaction."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            redact_pii,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
