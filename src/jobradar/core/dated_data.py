"""Dated reference data (salary thresholds, later tax tables): values with effective periods.

Each file says when it was last checked against an official source. Lookups warn when the data
is stale: not verified within ``STALE_AFTER``, or the requested date is past the newest entry
(the yearly update has not been recorded yet). Values are never extrapolated.
"""

from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Final, Self

import structlog
import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

STALE_AFTER: Final = timedelta(days=90)
logger = structlog.get_logger(__name__)


class DatedEntry(BaseModel):
    """Values that apply from ``effective_from`` to ``effective_to`` (inclusive)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    effective_from: date
    effective_to: date
    values: dict[str, float]

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.effective_to < self.effective_from:
            raise ValueError("effective_to is before effective_from")
        return self


class DatedTable(BaseModel):
    """One table of dated values, e.g. EU Blue Card salary thresholds for Germany."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    market: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    period: str
    basis: str
    value_notes: dict[str, str]  # what each value key means
    last_verified: date
    sources: list[HttpUrl] = Field(min_length=1)
    entries: list[DatedEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_overlaps(self) -> Self:
        ordered = sorted(self.entries, key=lambda entry: entry.effective_from)
        for before, after in pairwise(ordered):
            if after.effective_from <= before.effective_to:
                raise ValueError(f"{self.name}: entries overlap at {after.effective_from}")
        unexplained = {key for entry in self.entries for key in entry.values} - set(
            self.value_notes
        )
        if unexplained:
            raise ValueError(f"{self.name}: value keys without notes: {sorted(unexplained)}")
        return self

    def stale_reasons(self, on: date) -> list[str]:
        """Why the table should not be trusted on ``on`` (empty: fresh)."""
        reasons: list[str] = []
        if on - self.last_verified > STALE_AFTER:
            reasons.append(f"last verified {self.last_verified}, more than 90 days ago")
        newest = max(entry.effective_to for entry in self.entries)
        if on > newest:
            reasons.append(f"no values recorded after {newest}")
        return reasons

    def values_on(self, on: date) -> dict[str, float] | None:
        """The values in force on ``on``, or None; logs a warning when the data is stale."""
        for reason in self.stale_reasons(on):
            logger.warning("dated_data.stale", table=self.name, reason=reason)
        return next(
            (
                dict(entry.values)
                for entry in self.entries
                if entry.effective_from <= on <= entry.effective_to
            ),
            None,
        )


def load_dated_table(path: Path) -> DatedTable:
    """Load and validate one dated data file."""
    return DatedTable.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
