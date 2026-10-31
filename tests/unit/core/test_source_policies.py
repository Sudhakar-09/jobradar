from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from jobradar.core.source_policies import (
    AccessMode,
    RateLimit,
    SourcePolicy,
    SourcePolicyRegistry,
    load_source_policies,
)

ROOT = Path(__file__).resolve().parents[3]
ONE_TAP_ONLY_PLATFORMS = ("linkedin", "indeed", "naukrigulf", "bayt", "gulftalent")


@pytest.fixture(scope="module")
def registry() -> SourcePolicyRegistry:
    return load_source_policies(ROOT / "config" / "source_policies.yaml")


def _policy(**overrides: object) -> SourcePolicy:
    fields: dict[str, object] = {
        "id": "example",
        "name": "Example",
        "hosts": ["jobs.example.com"],
        "modes": [AccessMode.ATS_FEED],
        "rate_limit": RateLimit(per_minute=10, burst=2),
        "last_reviewed": date(2026, 10, 30),
    }
    fields.update(overrides)
    return SourcePolicy.model_validate(fields)


@pytest.mark.parametrize(
    "host",
    [
        "www.linkedin.com",
        "linkedin.com",
        "ae.indeed.com",
        "www.naukrigulf.com",
        "www.bayt.com",
        "www.gulftalent.com",
        "WWW.LinkedIn.com.",
    ],
)
def test_platforms_that_forbid_automation_are_alert_email_and_one_tap_only(
    registry: SourcePolicyRegistry, host: str
) -> None:
    assert registry.policy_for(host).modes == {AccessMode.ALERT_EMAIL, AccessMode.ONE_TAP}


def test_unknown_host_is_one_tap_only(registry: SourcePolicyRegistry) -> None:
    policy = registry.policy_for("careers.unknown-employer.example")

    assert policy.id == "unknown_host"
    assert policy.modes == {AccessMode.ONE_TAP}


def test_ats_boards_allow_feeds_and_assist_but_not_server_apply(
    registry: SourcePolicyRegistry,
) -> None:
    for host in (
        "boards-api.greenhouse.io",
        "api.lever.co",
        "api.ashbyhq.com",
        "apply.workable.com",
        "api.smartrecruiters.com",
    ):
        modes = registry.policy_for(host).modes
        assert AccessMode.ATS_FEED in modes
        assert AccessMode.SERVER_APPLY not in modes


def test_no_policy_grants_automation_to_one_tap_platforms(registry: SourcePolicyRegistry) -> None:
    for policy_id in ONE_TAP_ONLY_PLATFORMS:
        modes = registry.get(policy_id).modes
        assert AccessMode.EXTENSION_ASSIST not in modes
        assert AccessMode.SERVER_APPLY not in modes
        assert AccessMode.ATS_FEED not in modes


def test_hosts_with_mode_lists_extension_assist_hosts(registry: SourcePolicyRegistry) -> None:
    hosts = registry.hosts_with_mode(AccessMode.EXTENSION_ASSIST)

    assert "boards.greenhouse.io" in hosts
    assert not any("linkedin" in host or "indeed" in host for host in hosts)


def test_company_websites_policy_is_logo_fetch_only(registry: SourcePolicyRegistry) -> None:
    policy = registry.get("company_websites")

    assert policy.company_domains is True
    assert policy.modes == {AccessMode.LOGO_FETCH}


def test_policy_rejects_none_combined_with_other_modes() -> None:
    with pytest.raises(ValidationError, match="'none'"):
        _policy(modes=[AccessMode.NONE, AccessMode.ONE_TAP])


def test_company_domain_policy_rejects_modes_other_than_logo_fetch() -> None:
    with pytest.raises(ValidationError, match="logo_fetch"):
        _policy(hosts=[], company_domains=True, modes=[AccessMode.ATS_FEED])


def test_policy_needs_hosts_or_company_domains() -> None:
    with pytest.raises(ValidationError, match="needs hosts"):
        _policy(hosts=[])


@pytest.mark.parametrize("host", ["https://evil.example", "Jobs.Example.com", "localhost"])
def test_policy_rejects_malformed_host_patterns(host: str) -> None:
    with pytest.raises(ValidationError):
        _policy(hosts=[host])


def test_registry_rejects_host_in_two_policies() -> None:
    with pytest.raises(ValueError, match="two policies"):
        SourcePolicyRegistry([_policy(id="a"), _policy(id="b")])


def test_registry_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        SourcePolicyRegistry([_policy(), _policy(hosts=["other.example.com"])])
