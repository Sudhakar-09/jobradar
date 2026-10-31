"""Admin domain: feature flags with the rollout gate (more operator tools from Phase 4)."""

from jobradar.admin.service import (
    FlagView,
    conformance_reports,
    list_global_flags,
    set_global_flag,
)

__all__ = ["FlagView", "conformance_reports", "list_global_flags", "set_global_flag"]
