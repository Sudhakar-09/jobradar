"""Connector data models (docs/lld/connectors.md §2)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, ClassVar, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, StringConstraints

from jobradar.core.http import PoliteClient
from jobradar.core.source_policies import AccessMode

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
AtsCode = Literal["greenhouse", "lever", "ashby", "workable", "smartrecruiters"]


class RawJob(BaseModel):
    """A job as a source returned it. Title and description are untrusted third-party text."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str  # connector code, e.g. "greenhouse", "alert:linkedin"
    source_job_id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    company_id: UUID | None = None
    title: str = Field(min_length=1)
    description: str | None = None
    url: HttpUrl
    apply_url: HttpUrl | None = None
    location_raw: str | None = None
    country_code: CountryCode | None = None  # when the source states it explicitly
    city: str | None = None
    remote: bool | None = None
    posted_at: datetime | None = None
    salary_raw: str | None = None
    employment_type_raw: str | None = None
    raw: dict[str, JsonValue] = Field(default_factory=dict)  # job payload only, never email


class SourceRunResult(BaseModel):
    """Outcome of one connector run."""

    run_id: UUID
    connector: str
    company_id: UUID | None
    company_name: str | None
    status: Literal["ok", "partial", "failed", "degraded"]
    jobs_found: int
    jobs_new: int
    jobs_updated: int
    items_invalid: int
    http_status_counts: dict[str, int]
    error: str | None = None


class CompanyEntry(BaseModel):
    """One company in `config/companies.yaml` (the curated catalogue)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    domain: str | None = None
    ats: AtsCode
    ats_slug: str = Field(min_length=1, pattern=r"^[A-Za-z0-9._-]+$")
    countries: list[CountryCode] = Field(min_length=1)
    source: str = Field(min_length=1)  # how we learned the company hires there
    notes: str | None = None


class CompanyFile(BaseModel):
    """`config/companies.yaml`."""

    model_config = ConfigDict(extra="forbid")

    companies: list[CompanyEntry]


@dataclass(frozen=True, slots=True)
class CompanyRef:
    """What a connector needs to know about the company it fetches."""

    id: UUID
    name: str
    ats: str
    ats_slug: str


class ConnectorSettings(BaseModel):
    """Endpoint settings for one connector (`config/connectors.yaml`)."""

    model_config = ConfigDict(extra="forbid")

    list_url: str
    params: dict[str, str | int] = Field(default_factory=dict)
    page_size: int | None = Field(default=None, ge=1)
    max_pages: int | None = Field(default=None, ge=1)
    posting_url: str | None = None


class ConnectorsFile(BaseModel):
    """`config/connectors.yaml`."""

    model_config = ConfigDict(extra="forbid")

    connectors: dict[str, ConnectorSettings]


@dataclass(frozen=True, slots=True)
class FetchContext:
    """Everything a connector may use for one fetch."""

    http: PoliteClient
    settings: ConnectorSettings
    company: CompanyRef | None = None


@dataclass(slots=True)
class FetchResult:
    """Jobs a connector parsed, plus how many items failed validation."""

    jobs: list[RawJob] = field(default_factory=list)
    items_invalid: int = 0
    pages: int = 0


class Connector(Protocol):
    """A job source plug-in (entry point group ``jobradar.connectors``)."""

    code: ClassVar[str]
    mode: ClassVar[AccessMode]
    hosts: ClassVar[tuple[str, ...]]

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Fetch and parse all current jobs for the context's company or query."""
        ...
