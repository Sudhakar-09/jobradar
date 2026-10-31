"""Greenhouse public Job Board API (one company board per run)."""

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, HttpUrl, JsonValue

from jobradar.connectors.plugins._base import parse_items, require
from jobradar.connectors.schemas import FetchContext, FetchResult, RawJob
from jobradar.core.source_policies import AccessMode
from jobradar.core.text import html_to_text


class _Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = None


class _Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    title: str
    absolute_url: HttpUrl
    location: _Location | None = None
    content: str | None = None  # entity-escaped HTML
    first_published: datetime | None = None
    updated_at: datetime | None = None


class _Board(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jobs: list[JsonValue]


class GreenhouseConnector:
    """Reads `/v1/boards/{slug}/jobs?content=true`."""

    code: ClassVar[str] = "greenhouse"
    mode: ClassVar[AccessMode] = AccessMode.ATS_FEED
    hosts: ClassVar[tuple[str, ...]] = ("boards-api.greenhouse.io",)

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Fetch every published job on the company's board."""
        if ctx.company is None:
            raise ValueError("greenhouse needs a company")
        company = ctx.company
        url = ctx.settings.list_url.format(slug=company.ats_slug)
        body = await ctx.http.get_json(url, mode=self.mode, params=ctx.settings.params)
        board = require(self.code, body, _Board)

        def to_raw(job: _Job) -> RawJob:
            return RawJob(
                source=self.code,
                source_job_id=str(job.id),
                company_name=company.name,
                company_id=company.id,
                title=job.title,
                description=html_to_text(job.content, escaped=True) if job.content else None,
                url=job.absolute_url,
                apply_url=job.absolute_url,
                location_raw=job.location.name if job.location else None,
                posted_at=job.first_published or job.updated_at,
                raw={"id": job.id, "location": job.location.name if job.location else None},
            )

        result = FetchResult(pages=1)
        parse_items(self.code, board.jobs, _Job, to_raw, result)
        return result
