"""Load packs from YAML, warn on stale facts, and cross-check packs with source policies."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import structlog
import yaml
from pydantic import BaseModel

from jobradar.core.packs.common import Provenance
from jobradar.core.packs.market import MarketPack
from jobradar.core.packs.persona import PersonaPack
from jobradar.core.packs.role import RolePack
from jobradar.core.source_policies import SourcePolicyRegistry

PACK_STALE_AFTER: Final = timedelta(days=90)  # CLAUDE.md §8
logger = structlog.get_logger(__name__)


def _load_pack[PackT: BaseModel](path: Path, model: type[PackT]) -> PackT:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")  # noqa: TRY004 -- bad file content, not a caller type error
    return model.model_validate(data)


def _warn_if_stale(kind: str, code: str, provenance: Provenance) -> None:
    if provenance.last_verified is None:
        logger.warning("packs.verification_missing", pack_kind=kind, pack=code)
    elif provenance.last_verified < datetime.now(UTC).date() - PACK_STALE_AFTER:
        logger.warning(
            "packs.verification_stale",
            pack_kind=kind,
            pack=code,
            last_verified=provenance.last_verified.isoformat(),
        )


def load_market_pack(path: Path) -> MarketPack:
    """Load and validate one market pack, warning if its facts are unverified or stale."""
    pack = _load_pack(path, MarketPack)
    _warn_if_stale("market", pack.code, pack.provenance)
    return pack


def load_role_pack(path: Path) -> RolePack:
    """Load and validate one role pack, warning if its facts are unverified or stale."""
    pack = _load_pack(path, RolePack)
    _warn_if_stale("role", pack.code, pack.provenance)
    return pack


def load_persona_pack(path: Path) -> PersonaPack:
    """Load and validate one persona pack."""
    return _load_pack(path, PersonaPack)


def _check_unique_codes(kind: str, codes: list[str]) -> None:
    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    if duplicates:
        raise ValueError(f"duplicate {kind} pack codes: {duplicates}")


def load_market_packs(directory: Path) -> list[MarketPack]:
    """Load every market pack in a directory, sorted by file name; codes must be unique."""
    packs = [load_market_pack(path) for path in sorted(directory.glob("*.yaml"))]
    _check_unique_codes("market", [pack.code for pack in packs])
    return packs


def load_role_packs(directory: Path) -> list[RolePack]:
    """Load every role pack in a directory, sorted by file name; codes must be unique."""
    packs = [load_role_pack(path) for path in sorted(directory.glob("*.yaml"))]
    _check_unique_codes("role", [pack.code for pack in packs])
    return packs


def load_persona_packs(directory: Path) -> list[PersonaPack]:
    """Load every persona pack in a directory, sorted by file name; codes must be unique."""
    packs = [load_persona_pack(path) for path in sorted(directory.glob("*.yaml"))]
    _check_unique_codes("persona", [pack.code for pack in packs])
    return packs


def source_policy_problems(market: MarketPack, registry: SourcePolicyRegistry) -> list[str]:
    """Return every market source whose access modes its hosts' policies do not allow.

    A market may only claim modes that the source policy registry grants for each of the
    source's hosts (ADR-0022). An empty list means the pack is consistent.
    """
    problems: list[str] = []
    for source in market.sources:
        for host in source.hosts:
            allowed = registry.policy_for(host.removeprefix("*.")).modes
            extra = sorted(mode.value for mode in source.access_modes - allowed)
            if extra:
                problems.append(f"{market.code}/{source.code}: {host} does not allow {extra}")
    return problems
