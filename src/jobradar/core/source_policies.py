"""Source policy registry: which access modes JobRadar may use on each host (ADR-0022).

The registry is configuration (`config/source_policies.yaml`), validated on load. Connectors,
apply adapters and the browser extension must consult it; unknown hosts are one-tap only.
"""

from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Final, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

HostPattern = Annotated[
    str, StringConstraints(pattern=r"^(\*\.)?[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9-]+)+$")
]  # exact host, or "*.example.com" for any subdomain


class AccessMode(StrEnum):
    """What JobRadar is allowed to do with a source."""

    API = "api"
    ATS_FEED = "ats_feed"
    ALERT_EMAIL = "alert_email"
    EXTENSION_ASSIST = "extension_assist"
    SERVER_APPLY = "server_apply"
    ONE_TAP = "one_tap"
    LOGO_FETCH = "logo_fetch"
    NONE = "none"


# Modes that let JobRadar act on a site rather than only read alerts or hand over a link.
AUTOMATED_MODES: Final = frozenset(
    {AccessMode.API, AccessMode.ATS_FEED, AccessMode.EXTENSION_ASSIST, AccessMode.SERVER_APPLY}
)


class RateLimit(BaseModel):
    """Polite request budget for a source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    per_minute: int = Field(ge=1)
    burst: int = Field(ge=1)
    per_day: int | None = Field(default=None, ge=1)


class SourcePolicy(BaseModel):
    """Allowed access modes and politeness rules for one source."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
    name: str
    hosts: list[HostPattern] = []
    company_domains: bool = False  # applies to catalogued companies' own domains (logo proxy)
    modes: frozenset[AccessMode]
    rate_limit: RateLimit
    docs_url: HttpUrl | None = None
    terms_url: HttpUrl | None = None
    notes: str | None = None
    last_reviewed: date

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if AccessMode.NONE in self.modes and len(self.modes) > 1:
            raise ValueError(f"{self.id}: 'none' cannot be combined with other modes")
        if not self.hosts and not self.company_domains:
            raise ValueError(f"{self.id}: needs hosts or company_domains: true")
        if self.company_domains and self.modes != {AccessMode.LOGO_FETCH}:
            raise ValueError(f"{self.id}: company domains may only use logo_fetch (ADR-0022)")
        return self


DEFAULT_POLICY: Final = SourcePolicy(
    id="unknown_host",
    name="Unknown host",
    hosts=["unknown.invalid"],
    modes=frozenset({AccessMode.ONE_TAP}),
    rate_limit=RateLimit(per_minute=1, burst=1),
    notes="Any host without an entry is one-tap only (ADR-0022).",
    last_reviewed=date(2026, 10, 30),
)


class SourcePolicyRegistry:
    """Looks up the policy for a host; exact hosts win over wildcard patterns."""

    def __init__(self, policies: list[SourcePolicy]) -> None:
        """Index policies by host pattern; a host may appear in only one policy."""
        self._exact: dict[str, SourcePolicy] = {}
        self._wildcard: dict[str, SourcePolicy] = {}
        self._by_id: dict[str, SourcePolicy] = {}
        for policy in policies:
            if policy.id in self._by_id:
                raise ValueError(f"duplicate source policy id: {policy.id}")
            self._by_id[policy.id] = policy
            for pattern in policy.hosts:
                index = self._wildcard if pattern.startswith("*.") else self._exact
                key = pattern.removeprefix("*.")
                if key in index:
                    raise ValueError(f"host pattern {pattern} is listed in two policies")
                index[key] = policy

    def policy_for(self, host: str) -> SourcePolicy:
        """Return the policy for a host, or the one-tap-only default for unknown hosts."""
        normalized = host.strip().lower().rstrip(".")
        if normalized in self._exact:
            return self._exact[normalized]
        labels = normalized.split(".")
        for start in range(1, len(labels) - 1):
            suffix = ".".join(labels[start:])
            if suffix in self._wildcard:
                return self._wildcard[suffix]
        return DEFAULT_POLICY

    def is_allowed(self, host: str, mode: AccessMode) -> bool:
        """Return whether a host's policy allows an access mode."""
        return mode in self.policy_for(host).modes

    def hosts_with_mode(self, mode: AccessMode) -> frozenset[str]:
        """Return every host pattern whose policy allows a mode (e.g. extension manifest)."""
        return frozenset(
            pattern
            for policy in self._by_id.values()
            if mode in policy.modes
            for pattern in policy.hosts
        )

    def get(self, policy_id: str) -> SourcePolicy:
        """Return a policy by id; raises KeyError for unknown ids."""
        return self._by_id[policy_id]

    @property
    def policies(self) -> tuple[SourcePolicy, ...]:
        """All policies, in file order."""
        return tuple(self._by_id.values())


class _PolicyFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policies: list[SourcePolicy]


def load_source_policies(path: Path) -> SourcePolicyRegistry:
    """Load and validate `config/source_policies.yaml`."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SourcePolicyRegistry(_PolicyFile.model_validate(data).policies)
