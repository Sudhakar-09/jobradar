"""Shared parsing helpers for connector plug-ins."""

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Final

import structlog
from pydantic import BaseModel, ValidationError

from jobradar.connectors.schemas import FetchResult, RawJob
from jobradar.core.errors import SchemaDriftError

MILLISECONDS_PER_SECOND: Final = 1000
logger = structlog.get_logger(__name__)


def parse_items[ItemT: BaseModel](
    source: str,
    items: Iterable[object],
    model: type[ItemT],
    to_raw: Callable[[ItemT], RawJob | None],
    result: FetchResult,
) -> None:
    """Validate each item and convert it; invalid items are counted, never fatal.

    ``to_raw`` may return None for items that are valid but not jobs to keep (e.g. unlisted).
    """
    for item in items:
        try:
            job = to_raw(model.model_validate(item))
        except ValidationError as exc:
            result.items_invalid += 1
            logger.warning("connectors.item_invalid", source=source, errors=exc.error_count())
            continue
        if job is not None:
            result.jobs.append(job)


def require[EnvelopeT: BaseModel](source: str, body: object, model: type[EnvelopeT]) -> EnvelopeT:
    """Validate a response envelope; a mismatch means the source changed its format."""
    try:
        return model.model_validate(body)
    except ValidationError as exc:
        raise SchemaDriftError(
            source, f"unexpected response shape ({exc.error_count()} errors)"
        ) from exc


def from_epoch_ms(value: int | None) -> datetime | None:
    """Convert epoch milliseconds to an aware UTC datetime."""
    if value is None:
        return None
    return datetime.fromtimestamp(value / MILLISECONDS_PER_SECOND, tz=UTC)


def join_present(*parts: str | None, separator: str = ", ") -> str | None:
    """Join the non-empty parts, or return None if there are none."""
    present = [part.strip() for part in parts if part and part.strip()]
    return separator.join(present) or None
