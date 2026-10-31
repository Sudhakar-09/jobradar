"""Adzuna search API (aggregator; India in the first configuration).

Needs the owner's app id and key (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY` in `.env`); without them the
connector reports that it is not configured and discovery skips it. Predicted salaries are never
stored: JobRadar only keeps figures the employer published.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, Final, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, field_validator

from jobradar.connectors.plugins._base import parse_items, require
from jobradar.connectors.schemas import FetchContext, FetchResult, RawJob, SourceQuery
from jobradar.core.settings import Settings, get_settings
from jobradar.core.source_policies import AccessMode
from jobradar.core.text import html_to_text

DEFAULT_MAX_PAGES: Final = 1
DEFAULT_PAGE_SIZE: Final = 50
_MIN_AREA_PARTS_FOR_CITY: Final = 3  # ["India", "Karnataka", "Bengaluru"]
logger = structlog.get_logger(__name__)


class _Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display_name: str = Field(min_length=1)


class _Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display_name: str | None = None
    area: list[str] = []


class _Result(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str | None = None
    redirect_url: HttpUrl
    company: _Company
    location: _Location | None = None
    created: datetime | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_is_predicted: bool = False
    contract_time: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _id_as_text(cls, value: object) -> object:
        return str(value) if isinstance(value, int) else value

    @field_validator("salary_is_predicted", mode="before")
    @classmethod
    def _predicted_flag(cls, value: object) -> object:
        return str(value) == "1" if isinstance(value, (str, int)) else value


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore")
    results: list[JsonValue]


def _salary(result: _Result) -> str | None:
    if result.salary_is_predicted or (result.salary_min is None and result.salary_max is None):
        return None
    span = "-".join(
        str(int(value)) for value in (result.salary_min, result.salary_max) if value is not None
    )
    return f"{span} per year"


class AdzunaConnector:
    """Searches `/v1/api/jobs/{country}/search/{page}` for each role alias in covered markets."""

    code: ClassVar[str] = "adzuna"
    kind: ClassVar[Literal["company", "query"]] = "query"
    mode: ClassVar[AccessMode] = AccessMode.API
    hosts: ClassVar[tuple[str, ...]] = ("api.adzuna.com",)

    def __init__(self, settings: Settings | None = None) -> None:
        """Use ``settings`` (tests) or the process settings for credentials."""
        self._settings = settings

    def _credentials(self) -> tuple[str, str] | None:
        settings = self._settings or get_settings()
        if settings.adzuna_app_id and settings.adzuna_app_key:
            return settings.adzuna_app_id, settings.adzuna_app_key.get_secret_value()
        return None

    def is_configured(self) -> str | None:
        """Adzuna needs the owner's app id and key."""
        if self._credentials() is None:
            return "ADZUNA_APP_ID and ADZUNA_APP_KEY are not set in .env"
        return None

    async def fetch(self, ctx: FetchContext) -> FetchResult:
        """Run every query for markets Adzuna covers; markets it does not cover are skipped."""
        credentials = self._credentials()
        if credentials is None:
            raise ValueError("adzuna is not configured")
        search = _Search(code=self.code, mode=self.mode, ctx=ctx, credentials=credentials)
        for query in ctx.queries:
            country_path = ctx.settings.countries.get(query.market)
            if country_path is None:
                logger.info("connectors.adzuna_country_not_covered", market=query.market)
                continue
            for term in query.terms:
                await search.run(query, country_path, term)
        return search.result


@dataclass(slots=True)
class _Search:
    """State for one Adzuna run: credentials, collected jobs, and ids already seen."""

    code: str
    mode: AccessMode
    ctx: FetchContext
    credentials: tuple[str, str]
    result: FetchResult = field(default_factory=FetchResult)
    seen: set[str] = field(default_factory=set)

    def to_raw(self, item: _Result, query: SourceQuery) -> RawJob | None:
        if item.id in self.seen:  # the same job matched another alias
            return None
        self.seen.add(item.id)
        area = item.location.area if item.location else []
        return RawJob(
            source=self.code,
            source_job_id=item.id,
            company_name=item.company.display_name,
            title=html_to_text(item.title),
            description=html_to_text(item.description) if item.description else None,
            url=item.redirect_url,
            apply_url=item.redirect_url,
            location_raw=item.location.display_name if item.location else None,
            country_code=query.country,
            city=area[-1] if len(area) >= _MIN_AREA_PARTS_FOR_CITY else None,
            posted_at=item.created,
            salary_raw=_salary(item),
            employment_type_raw=item.contract_time,
            raw={"id": item.id, "query_role": query.role},
        )

    async def run(self, query: SourceQuery, country_path: str, term: str) -> None:
        settings = self.ctx.settings
        app_id, app_key = self.credentials
        page_size = int(settings.params.get("results_per_page", DEFAULT_PAGE_SIZE))
        for page in range(1, (settings.max_pages or DEFAULT_MAX_PAGES) + 1):
            url = settings.list_url.format(country=country_path, page=page)
            params = {**settings.params, "app_id": app_id, "app_key": app_key, "what_phrase": term}
            body = await self.ctx.http.get_json(url, mode=self.mode, params=params)
            page_body = require(self.code, body, _Page)
            self.result.pages += 1
            parse_items(
                self.code,
                page_body.results,
                _Result,
                lambda item: self.to_raw(item, query),
                self.result,
            )
            if len(page_body.results) < page_size:
                break
