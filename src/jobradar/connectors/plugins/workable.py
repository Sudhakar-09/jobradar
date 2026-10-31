"""Workable public account widget (one company account per run).

The posting fields follow Workable's documented widget format; the live shape is re-checked by
`jobradar companies verify` (Phase 2g) against real UAE-hiring accounts.
"""

from datetime import UTC, date, datetime, time
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, HttpUrl, JsonValue

from jobradar.connectors.plugins._base import join_present, parse_items, require
from jobradar.connectors.schemas import FetchContext, FetchResult, RawJob
from jobradar.core.source_policies import AccessMode
from jobradar.core.text import html_to_text

_COUNTRY_CODE_LENGTH = 2


class _Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    country: str | None = None
    countryCode: str | None = None  # noqa: N815 -- source field name
    city: str | None = None
    region: str | None = None


class _Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shortcode: str
    title: str
    url: HttpUrl
    application_url: HttpUrl | None = None
    employment_type: str | None = None
    telecommuting: bool | None = None
    published_on: date | None = None
    country: str | None = None
    city: str | None = None
    locations: list[_Location] = []
    description: str | None = None  # HTML, present with details=true


class _Account(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jobs: list[JsonValue]


def _country_code(job: _Job) -> str | None:
    for location in job.locations:
        code = (location.countryCode or "").upper()
        if len(code) == _COUNTRY_CODE_LENGTH:
            return code
    return None


class WorkableConnector:
    """Reads `/api/v1/widget/accounts/{slug}?details=true`."""

    code: ClassVar[str] = "workable"
    kind: ClassVar[Literal["company", "query"]] = "company"
    mode: ClassVar[AccessMode] = AccessMode.ATS_FEED
    hosts: ClassVar[tuple[str, ...]] = ("apply.workable.com",)

    def is_configured(self) -> str | None:
        """Public board API: no credentials needed."""
        return None

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Fetch every published job for the company's account."""
        if ctx.company is None:
            raise ValueError("workable needs a company")
        company = ctx.company
        url = ctx.settings.list_url.format(slug=company.ats_slug)
        body = await ctx.http.get_json(url, mode=self.mode, params=ctx.settings.params)
        account = require(self.code, body, _Account)

        def to_raw(job: _Job) -> RawJob:
            published = (
                datetime.combine(job.published_on, time.min, tzinfo=UTC)
                if job.published_on
                else None
            )
            return RawJob(
                source=self.code,
                source_job_id=job.shortcode,
                company_name=company.name,
                company_id=company.id,
                title=job.title,
                description=html_to_text(job.description) if job.description else None,
                url=job.url,
                apply_url=job.application_url or job.url,
                location_raw=join_present(job.city, job.country),
                country_code=_country_code(job),
                city=job.city,
                remote=job.telecommuting,
                posted_at=published,
                employment_type_raw=job.employment_type,
                raw={"shortcode": job.shortcode},
            )

        result = FetchResult(pages=1)
        parse_items(self.code, account.jobs, _Job, to_raw, result)
        return result
