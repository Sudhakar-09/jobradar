"""Pack conformance suite v1 (PRD §8a.1, US-2.9)."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from jobradar.core.packs import Provenance, Reference, load_market_pack, load_role_pack
from jobradar.core.packs.conformance import (
    ConformanceInputs,
    check_market,
    check_role,
    run_conformance,
)

pytestmark = pytest.mark.conformance
ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 10, 31)
INPUTS = ConformanceInputs(ROOT / "packs", ROOT / "config", ROOT / "tests" / "golden", TODAY)
VERIFIED = Provenance(
    last_verified=TODAY,
    references=[Reference(title="Official portal", url="https://www.example.gov/")],
)


def market(code: str, *, verified: bool = True):  # type: ignore[no-untyped-def]
    pack = load_market_pack(ROOT / "packs" / "markets" / f"{code}.yaml")
    return pack.model_copy(update={"provenance": VERIFIED}) if verified else pack


def failing(report) -> set[str]:  # type: ignore[no-untyped-def]
    return {check.check for check in report.failures()}


def test_every_pack_gets_a_report() -> None:
    reports = run_conformance(INPUTS)

    assert {(r.kind, r.code) for r in reports} >= {
        ("market", "india"),
        ("market", "uae"),
        ("market", "germany"),
        ("role", "java_backend"),
        ("persona", "mid"),
    }


def test_uae_passes_once_its_pack_is_verified() -> None:
    assert failing(check_market(market("uae", verified=False), INPUTS)) == {"provenance"}
    assert check_market(market("uae"), INPUTS).passed


def test_germany_cannot_be_enabled_yet_and_says_why() -> None:
    report = check_market(market("germany"), INPUTS)

    assert failing(report) == {"sources", "catalogue", "golden_datasets"}
    sources = next(c for c in report.checks if c.check == "sources")
    assert "stepstone: no alert parser" in sources.detail
    assert "xing: no alert parser" in sources.detail
    golden = next(c for c in report.checks if c.check == "golden_datasets")
    assert "linkedin" not in golden.detail  # the German LinkedIn golden sample exists
    assert "company_ats" not in golden.detail


def test_stale_visa_thresholds_fail_the_visa_check() -> None:
    later = replace(INPUTS, today=date(2027, 2, 1))

    report = check_market(market("germany"), later)

    visa = next(c for c in report.checks if c.check == "visa_routes")
    assert not visa.passed
    assert "no values recorded after 2026-12-31" in visa.detail


def test_stale_provenance_fails() -> None:
    old = Provenance(last_verified=date(2026, 1, 1), references=VERIFIED.references)

    report = check_market(market("uae").model_copy(update={"provenance": old}), INPUTS)

    assert "more than 90 days" in next(c for c in report.checks if c.check == "provenance").detail


def test_a_language_without_rules_fails(tmp_path: Path) -> None:
    pack = market("germany")
    french = pack.model_copy(
        update={"locales": [*pack.locales, pack.locales[0].model_copy(update={"code": "fr-FR"})]}
    )

    report = check_market(french, INPUTS)

    assert "fr: no entry" in next(c for c in report.checks if c.check == "language_rules").detail


def test_missing_golden_datasets_fail(tmp_path: Path) -> None:
    report = check_market(market("uae"), replace(INPUTS, golden_dir=tmp_path))

    golden = next(c for c in report.checks if c.check == "golden_datasets")
    assert not golden.passed
    assert "naukrigulf" in golden.detail
    assert "company_ats" in golden.detail


def test_role_pack_needs_provenance() -> None:
    role = load_role_pack(ROOT / "packs" / "roles" / "java_backend.yaml")

    assert failing(check_role(role, INPUTS)) == {"provenance"}
    assert check_role(role.model_copy(update={"provenance": VERIFIED}), INPUTS).passed
