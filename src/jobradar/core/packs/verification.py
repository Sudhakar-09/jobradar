"""Per-value verification records for packs (`packs/verification/<code>.yaml`).

Each factual value in a pack is checked against a source and recorded with the URL and date.
``verified``: an official government or authority source confirms it. ``secondary``: only a
reputable non-official source does (flagged for review, does not block). ``contradicted`` or
``unverified`` block the pack in conformance unless the owner explicitly accepted the value.
"""

from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from jobradar.core.packs.common import NonEmptyString


class VerificationStatus(StrEnum):
    """How well a value is supported."""

    VERIFIED = "verified"
    SECONDARY = "secondary"
    CONTRADICTED = "contradicted"
    UNVERIFIED = "unverified"


class VerifiedValue(BaseModel):
    """One factual value and the evidence for it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: NonEmptyString  # dotted path into the pack or data file, or a short label
    claim: NonEmptyString
    status: VerificationStatus
    source_title: str | None = None
    source_url: HttpUrl | None = None
    checked_on: date
    notes: str = ""
    owner_accepted_on: date | None = None  # owner accepted a value that is not verified

    @model_validator(mode="after")
    def _evidence(self) -> Self:
        needs_source = self.status in (VerificationStatus.VERIFIED, VerificationStatus.SECONDARY)
        if needs_source and self.source_url is None:
            raise ValueError(f"{self.field}: {self.status} needs a source_url")
        return self

    @property
    def blocks(self) -> bool:
        """Whether this value stops the pack from passing conformance."""
        unsettled = self.status in (VerificationStatus.CONTRADICTED, VerificationStatus.UNVERIFIED)
        return unsettled and self.owner_accepted_on is None


class VerificationRecord(BaseModel):
    """`packs/verification/<code>.yaml`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pack: NonEmptyString
    kind: str = "market"
    items: list[VerifiedValue] = Field(min_length=1)

    def flagged(self) -> list[VerifiedValue]:
        """Values resting on secondary sources (reviewed, not blocking)."""
        return [item for item in self.items if item.status is VerificationStatus.SECONDARY]

    def blocking(self) -> list[VerifiedValue]:
        """Values that keep the pack from passing."""
        return [item for item in self.items if item.blocks]


def load_verification(path: Path) -> VerificationRecord:
    """Load and validate one verification record."""
    return VerificationRecord.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
