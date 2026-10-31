"""Remotive remote-jobs API (aggregator; remote roles).

Remotive asks API users to poll rarely and to link back to the original posting; the source
policy caps requests per day and every job keeps its Remotive URL. Company logos are never
stored or loaded (privacy rule: no third-party images).
"""

from datetime import UTC, datetime
from typing import ClassVar, Literal

import structlog
from pydantic import BaseModel, ConfigDict, HttpUrl, JsonValue

from jobradar.connectors.plugins._base import parse_items, require
from jobradar.connectors.schemas import FetchContext, FetchResult, RawJob
from jobradar.core.source_policies import AccessMode
from jobradar.core.text import html_to_text

logger = structlog.get_logger(__name__)


class _Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    url: HttpUrl
    title: str
    company_name: str
    job_type: str | None = None
    publication_date: datetime | None = None  # sent without a time zone; treated as UTC
    candidate_required_location: str | None = None
    salary: str | None = None
    description: str | None = None  # HTML


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jobs: list[JsonValue]


def _utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


class RemotiveConnector:
    """Reads `/api/remote-jobs?category=…` once per role field category."""

    code: ClassVar[str] = "remotive"
    kind: ClassVar[Literal["company", "query"]] = "query"
    mode: ClassVar[AccessMode] = AccessMode.API
    hosts: ClassVar[tuple[str, ...]] = ("remotive.com",)

    def is_configured(self) -> str | None:
        """Public API: no credentials needed."""
        return None

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Fetch remote jobs for each distinct category of the queried roles."""
        categories = sorted(
            {
                category
                for query in ctx.queries
                if (category := ctx.settings.categories.get(query.field)) is not None
            }
        )
        result = FetchResult()

        def to_raw(job: _Job) -> RawJob:
            return RawJob(
                source=self.code,
                source_job_id=str(job.id),
                company_name=job.company_name,
                title=job.title,
                description=html_to_text(job.description) if job.description else None,
                url=job.url,
                apply_url=job.url,
                location_raw=job.candidate_required_location,
                remote=True,
                posted_at=_utc(job.publication_date),
                salary_raw=job.salary or None,
                employment_type_raw=job.job_type,
                raw={"id": job.id},
            )

        for category in categories:
            params = {**ctx.settings.params, "category": category}
            body = await ctx.http.get_json(ctx.settings.list_url, mode=self.mode, params=params)
            response = require(self.code, body, _Response)
            result.pages += 1
            parse_items(self.code, response.jobs, _Job, to_raw, result)
        if not categories:
            logger.info("connectors.remotive_no_categories")
        return result
