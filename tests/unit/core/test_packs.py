import copy
from pathlib import Path
from typing import Any

import pytest
import structlog
import yaml
from pydantic import ValidationError

from jobradar.core.packs import (
    SENSITIVE_CV_FIELDS,
    CvField,
    MarketPack,
    PersonaPack,
    RolePack,
    load_market_pack,
    load_market_packs,
    load_persona_packs,
    load_role_packs,
    source_policy_problems,
)
from jobradar.core.source_policies import AccessMode, load_source_policies

ROOT = Path(__file__).resolve().parents[3]
PACKS = ROOT / "packs"


def _uae_data() -> dict[str, Any]:
    data = yaml.safe_load((PACKS / "markets" / "uae.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _mid_data() -> dict[str, Any]:
    data = yaml.safe_load((PACKS / "personas" / "mid.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_repository_packs_load_and_validate() -> None:
    markets = {pack.code: pack for pack in load_market_packs(PACKS / "markets")}
    roles = {pack.code: pack for pack in load_role_packs(PACKS / "roles")}
    personas = {pack.code: pack for pack in load_persona_packs(PACKS / "personas")}

    assert set(markets) == {"india", "uae"}
    assert markets["india"].currency == "INR"
    assert markets["uae"].currency == "AED"
    assert roles["java_backend"].isco_08 == "2512"
    assert personas["mid"].default_llm_top_n == 10


def test_uae_pack_matches_owner_decisions() -> None:
    uae = load_market_pack(PACKS / "markets" / "uae.yaml")

    assert uae.money.default_period == "month"
    assert uae.money.income_tax == "none"
    assert uae.rtl is True
    assert {s.code for s in uae.sources} >= {"linkedin", "naukrigulf", "bayt", "gulftalent"}
    assert uae.cv.fields_default_on == [
        CvField.NATIONALITY,
        CvField.CURRENT_LOCATION,
        CvField.VISA_STATUS,
        CvField.NOTICE_PERIOD,
    ]
    assert set(uae.cv.fields_default_off) >= SENSITIVE_CV_FIELDS
    for code in ("linkedin", "naukrigulf", "bayt", "gulftalent"):
        source = next(s for s in uae.sources if s.code == code)
        assert source.access_modes == {AccessMode.ALERT_EMAIL, AccessMode.ONE_TAP}


def test_india_pack_is_ltr() -> None:
    india = load_market_pack(PACKS / "markets" / "india.yaml")

    assert india.rtl is False
    assert india.money.compensation_model == "india_ctc"


def test_market_packs_only_claim_modes_their_source_policies_allow() -> None:
    registry = load_source_policies(ROOT / "config" / "source_policies.yaml")

    for market in load_market_packs(PACKS / "markets"):
        assert source_policy_problems(market, registry) == []


def test_source_policy_problems_reports_overclaimed_mode() -> None:
    registry = load_source_policies(ROOT / "config" / "source_policies.yaml")
    data = _uae_data()
    linkedin = next(s for s in data["sources"] if s["code"] == "linkedin")
    linkedin["access_modes"] = ["alert_email", "extension_assist"]

    problems = source_policy_problems(MarketPack.model_validate(data), registry)

    assert problems
    assert "extension_assist" in problems[0]


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("money", "currency"), "dirham", "currency"),
        (("money", "default_period"), "hour", "default_period"),
        (("cv", "fields_default_on"), ["photo"], "sensitive"),
        (("cv", "fields_default_off"), ["nationality"], "both on and off"),
        (("locales",), [{"code": "ar-AE", "rtl": False}], "rtl"),
        (("default_locale",), "fr-FR", "default_locale"),
        (("country_codes",), ["AE", "SA"], "exactly one country"),
    ],
)
def test_market_pack_rejects_invalid_values(
    path: tuple[str, ...], value: object, message: str
) -> None:
    data = _uae_data()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValidationError, match=message):
        MarketPack.model_validate(data)


def test_market_pack_rejects_unknown_fields() -> None:
    data = _uae_data()
    data["job_boards"] = ["Old field"]

    with pytest.raises(ValidationError):
        MarketPack.model_validate(data)


def test_market_pack_rejects_duplicate_source_codes() -> None:
    data = _uae_data()
    data["sources"].append(copy.deepcopy(data["sources"][0]))

    with pytest.raises(ValidationError, match="unique"):
        MarketPack.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("channel_weights", {"company_ats": 0.5, "referral": 0.4}, "sum to 1"),
        ("channel_weights", {"company_ats": 1.5, "referral": -0.5}, "non-negative"),
        ("daily_volume_range", [8, 3], "daily_volume_range"),
        ("followup_days", [14, 7], "followup_days"),
        ("default_min_fit_score", 120, "less than or equal"),
    ],
)
def test_persona_pack_rejects_invalid_values(field: str, value: object, message: str) -> None:
    data = _mid_data()
    data[field] = value

    with pytest.raises(ValidationError, match=message):
        PersonaPack.model_validate(data)


def test_role_pack_rejects_duplicate_credential_codes() -> None:
    data = yaml.safe_load((PACKS / "roles" / "java_backend.yaml").read_text(encoding="utf-8"))
    credential = {"code": "licence", "name": "Licence", "verification_note": "Check registry."}
    data["required_credentials"] = [credential]
    data["valued_credentials"] = [credential]

    with pytest.raises(ValidationError, match="unique"):
        RolePack.model_validate(data)


def test_duplicate_pack_codes_in_a_directory_are_rejected(tmp_path: Path) -> None:
    text = (PACKS / "personas" / "mid.yaml").read_text(encoding="utf-8")
    (tmp_path / "a.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate persona pack codes"):
        load_persona_packs(tmp_path)


def test_pack_file_must_be_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "market.yaml"
    path.write_text("- not a mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML mapping"):
        load_market_pack(path)


def test_unverified_market_pack_logs_warning() -> None:
    with structlog.testing.capture_logs() as logs:
        load_market_pack(PACKS / "markets" / "uae.yaml")

    assert {
        "event": "packs.verification_missing",
        "pack_kind": "market",
        "pack": "uae",
        "log_level": "warning",
    } in logs


def test_stale_market_pack_logs_warning(tmp_path: Path) -> None:
    data = _uae_data()
    data["provenance"]["last_verified"] = "2020-01-01"
    path = tmp_path / "uae.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with structlog.testing.capture_logs() as logs:
        load_market_pack(path)

    assert any(log["event"] == "packs.verification_stale" for log in logs)
