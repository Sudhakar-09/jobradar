"""Company catalogue (US-2.7): verify ATS boards, probe for boards by name, alert suggestions.

Nothing reaches the catalogue from a suggestion or a probe without the owner's decision.
"""

# Postponed annotations: connectors and normalizer depend on each other (RawJob / ingest).
from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Final, Literal
from urllib.parse import urlsplit
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import normalizer
from jobradar.connectors.config import connectors_config, policy_registry
from jobradar.connectors.registry import discover_plugins
from jobradar.connectors.repository import CompanyRepository, SuggestionRepository
from jobradar.connectors.schemas import (
    CompanyEntry,
    CompanyRef,
    Connector,
    ConnectorsFile,
    FetchContext,
    RawJob,
)
from jobradar.core.clock import Clock, SystemClock
from jobradar.core.db import system_session, user_session
from jobradar.core.errors import (
    ExternalServiceError,
    NotFoundError,
    SchemaDriftError,
    ValidationFailedError,
)
from jobradar.core.http import PoliteClient
from jobradar.core.scope import UserScope, system_scope
from jobradar.core.settings import get_settings
from jobradar.core.source_policies import SourcePolicyRegistry
from jobradar.models import CompanySuggestion

CheckStatus = Literal["verified", "no_postings", "not_found", "error", "cached"]
SuggestionStatus = Literal["pending", "accepted", "rejected"]
ATS_ORDER: Final = ("greenhouse", "lever", "ashby", "workable", "smartrecruiters")
VERIFY_CACHE: Final = timedelta(hours=24)  # a board seen this recently is not fetched again
MAX_SLUG_GUESSES: Final = 3
NOT_FOUND_STATUS: Final = 404
PROBE_COMPANY_ID: Final = UUID(int=0)  # jobs fetched by a check are counted, never stored
_SLUG_CHARS: Final = re.compile(r"[^a-z0-9]")
logger = structlog.get_logger(__name__)

ClientFactory = Callable[[SourcePolicyRegistry], PoliteClient]
Factory = async_sessionmaker[AsyncSession] | None


@dataclass(frozen=True, slots=True)
class CompanyCheck:
    """What one ATS board showed: does it exist, and does it list jobs in the countries?"""

    name: str
    ats: str
    slug: str
    status: CheckStatus
    jobs_total: int = 0
    jobs_in_countries: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SuggestionInfo:
    """An employer seen in the user's alerts, as shown for review."""

    id: UUID
    company_name: str
    apply_host: str
    detected_ats: str | None
    detected_slug: str | None
    evidence_count: int
    status: str


@dataclass(frozen=True, slots=True)
class _Boards:
    """The company-board connectors and their endpoint settings."""

    connectors: dict[str, Connector]
    config: ConnectorsFile

    @classmethod
    def load(cls) -> _Boards:
        plugins = discover_plugins()
        return cls(
            connectors={code: plugins[code] for code in ATS_ORDER if code in plugins},
            config=connectors_config(),
        )


def _default_client(registry: SourcePolicyRegistry) -> PoliteClient:
    return PoliteClient(registry, get_settings())


def slug_guesses(name: str) -> list[str]:
    """Likely ATS board slugs for a company name ("Acme Labs LLC" → acmelabs, acme-labs, acme)."""
    words = [_SLUG_CHARS.sub("", word) for word in normalizer.normalize_company(name).split()]
    words = [word for word in words if word]
    if not words:
        return []
    guesses = ["".join(words), "-".join(words), words[0]]
    return list(dict.fromkeys(guesses))[:MAX_SLUG_GUESSES]


def detect_board(url: str, config: ConnectorsFile | None = None) -> tuple[str, str] | None:
    """The (ATS, slug) of a public ATS job link, from `board_urls` in connectors.yaml."""
    config = config or connectors_config()
    for ats in ATS_ORDER:
        settings = config.connectors.get(ats)
        for pattern in settings.board_urls if settings else ():
            match = re.match(pattern, url)
            if match:
                return ats, match.group("slug")
    return None


def _in_countries(jobs: Iterable[RawJob], countries: frozenset[str]) -> int:
    return sum(1 for job in jobs if normalizer.job_country(job) in countries)


