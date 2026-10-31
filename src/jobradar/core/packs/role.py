"""Role pack schema: job-search knowledge per role (PRD §4.2, ADR-0021)."""

import re
import unicodedata
from typing import Annotated, Final, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from jobradar.core.packs.common import LocaleCode, NonEmptyString, PackModel, Provenance, Slug

IscoCode = Annotated[str, StringConstraints(pattern=r"^\d{1,4}$")]  # ISCO-08 group code
SeniorityLevel = Literal["junior", "mid", "senior", "staff", "executive"]
SENIORITY_ORDER: Final[tuple[SeniorityLevel, ...]] = (
    "junior",
    "mid",
    "senior",
    "staff",
    "executive",
)
_NON_WORD: Final = re.compile(r"[^\w]+")


def _words(text: str) -> str:
    """Folded text as space-separated words, padded so phrases match on word boundaries."""
    folded = unicodedata.normalize("NFKD", text).casefold()
    plain = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return f" {_NON_WORD.sub(' ', plain).strip()} "


def _has(text_words: str, phrase: str) -> bool:
    return _words(phrase) in text_words


class DescriptionMatch(PackModel):
    """Terms a posting's description must contain for a conditional title alias to count."""

    all_of: list[NonEmptyString] = Field(min_length=1)  # every term must appear
    any_of: list[NonEmptyString] = Field(default_factory=list)  # one must appear, when listed

    def matches(self, description: str | None) -> bool:
        """Whether the description shows the required work."""
        words = _words(description or "")
        has_all = all(_has(words, term) for term in self.all_of)
        return has_all and (not self.any_of or any(_has(words, term) for term in self.any_of))


class ConditionalAlias(PackModel):
    """A generic title that counts for this role only when the description shows the role."""

    title: NonEmptyString
    requires_description: DescriptionMatch


class SeniorityBand(PackModel):
    """How one seniority level shows in titles, and the usual years of experience."""

    title_words: list[NonEmptyString] = Field(default_factory=list)
    years: tuple[int, int] | None = None  # [from, to) years of experience for this level

    @model_validator(mode="after")
    def _years_ordered(self) -> Self:
        if self.years is not None and not 0 <= self.years[0] < self.years[1]:
            raise ValueError("years must be [from, to) with 0 <= from < to")
        return self


class SenioritySignals(PackModel):
    """Title words per level; titles without any of them are ``default_level``."""

    default_level: SeniorityLevel = "mid"
    levels: dict[SeniorityLevel, SeniorityBand]

    def level_for(self, title: str) -> SeniorityLevel:
        """The highest level whose title words appear in the title, else the default level."""
        words = _words(title)
        found = [
            level
            for level in SENIORITY_ORDER
            if level in self.levels and any(_has(words, w) for w in self.levels[level].title_words)
        ]
        return found[-1] if found else self.default_level

    def level_for_years(self, min_years: float) -> SeniorityLevel | None:
        """The lowest level whose year range contains a posting's minimum years, if any."""
        return next(
            (
                level
                for level in SENIORITY_ORDER
                if (band := self.levels.get(level)) is not None
                and band.years is not None
                and band.years[0] <= min_years < band.years[1]
            ),
            None,
        )

    @model_validator(mode="after")
    def _ranges_increase(self) -> Self:
        starts = [b.years[0] for lvl in SENIORITY_ORDER if (b := self.levels.get(lvl)) and b.years]
        if starts != sorted(starts):
            raise ValueError("seniority year ranges must start in level order")
        return self


class CredentialRequirement(PackModel):
    """A licence, registration or certification relevant to a role."""

    code: Slug
    name: NonEmptyString
    markets: list[Slug] = Field(default_factory=list)  # market codes; empty = all markets
    verification_note: NonEmptyString


class HiringPatterns(PackModel):
    """How hiring for the role usually works."""

    channels: list[Slug]
    stages: list[NonEmptyString]
    assessment_types: list[NonEmptyString]
    seasonality: NonEmptyString | None = None
    typical_weeks_to_hire: tuple[int, int] | None = None


class RolePack(PackModel):
    """Role configuration within the field → family → role taxonomy."""

    code: Slug
    field: Slug
    family: Slug
    isco_08: IscoCode
    title_aliases: list[NonEmptyString]
    title_aliases_by_locale: dict[LocaleCode, list[NonEmptyString]] = Field(default_factory=dict)
    # Generic titles ("Software Engineer") that count only with a description match (Phase 3).
    conditional_title_aliases: list[ConditionalAlias] = Field(default_factory=list)
    seniority_signals: SenioritySignals | None = None
    core_skills: list[NonEmptyString]
    adjacent_roles: list[NonEmptyString] = Field(default_factory=list)
    signal_documents: list[NonEmptyString]
    required_credentials: list[CredentialRequirement] = Field(default_factory=list)
    valued_credentials: list[CredentialRequirement] = Field(default_factory=list)
    hiring_patterns: HiringPatterns
    resume_emphasis: list[NonEmptyString]
    provenance: Provenance

    @model_validator(mode="after")
    def _check_role(self) -> Self:
        if not self.title_aliases:
            raise ValueError("at least one title alias is required")
        codes = [c.code for c in [*self.required_credentials, *self.valued_credentials]]
        if len(codes) != len(set(codes)):
            raise ValueError("credential codes must be unique within a role")
        return self
