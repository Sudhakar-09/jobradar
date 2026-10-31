"""SmartRecruiters public Posting API (paginated, one company per run).

The list endpoint has no job description; fetching each posting's detail would multiply
requests, so descriptions are left empty in Phase 2 and filled later if matching needs them.
"""

from datetime import datetime
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, HttpUrl, JsonValue

from jobradar.connectors.plugins._base import parse_items, require
from jobradar.connectors.schemas import FetchContext, FetchResult, RawJob
from jobradar.core.source_policies import AccessMode

DEFAULT_PAGE_SIZE: Final = 100
DEFAULT_MAX_PAGES: Final = 10
_COUNTRY_CODE_LENGTH: Final = 2


class _Label(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: str | None = None


class _Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    city: str | None = None
    region: str | None = None
    country: str | None = None  # lower-case ISO code
    remote: bool | None = None
    fullLocation: str | None = None  # noqa: N815 -- source field name


class _Posting(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    releasedDate: datetime | None = None  # noqa: N815
    location: _Location | None = None
    typeOfEmployment: _Label | None = None  # noqa: N815


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore")
    offset: int
    limit: int
    totalFound: int  # noqa: N815
    content: list[JsonValue]


class SmartRecruitersConnector:
    """Reads `/v1/companies/{slug}/postings` page by page."""

    code: ClassVar[str] = "smartrecruiters"
    mode: ClassVar[AccessMode] = AccessMode.ATS_FEED
    hosts: ClassVar[tuple[str, ...]] = ("api.smartrecruiters.com",)

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Fetch every posting, following pagination up to the configured page limit."""
        if ctx.company is None:
            raise ValueError("smartrecruiters needs a company")
        if ctx.settings.posting_url is None:
            raise ValueError("smartrecruiters needs posting_url in config/connectors.yaml")
        company = ctx.company
        posting_url = ctx.settings.posting_url
        page_size = ctx.settings.page_size or DEFAULT_PAGE_SIZE
        max_pages = ctx.settings.max_pages or DEFAULT_MAX_PAGES
        url = ctx.settings.list_url.format(slug=company.ats_slug)

        def to_raw(posting: _Posting) -> RawJob:
            location = posting.location
            country = (location.country or "").upper() if location else ""
            public_url = HttpUrl(posting_url.format(slug=company.ats_slug, id=posting.id))
            return RawJob(
                source=self.code,
                source_job_id=posting.id,
                company_name=company.name,
                company_id=company.id,
                title=posting.name,
                url=public_url,
                apply_url=public_url,
                location_raw=location.fullLocation if location else None,
                country_code=country if len(country) == _COUNTRY_CODE_LENGTH else None,
                city=location.city if location else None,
                remote=location.remote if location else None,
                posted_at=posting.releasedDate,
                employment_type_raw=posting.typeOfEmployment.label
                if posting.typeOfEmployment
                else None,
                raw={"id": posting.id},
            )

        result = FetchResult()
        offset = 0
        while result.pages < max_pages:
            params = {**ctx.settings.params, "limit": page_size, "offset": offset}
            body = await ctx.http.get_json(url, mode=self.mode, params=params)
            page = require(self.code, body, _Page)
            result.pages += 1
            parse_items(self.code, page.content, _Posting, to_raw, result)
            offset = page.offset + max(page.limit, 1)
            if not page.content or offset >= page.totalFound:
                break
        return result
