"""Discovery service: run connectors per company, record runs, hand jobs to the normalizer."""

# Postponed annotations: connectors and normalizer depend on each other (RawJob / ingest).
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Final, Literal
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import normalizer
from jobradar.connectors.config import (
    companies_path,
    connectors_config,
    load_company_file,
    policy_registry,
)
from jobradar.connectors.health import evaluate_health
from jobradar.connectors.queries import plan_queries
from jobradar.connectors.registry import check_connectors, discover_plugins
from jobradar.connectors.repository import CompanyRepository, SourceRunRepository, SyncCounts
from jobradar.connectors.schemas import (
    CompanyRef,
    Connector,
    ConnectorsFile,
    FetchContext,
    FetchResult,
    SourceQuery,
    SourceRunResult,
)
from jobradar.core.clock import Clock, SystemClock
from jobradar.core.db import system_session
from jobradar.core.errors import ExternalServiceError, PolicyDeniedError, SchemaDriftError
from jobradar.core.http import PoliteClient
from jobradar.core.packs import load_market_packs, load_role_packs
from jobradar.core.scope import system_scope
from jobradar.core.settings import get_settings
from jobradar.core.source_policies import AccessMode, SourcePolicy, SourcePolicyRegistry

HISTORY_WINDOW: Final = timedelta(days=7)
NOT_FOUND_STATUS: Final = 404
logger = structlog.get_logger(__name__)

ClientFactory = Callable[[SourcePolicyRegistry], PoliteClient]
Factory = async_sessionmaker[AsyncSession] | None


def policy_for(host: str) -> SourcePolicy:
    """Source policy for a host (unknown hosts are one-tap only; ADR-0022)."""
    return policy_registry().policy_for(host)


def assert_allowed(host: str, mode: AccessMode) -> None:
    """Raise PolicyDeniedError unless the host's policy allows ``mode``."""
    if not policy_registry().is_allowed(host, mode):
        raise PolicyDeniedError(f"{mode.value} is not allowed on {host}")


def hosts_with_mode(mode: AccessMode) -> frozenset[str]:
    """Host patterns whose policy allows ``mode`` (e.g. the extension's host permissions)."""
    return policy_registry().hosts_with_mode(mode)


def _default_client(registry: SourcePolicyRegistry) -> PoliteClient:
    return PoliteClient(registry, get_settings())


async def sync_companies(*, factory: Factory = None) -> SyncCounts:
    """Load `config/companies.yaml` into the catalogue (insert new, update existing)."""
    entries = load_company_file(companies_path()).companies
    async with system_session(system_scope("companies.sync"), factory=factory) as session:
        return await CompanyRepository(session).sync(entries)


@dataclass(frozen=True, slots=True)
class Skipped:
    """A connector that did not run, and why (e.g. not configured, daily budget reached)."""

    connector: str
    reason: str


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    """Everything one discovery pass did."""

    runs: list[SourceRunResult]
    skipped: list[Skipped]


@dataclass(frozen=True, slots=True)
class _Plan:
    connectors: dict[str, Connector]
    config: ConnectorsFile
    companies: list[CompanyRef]
    queries: tuple[SourceQuery, ...]


def _load_queries() -> tuple[SourceQuery, ...]:
    packs_dir = get_settings().packs_dir
    return plan_queries(
        load_market_packs(packs_dir / "markets"), load_role_packs(packs_dir / "roles")
    )


async def _plan(source: str | None, company_id: UUID | None, factory: Factory) -> _Plan:
    connectors = discover_plugins()
    config = connectors_config()
    problems = check_connectors(connectors, policy_registry(), config)
    if problems:
        raise ValueError("connector configuration is inconsistent: " + "; ".join(problems))
    if source is not None and source not in connectors:
        raise ValueError(f"unknown source {source}; known: {sorted(connectors)}")
    async with system_session(system_scope("discover.plan"), factory=factory) as session:
        companies = await CompanyRepository(session).for_discovery(
            ats=source, company_id=company_id
        )
    queries = () if company_id is not None else _load_queries()
    return _Plan(connectors=connectors, config=config, companies=companies, queries=queries)


