"""Workday and unknown hiring systems stay one-tap: no connector, probe or suggestion reads them."""

from jobradar import connectors
from jobradar.connectors.registry import discover_plugins
from jobradar.core.source_policies import AccessMode
from tests.support.fake_http import registry

WORKDAY_JOB = "https://acme.wd3.myworkdayjobs.com/en-US/careers/job/Dubai/Java-Engineer_R1"
UNKNOWN_JOB = "https://careers.example-employer.ae/jobs/123"


def test_workday_and_unknown_hosts_allow_only_one_tap() -> None:
    policies = registry()

    for url_host in ("acme.wd3.myworkdayjobs.com", "careers.example-employer.ae"):
        assert policies.policy_for(url_host).modes == frozenset({AccessMode.ONE_TAP})


def test_no_connector_or_probe_targets_workday() -> None:
    hosts = {host for c in discover_plugins().values() for host in c.hosts}

    assert not any("myworkdayjobs" in host for host in hosts)
    assert "workday" not in connectors.ATS_ORDER


def test_job_links_on_workday_or_unknown_systems_name_no_board() -> None:
    assert connectors.detect_board(WORKDAY_JOB) is None
    assert connectors.detect_board(UNKNOWN_JOB) is None
