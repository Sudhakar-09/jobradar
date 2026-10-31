"""Privacy domain: consent per data source (export and deletion arrive in Phase 10)."""

from jobradar.privacy.service import (
    ConsentText,
    active_consent_id,
    consent_text,
    grant_consent,
    has_consent,
    require_consent,
    revoke_consent,
)

__all__ = [
    "ConsentText",
    "active_consent_id",
    "consent_text",
    "grant_consent",
    "has_consent",
    "require_consent",
    "revoke_consent",
]