async def discover(
    *,
    source: str | None = None,
    company_id: UUID | None = None,
    clock: Clock | None = None,
    client_factory: ClientFactory = _default_client,
    factory: Factory = None,
) -> DiscoveryReport:
    """Run every active company board and every aggregator (optionally one source or company).

    A failing source never stops the others; each run is recorded in ``source_runs``.
    Aggregators that are not configured or have used their daily request budget are skipped
    with a reason.
    """
    plan = await _plan(source, company_id, factory)
    clock = clock or SystemClock()
    report = DiscoveryReport(runs=[], skipped=[])
    async with client_factory(policy_registry()) as http:
        for company in plan.companies:
            connector = plan.connectors.get(company.ats)
            if connector is not None and connector.kind == "company":
                settings = plan.config.connectors[company.ats]
                ctx = FetchContext(http=http, settings=settings, company=company)
                report.runs.append(await _run(connector, ctx, clock, factory))
        for code, connector in sorted(plan.connectors.items()):
            if connector.kind != "query" or not plan.queries or source not in (None, code):
                continue
            reason = connector.is_configured() or await _budget_reason(connector, clock, factory)
            if reason is not None:
                logger.info("connectors.run_skipped", connector=code, reason=reason)
                report.skipped.append(Skipped(connector=code, reason=reason))
                continue
            settings = plan.config.connectors[code]
            ctx = FetchContext(http=http, settings=settings, queries=plan.queries)
            report.runs.append(await _run(connector, ctx, clock, factory))
    return report


async def _budget_reason(connector: Connector, clock: Clock, factory: Factory) -> str | None:
    per_day = policy_registry().policy_for(connector.hosts[0]).rate_limit.per_day
    if per_day is None:
        return None
    start_of_day = clock.now().replace(hour=0, minute=0, second=0, microsecond=0)
    async with system_session(system_scope("discover.budget"), factory=factory) as session:
        used = await SourceRunRepository(session).requests_since(connector.code, start_of_day)
    if used >= per_day:
        return f"daily request budget reached ({used}/{per_day} today, UTC)"
    return None


@dataclass(slots=True)
class _Outcome:
    """What happened in one run, before it is recorded."""

    run_id: UUID
    fetched: FetchResult
    statuses: Counter[str]
    error: str | None = None
    counts: normalizer.IngestResult | None = None


async def _run(
    connector: Connector, ctx: FetchContext, clock: Clock, factory: Factory
) -> SourceRunResult:
    company_id = ctx.company.id if ctx.company else None
    scope = system_scope(f"discover.{connector.code}")
    async with system_session(scope, factory=factory) as session:
        run_id = await SourceRunRepository(session).start(connector.code, company_id, clock.now())

    outcome = _Outcome(run_id=run_id, fetched=FetchResult(), statuses=Counter())
    try:
        outcome.fetched = await connector.fetch(ctx)
        outcome.statuses["200"] += outcome.fetched.pages
    except SchemaDriftError as exc:
        outcome.error = f"schema drift: {exc}"
    except ExternalServiceError as exc:
        outcome.error = str(exc)
        outcome.statuses[str(exc.status_code) if exc.status_code else "error"] += 1

    outcome.counts = await normalizer.ingest(
        scope, outcome.fetched.jobs, source_run_id=run_id, clock=clock, factory=factory
    )
    return await _finish(connector, ctx, outcome, clock, factory)


async def _finish(
    connector: Connector, ctx: FetchContext, outcome: _Outcome, clock: Clock, factory: Factory
) -> SourceRunResult:
    company = ctx.company
    company_id = company.id if company else None
    counts = outcome.counts or normalizer.IngestResult(new=0, updated=0, seen=0)
    now = clock.now()
    found = len(outcome.fetched.jobs)
    invalid = outcome.fetched.items_invalid
    async with system_session(system_scope("discover.finish"), factory=factory) as session:
        runs = SourceRunRepository(session)
        companies = CompanyRepository(session)
        if outcome.error is None:
            average = await runs.average_found(connector.code, company_id, now - HISTORY_WINDOW)
            status: Literal["ok", "partial", "failed", "degraded"] = evaluate_health(
                found, invalid, average
            )
            if company_id:
                await companies.record_found(company_id, now)
        else:
            status = "degraded" if outcome.error.startswith("schema drift") else "failed"
            if company_id and outcome.statuses.get(str(NOT_FOUND_STATUS)):
                await companies.record_not_found(company_id)
        await runs.finish(
            outcome.run_id,
            status=status,
            found=found,
            new=counts.new,
            updated=counts.updated,
            invalid=invalid,
            http_status_counts=dict(outcome.statuses),
            error=outcome.error,
            now=now,
        )
    logger.info(
        "connectors.run_finished",
        connector=connector.code,
        company_id=str(company_id) if company_id else None,
        status=status,
        found=found,
        new=counts.new,
        invalid=invalid,
    )
    return SourceRunResult(
        run_id=outcome.run_id,
        connector=connector.code,
        company_id=company_id,
        company_name=company.name if company else None,
        status=status,
        jobs_found=found,
        jobs_new=counts.new,
        jobs_updated=counts.updated,
        items_invalid=invalid,
        http_status_counts=dict(outcome.statuses),
        error=outcome.error,
    )
