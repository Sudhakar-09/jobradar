"""Role pack schema: job-search knowledge per role (PRD §4.2, ADR-0021)."""

from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from jobradar.core.packs.common import LocaleCode, NonEmptyString, PackModel, Provenance, Slug

IscoCode = Annotated[str, StringConstraints(pattern=r"^\d{1,4}$")]  # ISCO-08 group code


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
