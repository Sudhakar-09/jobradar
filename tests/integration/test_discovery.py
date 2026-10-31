"""`discover` end to end against the test database, with fixture HTTP responses."""

import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import connectors
from jobradar.connectors import service as discovery
from jobradar.core.clock import FrozenClock
from jobradar.core.http import PoliteClient
from jobradar.core.source_policies import SourcePolicyRegistry
from tests.support.fake_http import fixture_json, polite_client, routes

pytestmark = [pytest.mark.integration, pytest.mark.anyio]
COMPANIES = """\
companies:
  - {name: Example Logistics, ats: greenhouse, ats_slug: examplelogistics,
     countries: [AE], source: test}
  - {name: Sample Pay, ats: lever, ats_slug: samplepay, countries: [IN], source: test}
  - {name: Demo Air, ats: ashby, ats_slug: demoair, countries: [AE], source: test}
  - {name: Fictional Retail, ats: workable, ats_slug: fictional-retail,
     countries: [AE], source: test}
  - {name: Sample Bank, ats: smartrecruiters, ats_slug: SampleBank,
     countries: [AE, IN], source: test}
"""


def board_routes() -> dict[str, Any]:
    return {
        "/v1/boards/examplelogistics/jobs": fixture_json("connectors", "greenhouse", "board.json"),
        "/v0/postings/samplepay": fixture_json("connectors", "lever", "postings.json"),
        "/posting-api/job-board/demoair": fixture_json("connectors", "ashby", "board.json"),
        "/api/v1/widget/accounts/fictional-retail": fixture_json(
            "connectors", "workable", "account.json"
        ),
    }


def smartrecruiters_handler(table: dict[str, Any]) -> Any:
    pages = [
        fixture_json("connectors", "smartrecruiters", "page1.json"),
        fixture_json("connectors", "smartrecruiters", "page2.json"),
    ]
    inner = routes(table)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/companies/SampleBank/postings":
            return httpx.Response(200, json=pages[int(request.url.params["offset"]) // 2])
        return inner(request)

    return handler


@pytest.fixture
def catalogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "companies.yaml"
    path.write_text(COMPANIES, encoding="utf-8")
    monkeypatch.setattr(discovery, "companies_path", lambda: path)
    return path


def count(engine: Engine, sql: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(sql)).scalar() or 0)


async def run_discover(
    factory: async_sessionmaker[AsyncSession], table: dict[str, Any], clock: FrozenClock
) -> list[connectors.SourceRunResult]:
    def make_client(policies: SourcePolicyRegistry) -> PoliteClient:
        return polite_client(smartrecruiters_handler(table), policies)

    return await connectors.discover(client_factory=make_client, factory=factory, clock=clock)


async def test_discover_stores_jobs_and_records_runs(
    catalogue: Path, session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    sync = await connectors.sync_companies(factory=session_factory)
    clock = FrozenClock(datetime(2026, 10, 30, 6, 0, tzinfo=UTC))

    results = await run_discover(session_factory, board_routes(), clock)

    assert sync.created == 5
    by_source = {result.connector: result for result in results}
    assert {source: r.jobs_new for source, r in by_source.items()} == {
        "greenhouse": 2,
        "lever": 2,
        "ashby": 1,
        "workable": 1,
        "smartrecruiters": 2,
    }
    assert all(result.items_invalid == 1 for result in results)
    assert {result.status for result in results} <= {"partial", "degraded"}
    assert count(admin_engine, "SELECT count(*) FROM jobs") == 8
    assert (
        count(admin_engine, "SELECT count(*) FROM source_runs WHERE finished_at IS NOT NULL") == 5
    )
    assert count(admin_engine, "SELECT count(*) FROM jobs WHERE country = 'AE'") == 4
    assert count(admin_engine, "SELECT count(*) FROM jobs WHERE apply_host IS NULL") == 0


async def test_rerun_is_idempotent_and_detects_edited_postings(
    catalogue: Path, session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    await connectors.sync_companies(factory=session_factory)
    clock = FrozenClock(datetime(2026, 10, 30, 6, 0, tzinfo=UTC))
    table = board_routes()
    await run_discover(session_factory, table, clock)

    clock.advance(timedelta(hours=2))
    edited = copy.deepcopy(table)
    edited["/v1/boards/examplelogistics/jobs"]["jobs"][0]["content"] = "&lt;p&gt;New text&lt;/p&gt;"
    results = await run_discover(session_factory, edited, clock)

    assert sum(result.jobs_new for result in results) == 0
    assert {r.connector: r.jobs_updated for r in results}["greenhouse"] == 1
    assert count(admin_engine, "SELECT count(*) FROM jobs") == 8
    assert count(admin_engine, "SELECT count(*) FROM job_sources") == 8
    assert count(admin_engine, "SELECT count(*) FROM jobs WHERE last_seen_at > first_seen_at") == 8


async def test_same_job_on_two_boards_is_stored_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_factory: async_sessionmaker[AsyncSession],
    admin_engine: Engine,
) -> None:
    path = tmp_path / "companies.yaml"
    path.write_text(
        "companies:\n"
        "  - {name: Example Logistics, ats: greenhouse, ats_slug: examplelogistics, "
        "countries: [AE], source: test}\n"
        "  - {name: Example Logistics LLC, ats: lever, ats_slug: example-logistics, "
        "countries: [AE], source: test}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(discovery, "companies_path", lambda: path)
    await connectors.sync_companies(factory=session_factory)
    duplicate = {
        "id": "dup-1",
        "text": "Senior Java Backend Engineer",
        "hostedUrl": "https://jobs.lever.co/example-logistics/dup-1",
        "categories": {"location": "Dubai"},
        "country": "AE",
    }
    table = {
        "/v1/boards/examplelogistics/jobs": fixture_json("connectors", "greenhouse", "board.json"),
        "/v0/postings/example-logistics": [duplicate],
    }

    results = await run_discover(session_factory, table, FrozenClock(datetime.now(UTC)))

    assert {r.connector: r.jobs_new for r in results} == {"greenhouse": 2, "lever": 0}
    assert count(admin_engine, "SELECT count(*) FROM jobs") == 2
    assert count(admin_engine, "SELECT count(*) FROM job_sources") == 3


async def test_missing_board_fails_run_and_is_retired_after_three_404s(
    catalogue: Path, session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    await connectors.sync_companies(factory=session_factory)
    clock = FrozenClock(datetime(2026, 10, 30, 6, 0, tzinfo=UTC))
    table = board_routes()
    del table["/v0/postings/samplepay"]

    for _ in range(3):
        results = await run_discover(session_factory, table, clock)
        lever = next(r for r in results if r.connector == "lever")
        assert lever.status == "failed"
        assert lever.http_status_counts == {"404": 1}

    assert count(admin_engine, "SELECT count(*) FROM companies WHERE status = 'not_found'") == 1
    results = await run_discover(session_factory, table, clock)
    assert "lever" not in {result.connector for result in results}


async def test_changed_response_shape_marks_the_run_degraded(
    catalogue: Path, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await connectors.sync_companies(factory=session_factory)
    table = board_routes()
    table["/v1/boards/examplelogistics/jobs"] = {"postings": []}

    results = await run_discover(session_factory, table, FrozenClock(datetime.now(UTC)))

    greenhouse = next(r for r in results if r.connector == "greenhouse")
    assert greenhouse.status == "degraded"
    assert greenhouse.error is not None
    assert greenhouse.error.startswith("schema drift")
