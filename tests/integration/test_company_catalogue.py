"""Company catalogue (US-2.7) against the test database: suggestions, decisions, verify."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import accounts, connectors, privacy
from jobradar.connectors.repository import CompanyRepository
from jobradar.connectors.schemas import CompanyEntry
from jobradar.connectors.service.catalogue import record_suggestions
from jobradar.core.clock import FrozenClock
from jobradar.core.db import system_session
from jobradar.core.errors import NotFoundError, ValidationFailedError
from jobradar.core.ids import new_id
from jobradar.core.scope import ClientKind, Role, UserScope, system_scope
from jobradar.core.source_policies import SourcePolicyRegistry
from tests.support.alerts import ALERT_FIXTURES, stream
from tests.support.fake_http import fixture_json, polite_client, routes

pytestmark = [pytest.mark.integration, pytest.mark.anyio]
CLOCK = FrozenClock(datetime(2026, 10, 31, 8, 0, tzinfo=UTC))


def rows(engine: Engine, sql: str) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(sql))]


async def owner_after_alerts(factory: async_sessionmaker[AsyncSession]) -> UserScope:
    owner = await accounts.bootstrap_owner("owner@example.org", factory=factory)
    scope = owner.scope()
    gmail = privacy.consent_text("gmail_alerts")
    await privacy.grant_consent(
        scope, gmail, technical_scope=["gmail.readonly"], clock=CLOCK, factory=factory
    )
    inbox_id = await connectors.create_alert_inbox(scope, kind="gmail", factory=factory)
    await connectors.ingest_alert_messages(
        scope, inbox_id, stream(ALERT_FIXTURES), clock=CLOCK, factory=factory
    )
    return scope


async def seed_catalogue(factory: async_sessionmaker[AsyncSession], *entries: CompanyEntry) -> None:
    async with system_session(system_scope("test.seed"), factory=factory) as session:
        await CompanyRepository(session).sync(list(entries))


def entry(name: str, ats: str, slug: str) -> CompanyEntry:
    return CompanyEntry.model_validate(
        {"name": name, "ats": ats, "ats_slug": slug, "countries": ["AE"], "source": "test"}
    )


def other_user() -> UserScope:
    return UserScope(user_id=new_id(), roles=frozenset({Role.USER}), via=ClientKind.WEB)


async def test_unknown_alert_employers_become_pending_suggestions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await seed_catalogue(session_factory, entry("Example Logistics LLC", "greenhouse", "exlog"))

    scope = await owner_after_alerts(session_factory)

    suggestions = await connectors.list_company_suggestions(scope, factory=session_factory)
    assert [(s.company_name, s.evidence_count) for s in suggestions] == [
        ("Sample Pay", 3),
        ("Fictional Retail", 2),
        ("Sample Bank", 2),
        ("Demo Air", 1),
    ]  # Example Logistics is in the catalogue already (legal suffix ignored)
    assert all(s.status == "pending" and s.detected_ats is None for s in suggestions)
    assert {s.apply_host for s in suggestions} >= {"www.linkedin.com", "www.naukrigulf.com"}


async def test_an_ats_link_in_an_alert_names_the_board(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await accounts.bootstrap_owner("owner@example.org", factory=session_factory)
    job = connectors.RawJob(
        source="alert:linkedin",
        source_job_id="1",
        company_name="Demo Air",
        title="Java Engineer",
        url="https://www.linkedin.com/jobs/view/1/",
        apply_url="https://jobs.ashbyhq.com/demoair/b1",
    )

    assert await record_suggestions(owner.scope(), [job, job], factory=session_factory) == 2

    (suggestion,) = await connectors.list_company_suggestions(
        owner.scope(), factory=session_factory
    )
    assert (suggestion.detected_ats, suggestion.detected_slug) == ("ashby", "demoair")
    assert suggestion.apply_host == "jobs.ashbyhq.com"
    assert suggestion.evidence_count == 2


async def test_accepting_adds_the_company_once_and_rejecting_adds_nothing(
    session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    scope = await owner_after_alerts(session_factory)
    by_name = {
        s.company_name: s.id
        for s in await connectors.list_company_suggestions(scope, factory=session_factory)
    }

    with pytest.raises(ValidationFailedError, match="no ATS board known"):
        await connectors.decide_company_suggestion(
            scope, by_name["Demo Air"], accept=True, countries=["AE"], factory=session_factory
        )
    with pytest.raises(ValidationFailedError, match="country"):
        await connectors.decide_company_suggestion(
            scope, by_name["Demo Air"], accept=True, board=("ashby", "demoair"),
            factory=session_factory,
        )  # fmt: skip
    company = await connectors.decide_company_suggestion(
        scope,
        by_name["Demo Air"],
        accept=True,
        countries=["ae"],
        board=("ashby", "demoair"),
        clock=CLOCK,
        factory=session_factory,
    )
    same_board = await connectors.decide_company_suggestion(
        scope,
        by_name["Sample Bank"],
        accept=True,
        countries=["IN"],
        board=("ashby", "demoair"),
        factory=session_factory,
    )
    rejected = await connectors.decide_company_suggestion(
        scope, by_name["Fictional Retail"], accept=False, factory=session_factory
    )

    assert company is not None
    assert same_board is not None
    assert same_board.id == company.id  # linked, not duplicated
    assert rejected is None
    assert rows(admin_engine, "SELECT name, ats, ats_slug, countries FROM companies") == [
        ("Demo Air", "ashby", "demoair", ["AE", "IN"])
    ]
    decided = await connectors.list_company_suggestions(scope, status=None, factory=session_factory)
    assert {s.company_name: s.status for s in decided} == {
        "Example Logistics": "pending",
        "Sample Pay": "pending",
        "Fictional Retail": "rejected",
        "Sample Bank": "accepted",
        "Demo Air": "accepted",
    }
    with pytest.raises(ValidationFailedError, match="already accepted"):
        await connectors.decide_company_suggestion(
            scope, by_name["Demo Air"], accept=False, factory=session_factory
        )


async def test_another_users_suggestions_are_invisible(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await owner_after_alerts(session_factory)
    first = (await connectors.list_company_suggestions(scope, factory=session_factory))[0]
    stranger = other_user()

    assert await connectors.list_company_suggestions(stranger, factory=session_factory) == []
    with pytest.raises(NotFoundError):
        await connectors.decide_company_suggestion(
            stranger, first.id, accept=False, factory=session_factory
        )


async def test_probe_fills_in_boards_for_pending_suggestions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await owner_after_alerts(session_factory)
    board = fixture_json("connectors", "ashby", "board.json")

    def client(policies: SourcePolicyRegistry) -> object:
        return polite_client(routes({"/posting-api/job-board/demoair": board}), policies)

    updated = await connectors.probe_company_suggestions(
        scope,
        countries=frozenset({"AE"}),
        client_factory=client,  # type: ignore[arg-type]
        factory=session_factory,
    )

    assert [(s.company_name, s.detected_ats, s.detected_slug) for s in updated] == [
        ("Demo Air", "ashby", "demoair")
    ]


async def test_verify_records_results_and_skips_boards_checked_today(
    session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    await seed_catalogue(
        session_factory,
        entry("Example Logistics", "greenhouse", "examplelogistics"),
        entry("Gone Co", "lever", "goneco"),
    )
    board = fixture_json("connectors", "greenhouse", "board.json")
    calls: list[str] = []

    def client(policies: SourcePolicyRegistry) -> object:
        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            return routes({"/v1/boards/examplelogistics/jobs": board})(request)

        return polite_client(handler, policies)

    checks = await connectors.verify_companies(
        clock=CLOCK,
        client_factory=client,  # type: ignore[arg-type]
        factory=session_factory,
    )
    again = await connectors.verify_companies(
        clock=FrozenClock(CLOCK.now() + timedelta(hours=1)),
        client_factory=client,  # type: ignore[arg-type]
        factory=session_factory,
    )

    assert [(c.name, c.status) for c in checks] == [
        ("Example Logistics", "verified"),
        ("Gone Co", "not_found"),
    ]
    assert [(c.name, c.status) for c in again] == [
        ("Example Logistics", "cached"),
        ("Gone Co", "not_found"),
    ]
    assert len(calls) == 3  # the verified board was not fetched a second time
    assert rows(
        admin_engine, "SELECT name, consecutive_not_found FROM companies ORDER BY name"
    ) == [("Example Logistics", 0), ("Gone Co", 2)]
    assert rows(admin_engine, "SELECT count(*) FROM companies WHERE verified_at IS NOT NULL") == [
        (1,)
    ]
