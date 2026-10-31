"""Pack conformance suite v1 (PRD §8a.1, US-2.9): may a market or role be enabled?

v1 runs the checks that Phase 2 can answer from configuration alone. Later phases add the CV
rendering, compensation model, eligibility and UI checks as their modules arrive. A pack whose
report has any failed check cannot have its ``market.<code>.enabled`` / ``role.<code>.enabled``
flag turned on (admin rollout gate). Golden datasets themselves are verified by
``tests/golden``; here we only check that each source has one.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final

import yaml

from jobradar.core.dated_data import load_dated_table
from jobradar.core.packs.common import Provenance
from jobradar.core.packs.loader import (
    PACK_STALE_AFTER,
    load_market_packs,
    load_persona_packs,
    load_role_packs,
    source_policy_problems,
)
from jobradar.core.packs.market import MarketPack
from jobradar.core.packs.persona import PersonaPack
from jobradar.core.packs.role import RolePack
from jobradar.core.packs.verification import load_verification
from jobradar.core.source_policies import AccessMode, load_source_policies

MIN_CITIES: Final = 3  # a market's gazetteer must name at least its main cities
GOLDEN_EXPECTED_SUFFIX: Final = ".expected.json"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One conformance check for one pack."""

    check: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class PackReport:
    """All checks for one pack."""

    kind: str  # market, role or persona
    code: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True when every check passed."""
        return all(check.passed for check in self.checks)

    def failures(self) -> list[CheckResult]:
        """The checks that failed."""
        return [check for check in self.checks if not check.passed]


@dataclass(frozen=True, slots=True)
class ConformanceInputs:
    """Where the suite reads packs, configuration and golden datasets from."""

    packs_dir: Path
    config_dir: Path
    golden_dir: Path
    today: date


def _check(name: str, problems: Iterable[str]) -> CheckResult:
    listed = sorted(problems)
    return CheckResult(name, not listed, "; ".join(listed))


def _yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return data if isinstance(data, dict) else {}


def _provenance(provenance: Provenance, today: date) -> CheckResult:
    problems = []
    if provenance.last_verified is None:
        problems.append("last_verified is not set")
    elif today - provenance.last_verified > PACK_STALE_AFTER:
        problems.append(f"last verified {provenance.last_verified}, more than 90 days ago")
    if not provenance.references:
        problems.append("no official references")
    return _check("provenance", problems)


def _verification(kind: str, code: str, inputs: ConformanceInputs) -> CheckResult:
    """Every factual value checked against a source (`packs/verification/<code>.yaml`)."""
    path = inputs.packs_dir / "verification" / f"{code}.yaml"
    if not path.is_file():
        return CheckResult("verification", passed=False, detail=f"no {path.name} record")
    record = load_verification(path)
    problems = [f"{item.field}: {item.status.value}" for item in record.blocking()]
    if record.kind != kind or record.pack != code:
        problems.append(f"record is for {record.kind} {record.pack}")
    flagged = len(record.flagged())
    detail = "; ".join(problems) or f"{len(record.items)} values, {flagged} on secondary sources"
    return CheckResult("verification", not problems, detail)


def _visa_routes(pack: MarketPack, inputs: ConformanceInputs) -> CheckResult:
    problems = [f"{r.name}: no official link" for r in pack.visa_routes if r.official_url is None]
    for route in pack.visa_routes:
        if route.salary_thresholds is None:
            continue
        path = inputs.config_dir / "market_data" / route.salary_thresholds
        if not path.is_file():
            problems.append(f"{route.name}: {route.salary_thresholds} is missing")
            continue
        stale = load_dated_table(path).stale_reasons(inputs.today)
        problems.extend(f"{route.name}: {reason}" for reason in stale)
    return _check("visa_routes", problems)


def _gazetteer(pack: MarketPack, inputs: ConformanceInputs) -> CheckResult:
    aliases = _yaml(inputs.config_dir / "locations.yaml")
    countries = aliases.get("countries") or {}
    cities = aliases.get("cities") or {}
    problems = []
    for code in pack.country_codes:
        if not isinstance(countries, dict) or code not in countries:
            problems.append(f"{code}: country names missing in locations.yaml")
        known = cities.get(code) if isinstance(cities, dict) else None
        if not isinstance(known, dict) or len(known) < MIN_CITIES:
            problems.append(f"{code}: fewer than {MIN_CITIES} cities in locations.yaml")
    return _check("gazetteer", problems)


def _languages(pack: MarketPack, inputs: ConformanceInputs) -> CheckResult:
    rules = _yaml(inputs.config_dir / "language_requirements.yaml").get("languages") or {}
    needed = {locale.code.split("-")[0] for locale in pack.locales}
    missing = sorted(code for code in needed if not isinstance(rules, dict) or code not in rules)
    return _check(
        "language_rules", [f"{code}: no entry in language_requirements.yaml" for code in missing]
    )


def _sources(pack: MarketPack, inputs: ConformanceInputs) -> CheckResult:
    policies = load_source_policies(inputs.config_dir / "source_policies.yaml")
    problems = list(source_policy_problems(pack, policies))
    parsers = _yaml(inputs.config_dir / "alert_senders.yaml").get("parsers")
    known = set(parsers) if isinstance(parsers, dict) else set()
    problems.extend(
        f"{source.code}: no alert parser in alert_senders.yaml"
        for source in pack.sources
        if AccessMode.ALERT_EMAIL in source.access_modes and source.code not in known
    )
    return _check("sources", problems)


def _company_countries(config_dir: Path) -> list[set[str]]:
    companies = _yaml(config_dir / "companies.yaml").get("companies")
    if not isinstance(companies, list):
        return []
    return [
        {str(code) for code in company.get("countries") or []}
        for company in companies
        if isinstance(company, dict)
    ]


def _catalogue(pack: MarketPack, inputs: ConformanceInputs) -> CheckResult:
    if not any(source.code == "company_ats" for source in pack.sources):
        return CheckResult("catalogue", passed=True, detail="no company_ats source")
    countries = set(pack.country_codes)
    count = sum(1 for hires in _company_countries(inputs.config_dir) if hires & countries)
    problems = [] if count else ["no catalogue companies hire in this market"]
    return CheckResult("catalogue", not problems, "; ".join(problems) or f"{count} companies")


def _golden(pack: MarketPack, inputs: ConformanceInputs) -> CheckResult:
    root = inputs.golden_dir / pack.code
    problems = []
    for source in pack.sources:
        if AccessMode.ALERT_EMAIL in source.access_modes:
            sample = root / "alerts" / f"{source.code}.eml"
            expected = root / "alerts" / f"{source.code}{GOLDEN_EXPECTED_SUFFIX}"
            if not (sample.is_file() and expected.is_file()):
                problems.append(f"{source.code}: no golden alert sample with expected output")
    if any(source.code == "company_ats" for source in pack.sources):
        boards = list((root / "ats").glob(f"*{GOLDEN_EXPECTED_SUFFIX}")) if root.is_dir() else []
        if not boards:
            problems.append("company_ats: no golden ATS sample with expected output")
    return _check("golden_datasets", problems)


def check_market(pack: MarketPack, inputs: ConformanceInputs) -> PackReport:
    """Every v1 check for one market pack."""
    return PackReport(
        "market",
        pack.code,
        [
            _provenance(pack.provenance, inputs.today),
            _verification("market", pack.code, inputs),
            _visa_routes(pack, inputs),
            _gazetteer(pack, inputs),
            _languages(pack, inputs),
            _sources(pack, inputs),
            _catalogue(pack, inputs),
            _golden(pack, inputs),
        ],
    )


def check_role(pack: RolePack, inputs: ConformanceInputs) -> PackReport:
    """Every v1 check for one role pack."""
    aliases = _check("title_aliases", [] if pack.title_aliases else ["no title aliases"])
    return PackReport("role", pack.code, [_provenance(pack.provenance, inputs.today), aliases])


def check_persona(pack: PersonaPack) -> PackReport:
    """Every v1 check for one persona pack (channel weights are validated on load)."""
    steps = _check("onboarding_steps", [] if pack.onboarding_steps else ["no onboarding steps"])
    return PackReport("persona", pack.code, [steps])


def run_conformance(inputs: ConformanceInputs) -> list[PackReport]:
    """Reports for every market, role and persona pack, in that order."""
    packs = inputs.packs_dir
    return [
        *(check_market(pack, inputs) for pack in load_market_packs(packs / "markets")),
        *(check_role(pack, inputs) for pack in load_role_packs(packs / "roles")),
        *(check_persona(pack) for pack in load_persona_packs(packs / "personas")),
    ]
