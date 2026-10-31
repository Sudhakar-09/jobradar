from uuid import UUID

import httpx
import pytest

from jobradar.connectors.plugins.ashby import AshbyConnector
from jobradar.connectors.plugins.greenhouse import GreenhouseConnector
from jobradar.connectors.plugins.lever import LeverConnector
from jobradar.connectors.plugins.smartrecruiters import SmartRecruitersConnector
from jobradar.connectors.plugins.workable import WorkableConnector
from jobradar.connectors.schemas import CompanyRef, ConnectorSettings, FetchContext, FetchResult
from jobradar.core.errors import ExternalServiceError, SchemaDriftError
from tests.support.fake_http import ROOT, fixture_json, polite_client, routes

pytestmark = pytest.mark.anyio
CONFIG = __import__("jobradar.connectors.config", fromlist=["load_connectors_file"])
SETTINGS = CONFIG.load_connectors_file(ROOT / "config" / "connectors.yaml").connectors


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def company(ats: str, slug: str, name: str = "Example Co") -> CompanyRef:
    return CompanyRef(id=UUID(int=42), name=name, ats=ats, ats_slug=slug)


async def fetch(connector: object, ats: str, slug: str, table: dict[str, object]) -> FetchResult:
    settings: ConnectorSettings = SETTINGS[ats]
    async with polite_client(routes(table)) as http:
        ctx = FetchContext(http=http, settings=settings, company=company(ats, slug))
        return await connector.fetch(ctx)  # type: ignore[attr-defined, no-any-return]


async def test_greenhouse_parses_jobs_strips_markup_and_counts_invalid() -> None:
    body = fixture_json("connectors", "greenhouse", "board.json")
    result = await fetch(
        GreenhouseConnector(),
        "greenhouse",
        "examplelogistics",
        {"/v1/boards/examplelogistics/jobs": body},
    )

    assert [job.source_job_id for job in result.jobs] == ["4001", "4002"]
    assert result.items_invalid == 1
    first = result.jobs[0]
    assert first.title == "Senior Java Backend Engineer"
    assert first.location_raw == "Dubai, United Arab Emirates"
    assert first.description == "Build Java services with Spring Boot.\n\nKafka"
    assert "alert" not in (first.description or "")
    assert first.company_id == UUID(int=42)
    assert first.posted_at is not None
    assert first.posted_at.isoformat() == "2026-10-20T08:00:00+00:00"


async def test_greenhouse_sends_the_content_parameter() -> None:
    seen: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json={"jobs": []})

    async with polite_client(handler) as http:
        ctx = FetchContext(
            http=http, settings=SETTINGS["greenhouse"], company=company("greenhouse", "x")
        )
        await GreenhouseConnector().fetch(ctx)

    assert seen[0].params["content"] == "true"


async def test_lever_builds_description_country_salary_and_remote() -> None:
    body = fixture_json("connectors", "lever", "postings.json")
    result = await fetch(LeverConnector(), "lever", "samplepay", {"/v0/postings/samplepay": body})

    assert len(result.jobs) == 2
    assert result.items_invalid == 1
    first, second = result.jobs
    assert first.country_code == "IN"
    assert first.remote is False
    assert first.salary_raw == "2400000-3200000 INR per-year-salary"
    assert first.description == (
        "Join the platform team.\n\nWhat you do\nBuild APIs\nWrite tests\n\nWe value diverse teams."
    )
    assert str(first.apply_url).endswith("/apply")
    assert second.remote is True
    assert str(second.apply_url) == str(second.url)


async def test_ashby_skips_unlisted_jobs_and_reads_address() -> None:
    body = fixture_json("connectors", "ashby", "board.json")
    result = await fetch(
        AshbyConnector(), "ashby", "demoair", {"/posting-api/job-board/demoair": body}
    )

    assert [job.title for job in result.jobs] == ["Senior Backend Engineer"]
    assert result.items_invalid == 1
    job = result.jobs[0]
    assert job.city == "Abu Dhabi"
    assert job.location_raw == "Abu Dhabi, United Arab Emirates"
    assert job.remote is False


async def test_workable_reads_country_code_and_utc_publish_date() -> None:
    body = fixture_json("connectors", "workable", "account.json")
    result = await fetch(
        WorkableConnector(),
        "workable",
        "fictional-retail",
        {"/api/v1/widget/accounts/fictional-retail": body},
    )

    assert len(result.jobs) == 1
    assert result.items_invalid == 1
    job = result.jobs[0]
    assert job.country_code == "AE"
    assert job.description == "Scale our order platform."
    assert job.posted_at is not None
    assert job.posted_at.isoformat() == "2026-10-22T00:00:00+00:00"


async def test_smartrecruiters_follows_pagination() -> None:
    pages = [
        fixture_json("connectors", "smartrecruiters", "page1.json"),
        fixture_json("connectors", "smartrecruiters", "page2.json"),
    ]
    offsets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offsets.append(request.url.params["offset"])
        return httpx.Response(200, json=pages[len(offsets) - 1])

    async with polite_client(handler) as http:
        ctx = FetchContext(
            http=http,
            settings=SETTINGS["smartrecruiters"],
            company=company("smartrecruiters", "SampleBank"),
        )
        result = await SmartRecruitersConnector().fetch(ctx)

    assert offsets == ["0", "2"]
    assert result.pages == 2
    assert [job.country_code for job in result.jobs] == ["AE", "IN"]
    assert result.items_invalid == 1
    assert str(result.jobs[0].url) == "https://jobs.smartrecruiters.com/SampleBank/744000000000001"


async def test_unexpected_response_shape_is_schema_drift() -> None:
    with pytest.raises(SchemaDriftError):
        await fetch(
            GreenhouseConnector(),
            "greenhouse",
            "examplelogistics",
            {"/v1/boards/examplelogistics/jobs": {"postings": []}},
        )


async def test_missing_board_raises_not_found_error() -> None:
    with pytest.raises(ExternalServiceError) as error:
        await fetch(LeverConnector(), "lever", "gone", {})

    assert error.value.status_code == 404
    assert error.value.retryable is False


async def test_connectors_refuse_to_run_without_a_company() -> None:
    async with polite_client(routes({})) as http:
        for connector, ats in (
            (GreenhouseConnector(), "greenhouse"),
            (LeverConnector(), "lever"),
            (AshbyConnector(), "ashby"),
            (WorkableConnector(), "workable"),
            (SmartRecruitersConnector(), "smartrecruiters"),
        ):
            with pytest.raises(ValueError, match="needs a company"):
                await connector.fetch(FetchContext(http=http, settings=SETTINGS[ats]))
