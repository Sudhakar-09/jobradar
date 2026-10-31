"""Lever public Postings API (one company site per run)."""

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, HttpUrl, JsonValue

from jobradar.connectors.plugins._base import from_epoch_ms, join_present, parse_items, require
from jobradar.connectors.schemas import FetchContext, FetchResult, RawJob
from jobradar.core.source_policies import AccessMode
from jobradar.core.text import html_to_text

_COUNTRY_CODE_LENGTH = 2


class _Categories(BaseModel):
    model_config = ConfigDict(extra="ignore")
    location: str | None = None
    commitment: str | None = None


class _ListBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str | None = None
    content: str | None = None  # HTML


class _Salary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min: int | None = None
    max: int | None = None
    currency: str | None = None
    interval: str | None = None


class _Posting(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    text: str
    hostedUrl: HttpUrl  # noqa: N815 -- source field name
    applyUrl: HttpUrl | None = None  # noqa: N815
    categories: _Categories | None = None
    createdAt: int | None = None  # noqa: N815 -- epoch milliseconds
    descriptionPlain: str | None = None  # noqa: N815
    additionalPlain: str | None = None  # noqa: N815
    lists: list[_ListBlock] = []
    country: str | None = None
    workplaceType: str | None = None  # noqa: N815
    salaryRange: _Salary | None = None  # noqa: N815


class _Postings(BaseModel):
    """Lever returns a bare JSON list."""

    items: list[JsonValue]


def _description(posting: _Posting) -> str | None:
    blocks = [
        join_present(block.text, html_to_text(block.content or ""), separator="\n")
        for block in posting.lists
    ]
    return join_present(
        posting.descriptionPlain, *blocks, posting.additionalPlain, separator="\n\n"
    )


def _salary(salary: _Salary | None) -> str | None:
    if salary is None or (salary.min is None and salary.max is None):
        return None
    span = "-".join(str(value) for value in (salary.min, salary.max) if value is not None)
    return join_present(span, salary.currency, salary.interval, separator=" ")


class LeverConnector:
    """Reads `/v0/postings/{slug}?mode=json`."""

    code: ClassVar[str] = "lever"
    kind: ClassVar[Literal["company", "query"]] = "company"
    mode: ClassVar[AccessMode] = AccessMode.ATS_FEED
    hosts: ClassVar[tuple[str, ...]] = ("api.lever.co",)

    def is_configured(self) -> str | None:
        """Public board API: no credentials needed."""
        return None

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Fetch every published posting for the company."""
        if ctx.company is None:
            raise ValueError("lever needs a company")
        company = ctx.company
        url = ctx.settings.list_url.format(slug=company.ats_slug)
        body = await ctx.http.get_json(url, mode=self.mode, params=ctx.settings.params)
        postings = require(self.code, {"items": body}, _Postings)

        def to_raw(posting: _Posting) -> RawJob:
            country = (posting.country or "").upper()
            return RawJob(
                source=self.code,
                source_job_id=posting.id,
                company_name=company.name,
                company_id=company.id,
                title=posting.text,
                description=_description(posting),
                url=posting.hostedUrl,
                apply_url=posting.applyUrl or posting.hostedUrl,
                location_raw=posting.categories.location if posting.categories else None,
                country_code=country if len(country) == _COUNTRY_CODE_LENGTH else None,
                remote=(posting.workplaceType == "remote") if posting.workplaceType else None,
                posted_at=from_epoch_ms(posting.createdAt),
                salary_raw=_salary(posting.salaryRange),
                employment_type_raw=posting.categories.commitment if posting.categories else None,
                raw={"id": posting.id, "workplaceType": posting.workplaceType},
            )

        result = FetchResult(pages=1)
        parse_items(self.code, postings.items, _Posting, to_raw, result)
        return result
