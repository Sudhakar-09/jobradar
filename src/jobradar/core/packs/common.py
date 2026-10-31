"""Shared field types and base model for pack schemas."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]  # ISO 3166-1 alpha-2
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]  # ISO 4217
LocaleCode = Annotated[
    str, StringConstraints(pattern=r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?$")
]  # BCP 47 subset: language[-Script][-REGION]

RTL_LANGUAGES: Final = frozenset({"ar", "dv", "fa", "he", "ps", "ur", "yi"})


def language_of(locale: str) -> str:
    """Return the language subtag of a BCP 47 locale code (``ar-AE`` → ``ar``)."""
    return locale.split("-", 1)[0]


class PackModel(BaseModel):
    """Base for every pack model: unknown keys are errors and strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


class Reference(PackModel):
    """An official or authoritative source a pack fact was checked against."""

    title: NonEmptyString
    url: HttpUrl


class Provenance(PackModel):
    """When a pack's facts were last checked, and against what."""

    last_verified: date | None
    references: list[Reference] = Field(default_factory=list)


class SalaryPeriod(StrEnum):
    """Period a salary figure is quoted for."""

    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class SalaryBasis(StrEnum):
    """What a quoted salary figure includes."""

    GROSS = "gross"
    CTC = "ctc"
    PACKAGE = "package"
    BASIC = "basic"
    NET = "net"
    UNKNOWN = "unknown"
