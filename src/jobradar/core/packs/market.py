"""Market pack schema: everything that differs by country or region (PRD §4.1, ADR-0006)."""

from enum import StrEnum
from typing import Final, Literal, Self

from pydantic import Field, HttpUrl, model_validator

from jobradar.core.packs.common import (
    RTL_LANGUAGES,
    CountryCode,
    CurrencyCode,
    LocaleCode,
    NonEmptyString,
    PackModel,
    Provenance,
    SalaryBasis,
    SalaryPeriod,
    Slug,
    language_of,
)
from jobradar.core.source_policies import AccessMode, HostPattern


class Money(PackModel):
    """How salaries are quoted and taxed in a market."""

    currency: CurrencyCode
    quoted_periods: list[SalaryPeriod]
    default_period: SalaryPeriod
    quoted_bases: list[SalaryBasis]
    default_basis: SalaryBasis
    common_allowances: list[NonEmptyString] = Field(default_factory=list)
    income_tax: Literal["progressive", "flat", "none"]
    compensation_model: Slug  # code of the registered CompensationModel plug-in
    notes: NonEmptyString

    @model_validator(mode="after")
    def _defaults_are_listed(self) -> Self:
        if self.default_period not in self.quoted_periods:
            raise ValueError("default_period must be one of quoted_periods")
        if self.default_basis not in self.quoted_bases:
            raise ValueError("default_basis must be one of quoted_bases")
        return self


class LocaleSpec(PackModel):
    """A locale used for jobs and CVs in the market."""

    code: LocaleCode
    rtl: bool

    @model_validator(mode="after")
    def _direction_matches_language(self) -> Self:
        if self.rtl != (language_of(self.code) in RTL_LANGUAGES):
            raise ValueError(f"{self.code}: rtl must be {not self.rtl} for this language")
        return self


class CvField(StrEnum):
    """Optional CV header fields whose default visibility differs by market."""

    NATIONALITY = "nationality"
    CURRENT_LOCATION = "current_location"
    VISA_STATUS = "visa_status"
    NOTICE_PERIOD = "notice_period"
    EARLIEST_JOIN_DATE = "earliest_join_date"
    CURRENT_CTC = "current_ctc"
    EXPECTED_CTC = "expected_ctc"
    DRIVING_LICENCE = "driving_licence"
    PHOTO = "photo"
    DATE_OF_BIRTH = "date_of_birth"
    MARITAL_STATUS = "marital_status"


# Sensitive personal data: never shown on a CV by default, in any market (ADR-0010).
SENSITIVE_CV_FIELDS: Final = frozenset(
    {CvField.PHOTO, CvField.DATE_OF_BIRTH, CvField.MARITAL_STATUS}
)


class CvNorms(PackModel):
    """CV conventions for a market."""

    format: Slug  # CvFormatter plug-in code
    term: NonEmptyString  # what people call it: "CV", "resume", "Lebenslauf"
    length_pages: tuple[int, int]
    photo_customary: bool  # common practice only; the photo is still off by default
    fields_default_on: list[CvField]
    fields_default_off: list[CvField]
    section_order: list[Slug]

    @model_validator(mode="after")
    def _check_fields(self) -> Self:
        on, off = set(self.fields_default_on), set(self.fields_default_off)
        if sensitive_on := sorted(field.value for field in on & SENSITIVE_CV_FIELDS):
            raise ValueError(f"sensitive fields must be off by default: {sensitive_on}")
        if overlap := sorted(field.value for field in on & off):
            raise ValueError(f"fields both on and off by default: {overlap}")
        low, high = self.length_pages
        if not 1 <= low <= high:
            raise ValueError("length_pages must be (min, max) with 1 <= min <= max")
        return self


class VisaRoute(PackModel):
    """A work-authorization route described in a market pack."""

    name: NonEmptyString
    summary: NonEmptyString
    sponsor_required: bool
    official_url: HttpUrl | None = None


class MarketSource(PackModel):
    """A channel jobs come from in this market, and how JobRadar may use it."""

    code: Slug
    name: NonEmptyString
    kind: Literal["ats", "aggregator", "job_board", "professional_network", "recruiter"]
    hosts: list[HostPattern] = Field(default_factory=list)  # empty: "company ATS boards"
    access_modes: frozenset[AccessMode]


class CredentialRecognition(PackModel):
    """Where a field's professional credentials are recognised in this market."""

    field: Slug
    authority: NonEmptyString
    url: HttpUrl | None = None
    notes: NonEmptyString


class MarketPack(PackModel):
    """Country or region configuration: money, language, CV norms, visas and sources."""

    code: Slug
    name: NonEmptyString
    kind: Literal["country", "region"]
    country_codes: list[CountryCode]
    money: Money
    locales: list[LocaleSpec]
    default_locale: LocaleCode
    cv: CvNorms
    visa_routes: list[VisaRoute]
    sponsor_register_source: NonEmptyString | None = None
    nationality_restricted_programmes: list[NonEmptyString] = Field(default_factory=list)
    sources: list[MarketSource]
    notice_period_norm: NonEmptyString
    hiring_seasons: list[NonEmptyString] = Field(default_factory=list)
    language_notes: NonEmptyString
    credential_recognition: list[CredentialRecognition] = Field(default_factory=list)
    provenance: Provenance

    @model_validator(mode="after")
    def _check_market(self) -> Self:
        if self.kind == "country" and len(self.country_codes) != 1:
            raise ValueError("a country market has exactly one country code")
        if not self.locales:
            raise ValueError("at least one locale is required")
        if self.default_locale not in {locale.code for locale in self.locales}:
            raise ValueError("default_locale must be one of locales")
        codes = [source.code for source in self.sources]
        if len(codes) != len(set(codes)):
            raise ValueError("source codes must be unique")
        return self

    @property
    def currency(self) -> str:
        """The market's ISO 4217 currency."""
        return self.money.currency

    @property
    def rtl(self) -> bool:
        """Whether any of the market's locales is written right to left."""
        return any(locale.rtl for locale in self.locales)