async def _check(
    boards: _Boards, http: PoliteClient, ref: CompanyRef, countries: frozenset[str]
) -> CompanyCheck:
    def failed(status: CheckStatus, error: str | None = None) -> CompanyCheck:
        return CompanyCheck(ref.name, ref.ats, ref.ats_slug, status, error=error)

    connector = boards.connectors.get(ref.ats)
    if connector is None:
        return failed("error", f"no connector for {ref.ats}")
    ctx = FetchContext(http=http, settings=boards.config.connectors[ref.ats], company=ref)
    try:
        fetched = await connector.fetch(ctx)
    except SchemaDriftError as exc:
        return failed("error", f"schema drift: {exc}")
    except ExternalServiceError as exc:
        return (
            failed("not_found")
            if exc.status_code == NOT_FOUND_STATUS
            else failed("error", str(exc))
        )
    total = len(fetched.jobs)
    if total == 0:  # SmartRecruiters answers unknown companies with an empty list
        return failed("not_found")
    matching = _in_countries(fetched.jobs, countries)
    return CompanyCheck(
        ref.name,
        ref.ats,
        ref.ats_slug,
        "verified" if matching else "no_postings",
        jobs_total=total,
        jobs_in_countries=matching,
    )


async def verify_entries(
    entries: Sequence[CompanyEntry],
    *,
    countries: frozenset[str] | None = None,
    client_factory: ClientFactory = _default_client,
) -> list[CompanyCheck]:
    """Check the boards of catalogue entries (e.g. a candidate file) without touching the DB.

    Jobs are counted in ``countries``, or in each entry's own countries when None.
    """
    boards = _Boards.load()
    checks: list[CompanyCheck] = []
    async with client_factory(policy_registry()) as http:
        for entry in entries:
            ref = CompanyRef(PROBE_COMPANY_ID, entry.name, entry.ats, entry.ats_slug)
            checks.append(await _check(boards, http, ref, countries or frozenset(entry.countries)))
    return checks


async def verify_companies(
    *,
    countries: frozenset[str] | None = None,
    force: bool = False,
    clock: Clock | None = None,
    client_factory: ClientFactory = _default_client,
    factory: Factory = None,
) -> list[CompanyCheck]:
    """Check every active catalogue board; record found / not found like discovery does.

    Boards verified or fetched within the last day are reported as ``cached`` unless ``force``.
    """
    clock = clock or SystemClock()
    now = clock.now()
    async with system_session(system_scope("companies.verify"), factory=factory) as session:
        rows = [
            (row.id, row.name, row.ats or "", row.ats_slug or "", row.countries, row.verified_at)
            for row in await CompanyRepository(session).catalogue()
        ]
    boards = _Boards.load()
    checks: list[CompanyCheck] = []
    async with client_factory(policy_registry()) as http:
        for company_id, name, ats, slug, own_countries, verified_at in rows:
            if not force and verified_at is not None and now - verified_at < VERIFY_CACHE:
                checks.append(CompanyCheck(name, ats, slug, "cached"))
                continue
            ref = CompanyRef(company_id, name, ats, slug)
            check = await _check(boards, http, ref, countries or frozenset(own_countries))
            checks.append(check)
            async with system_session(system_scope("companies.verify"), factory=factory) as session:
                companies = CompanyRepository(session)
                if check.status in ("verified", "no_postings"):
                    await companies.record_found(company_id, now)
                elif check.status == "not_found":
                    await companies.record_not_found(company_id)
            logger.info("connectors.company_verified", ats=ats, status=check.status)
    return checks


async def _probe_one(
    boards: _Boards, http: PoliteClient, name: str, countries: frozenset[str]
) -> CompanyCheck | None:
    """The first board with jobs in the countries, else the first board with any jobs."""
    fallback: CompanyCheck | None = None
    for ats in boards.connectors:
        for slug in slug_guesses(name):
            check = await _check(
                boards, http, CompanyRef(PROBE_COMPANY_ID, name, ats, slug), countries
            )
            if check.status == "verified":
                return check
            if check.status == "no_postings" and fallback is None:
                fallback = check
    return fallback


async def probe_companies(
    names: Sequence[str],
    *,
    countries: frozenset[str],
    client_factory: ClientFactory = _default_client,
) -> dict[str, CompanyCheck | None]:
    """Look for each company's public board on every supported ATS by guessing its slug.

    A guessed slug can belong to a different company with the same name, so results are
    candidates for the owner to review, never catalogue entries by themselves.
    """
    boards = _Boards.load()
    found: dict[str, CompanyCheck | None] = {}
    async with client_factory(policy_registry()) as http:
        for name in names:
            found[name] = await _probe_one(boards, http, name, countries)
    return found


