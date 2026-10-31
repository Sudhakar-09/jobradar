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
    InboxInfo,
    alert_sender_addresses,
    connect_gmail_inbox,
    create_alert_inbox,
    disconnect_inbox,
    gmail_settings,
    ingest_alert_messages,
    ingest_alerts,
    list_inboxes,
)

__all__ = [
    "CompanyEntry",
    "CompanyRef",
    "DiscoveryReport",
    "FetchResult",
    "InboxInfo",
    "RawJob",
    "Skipped",
    "SourceRunResult",
    "alert_sender_addresses",
    "assert_allowed",
    "connect_gmail_inbox",
    "create_alert_inbox",
    "disconnect_inbox",
    "discover",
    "gmail_settings",
    "hosts_with_mode",
    "ingest_alert_messages",
    "ingest_alerts",
    "list_inboxes",
    "policy_for",
    "sync_companies",
]
