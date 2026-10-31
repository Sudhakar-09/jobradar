"""Connectors domain: job sources, the company catalogue and source policies (public API)."""

from jobradar.connectors.schemas import (
    CompanyEntry,
    CompanyRef,
    FetchResult,
    RawJob,
    SourceRunResult,
)
from jobradar.connectors.service import (
    DiscoveryReport,
    Skipped,
    assert_allowed,
    discover,
    hosts_with_mode,
    policy_for,
    sync_companies,
)

__all__ = [
    "CompanyEntry",
    "CompanyRef",
    "DiscoveryReport",
    "FetchResult",
    "RawJob",
    "Skipped",
    "SourceRunResult",
    "assert_allowed",
    "discover",
    "hosts_with_mode",
    "policy_for",
    "sync_companies",
]