async def record_suggestions(
    scope: UserScope, jobs: Sequence[RawJob], *, factory: Factory = None
) -> int:
    """Suggest every employer in the jobs that the catalogue does not know yet.

    A job link on a supported ATS gives the board directly; otherwise it can be probed later.
    Returns how many jobs pointed at an unknown employer.
    """
    config = connectors_config()
    counted = 0
    async with user_session(scope, factory=factory) as session:
        known = {normalizer.normalize_company(n) for n in await CompanyRepository(session).names()}
        suggestions = SuggestionRepository(session)
        seen = {
            normalizer.normalize_company(r.company_name): r for r in await suggestions.list(None)
        }
        for job in jobs:
            key = normalizer.normalize_company(job.company_name)
            if key in known:
                continue
            link = str(job.apply_url or job.url)
            board = detect_board(link, config)
            row = seen.get(key)
            if row is None:
                seen[key] = await suggestions.add(
                    user_id=scope.user_id,
                    company_name=job.company_name,
                    apply_host=urlsplit(link).hostname or "",
                    board=board,
                )
            else:
                row.evidence_count += 1
                if board is not None and row.detected_ats is None:
                    row.detected_ats, row.detected_slug = board
            counted += 1
    return counted


def _info(row: CompanySuggestion) -> SuggestionInfo:
    return SuggestionInfo(
        id=row.id,
        company_name=row.company_name,
        apply_host=row.apply_host,
        detected_ats=row.detected_ats,
        detected_slug=row.detected_slug,
        evidence_count=row.evidence_count,
        status=row.status,
    )


async def list_company_suggestions(
    scope: UserScope, *, status: SuggestionStatus | None = "pending", factory: Factory = None
) -> list[SuggestionInfo]:
    """The user's company suggestions (all statuses when ``status`` is None)."""
    async with user_session(scope, factory=factory) as session:
        return [_info(row) for row in await SuggestionRepository(session).list(status)]


async def probe_company_suggestions(
    scope: UserScope,
    *,
    countries: frozenset[str],
    client_factory: ClientFactory = _default_client,
    factory: Factory = None,
) -> list[SuggestionInfo]:
    """Look for an ATS board for each pending suggestion that has none yet; returns updates."""
    pending = [
        s for s in await list_company_suggestions(scope, factory=factory) if s.detected_ats is None
    ]
    found = await probe_companies(
        [s.company_name for s in pending], countries=countries, client_factory=client_factory
    )
    updated: list[SuggestionInfo] = []
    async with user_session(scope, factory=factory) as session:
        repository = SuggestionRepository(session)
        for suggestion in pending:
            check = found.get(suggestion.company_name)
            row = await repository.get(suggestion.id)
            if check is None or row is None:
                continue
            row.detected_ats, row.detected_slug = check.ats, check.slug
            updated.append(_info(row))
    return updated


async def decide_company_suggestion(  # noqa: PLR0913 -- the decision plus optional corrections
    scope: UserScope,
    suggestion_id: UUID,
    *,
    accept: bool,
    countries: Sequence[str] = (),
    board: tuple[str, str] | None = None,
    clock: Clock | None = None,
    factory: Factory = None,
) -> CompanyRef | None:
    """Accept (add or link the company in the catalogue) or reject a pending suggestion.

    ``board`` overrides the detected (ATS, slug). Returns the catalogue company when accepted.

    Raises:
        NotFoundError: no such suggestion for this user.
        ValidationFailedError: already decided, or accepted without a board or countries.
    """
    clock = clock or SystemClock()
    async with user_session(scope, factory=factory) as session:
        row = await SuggestionRepository(session).get(suggestion_id)
        if row is None:
            raise NotFoundError("company suggestion not found")
        if row.status != "pending":
            raise ValidationFailedError(f"suggestion already {row.status}")
        name = row.company_name
        detected = (row.detected_ats, row.detected_slug)
    company: CompanyRef | None = None
    if accept:
        ats, slug = board or detected
        if ats not in ATS_ORDER or not slug:
            raise ValidationFailedError("no ATS board known: probe it or give the ATS and slug")
        if not countries:
            raise ValidationFailedError("give at least one country the company hires in")
        async with system_session(system_scope("companies.accept"), factory=factory) as session:
            company, created = await CompanyRepository(session).link_or_create(
                name=name, ats=ats, ats_slug=slug, countries=[c.upper() for c in countries]
            )
        logger.info("connectors.suggestion_accepted", ats=ats, created=created)
    async with user_session(scope, factory=factory) as session:
        row = await SuggestionRepository(session).get(suggestion_id)
        if row is not None:
            row.status = "accepted" if accept else "rejected"
            row.decided_at = clock.now()
    return company
