from pathlib import Path

import httpx
import pytest

from jobradar.connectors.config import load_connectors_file
from jobradar.connectors.plugins.adzuna import AdzunaConnector
from jobradar.connectors.plugins.remotive import RemotiveConnector
from jobradar.connectors.queries import plan_queries
from jobradar.connectors.schemas import FetchContext
from jobradar.core.packs import load_market_packs, load_role_packs
from jobradar.core.settings import Settings
from tests.support.fake_http import ROOT, fixture_json, polite_client

pytestmark = pytest.mark.anyio
SETTINGS = load_connectors_file(ROOT / "config" / "connectors.yaml").connectors
QUERIES = plan_queries(
    load_market_packs(ROOT / "packs" / "markets"), load_role_packs(ROOT / "packs" / "roles")
)
CREDENTIALS = Settings.model_validate({"adzuna_app_id": "id-123", "adzuna_app_key": "key-456"})


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_queries_cover_every_country_market_and_role() -> None:
    assert {(q.market, q.country, q.role) for q in QUERIES} == {
        ("india", "IN", "java_backend"),
        ("uae", "AE", "java_backend"),
    }
    assert QUERIES[0].terms[0] == "Java Backend Engineer"
    assert QUERIES[0].field == "software_it"


def test_adzuna_reports_missing_credentials() -> None:
    connector = AdzunaConnector(Settings.model_validate({}))

    assert connector.is_configured() == "ADZUNA_APP_ID and ADZUNA_APP_KEY are not set in .env"
    assert AdzunaConnector(CREDENTIALS).is_configured() is None


async def test_adzuna_searches_covered_markets_only_and_never_keeps_predicted_salary() -> None:
    requests: list[httpx.URL] = []
    pages = {
        "Java Backend Engineer": fixture_json(
            "connectors", "adzuna", "search_java_backend_engineer.json"
        ),
        "Java Backend Developer": fixture_json(
            "connectors", "adzuna", "search_java_backend_developer.json"
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url)
        return httpx.Response(
            200, json=pages.get(request.url.params["what_phrase"], {"results": []})
        )

    async with polite_client(handler) as http:
        ctx = FetchContext(http=http, settings=SETTINGS["adzuna"], queries=QUERIES)
        result = await AdzunaConnector(CREDENTIALS).fetch(ctx)

    assert {url.path for url in requests} == {"/v1/api/jobs/in/search/1"}  # UAE not covered
    assert requests[0].params["app_id"] == "id-123"
    assert requests[0].params["max_days_old"] == "3"
    assert [job.source_job_id for job in result.jobs] == ["5001001", "5001002", "5001004"]
    assert result.items_invalid == 1
    first, predicted, no_city = result.jobs
    assert first.title == "Java Backend Engineer"
    assert first.country_code == "IN"
    assert first.city == "Bengaluru"
    assert first.salary_raw == "2400000-3000000 per year"
    assert predicted.salary_raw is None
    assert no_city.city is None


async def test_adzuna_stops_paging_when_a_page_is_short(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"results": []})

    async with polite_client(handler) as http:
        ctx = FetchContext(http=http, settings=SETTINGS["adzuna"], queries=QUERIES[:1])
        await AdzunaConnector(CREDENTIALS).fetch(ctx)

    assert calls == ["/v1/api/jobs/in/search/1"] * len(QUERIES[0].terms)


async def test_adzuna_refuses_to_fetch_without_credentials() -> None:
    async with polite_client(lambda _: httpx.Response(200)) as http:
        ctx = FetchContext(http=http, settings=SETTINGS["adzuna"], queries=QUERIES)
        with pytest.raises(ValueError, match="not configured"):
            await AdzunaConnector(Settings.model_validate({})).fetch(ctx)


async def test_remotive_fetches_each_category_once_and_drops_logos() -> None:
    categories: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        categories.append(request.url.params["category"])
        return httpx.Response(200, json=fixture_json("connectors", "remotive", "software_dev.json"))

    async with polite_client(handler) as http:
        ctx = FetchContext(http=http, settings=SETTINGS["remotive"], queries=QUERIES)
        result = await RemotiveConnector().fetch(ctx)

    assert categories == ["software-dev"]  # India and UAE queries share one category
    assert len(result.jobs) == 2
    assert result.items_invalid == 1
    first, second = result.jobs
    assert first.remote is True
    assert first.posted_at is not None
    assert first.posted_at.isoformat() == "2026-10-29T06:15:00+00:00"
    assert first.salary_raw is None
    assert second.salary_raw == "$80k - $100k"
    assert "logo" not in str(first.raw)
    assert first.description == "Work from anywhere in India."


async def test_remotive_without_mapped_categories_makes_no_requests() -> None:
    calls: list[int] = []
    unmapped = SETTINGS["remotive"].model_copy(update={"categories": {}})

    async with polite_client(lambda r: calls.append(1) or httpx.Response(200)) as http:
        result = await RemotiveConnector().fetch(
            FetchContext(http=http, settings=unmapped, queries=QUERIES)
        )

    assert calls == []
    assert result.jobs == []
