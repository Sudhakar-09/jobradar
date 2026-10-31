"""Ashby public job posting API (one company board per run)."""

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, HttpUrl, JsonValue

from jobradar.connectors.plugins._base import join_present, parse_items, require
from jobradar.connectors.schemas import FetchContext, FetchResult, RawJob
from jobradar.core.source_policies import AccessMode


class _PostalAddress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    addressLocality: str | None = None  # noqa: N815 -- source field names
    addressRegion: str | None = None  # noqa: N815
    addressCountry: str | None = None  # noqa: N815


class _Address(BaseModel):
    model_config = ConfigDict(extra="ignore")
    postalAddress: _PostalAddress | None = None  # noqa: N815


class _Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    location: str | None = None
    isListed: bool = True  # noqa: N815
    isRemote: bool | None = None  # noqa: N815
    employmentType: str | None = None  # noqa: N815
    publishedAt: datetime | None = None  # noqa: N815
    jobUrl: HttpUrl  # noqa: N815
    applyUrl: HttpUrl | None = None  # noqa: N815
    descriptionPlain: str | None = None  # noqa: N815
    address: _Address | None = None


class _Board(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jobs: list[JsonValue]


class AshbyConnector:
    """Reads `/posting-api/job-board/{slug}`."""

    code: ClassVar[str] = "ashby"
    mode: ClassVar[AccessMode] = AccessMode.ATS_FEED
    hosts: ClassVar[tuple[str, ...]] = ("api.ashbyhq.com",)

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Fetch every listed job on the company's board (unlisted jobs are skipped)."""
        if ctx.company is None:
            raise ValueError("ashby needs a company")
        company = ctx.company
        url = ctx.settings.list_url.format(slug=company.ats_slug)
        body = await ctx.http.get_json(url, mode=self.mode, params=ctx.settings.params)
        board = require(self.code, body, _Board)

        def to_raw(job: _Job) -> RawJob | None:
            if not job.isListed:
                return None
            postal = job.address.postalAddress if job.address else None
            return RawJob(
                source=self.code,
                source_job_id=job.id,
                company_name=company.name,
                company_id=company.id,
                title=job.title,
                description=job.descriptionPlain,
                url=job.jobUrl,
                apply_url=job.applyUrl or job.jobUrl,
                location_raw=join_present(job.location, postal.addressCountry if postal else None),
                city=postal.addressLocality if postal else None,
                remote=job.isRemote,
                posted_at=job.publishedAt,
                employment_type_raw=job.employmentType,
                raw={"id": job.id, "location": job.location},
            )

        result = FetchResult(pages=1)
        parse_items(self.code, board.jobs, _Job, to_raw, result)
        return result
