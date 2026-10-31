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
from jobradar.connectors.service.alerts import (
    alert_sender_addresses,
    create_alert_inbox,
    ingest_alert_messages,
)

__all__ = [
    "CompanyEntry",
    "CompanyRef",
    "DiscoveryReport",
    "FetchResult",
    "RawJob",
    "Skipped",
    "SourceRunResult",
    "alert_sender_addresses",
    "assert_allowed",
    "create_alert_inbox",
    "discover",
    "hosts_with_mode",
    "ingest_alert_messages",
    "policy_for",
    "sync_companies",
]
