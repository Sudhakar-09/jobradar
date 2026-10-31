"""Schemas and loaders for market, role and persona packs."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Final

import structlog
import yaml
from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
MARKET_PACK_STALE_AFTER: Final = timedelta(days=90)  # CLAUDE.md §8
logger = structlog.get_logger(__name__)


class VisaRoute(BaseModel):
    """A work-authorization route described in a market pack."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: NonEmptyString
    summary: NonEmptyString
    sponsor_required: bool


class MarketPack(BaseModel):
    """Country or region configuration: money, CV norms, visa routes and sources."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: NonEmptyString
    name: NonEmptyString
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    job_boards: list[NonEmptyString]
    cv_format: NonEmptyString
    photo_on_cv: bool
    salary_convention: NonEmptyString
    visa_routes: list[VisaRoute]
    sponsor_register_source: NonEmptyString | None = None
    notice_period_norm: NonEmptyString
    language_notes: NonEmptyString
    last_verified: date | None


class RolePack(BaseModel):
    """Role configuration: title aliases, skills, signal documents and assessments."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: NonEmptyString
    title_aliases: list[NonEmptyString]
    core_skills: list[NonEmptyString]
    signal_documents: list[NonEmptyString]
    assessment_types: list[NonEmptyString]
    resume_emphasis: list[NonEmptyString]


class PersonaPack(BaseModel):
    """Persona configuration: channel weights, volume and resume strategy."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: NonEmptyString
    description: NonEmptyString
    channel_weights: dict[NonEmptyString, float]
    daily_volume_range: tuple[int, int]
    resume_strategy: NonEmptyString
    tips: list[NonEmptyString]


def _load_pack[PackT: BaseModel](path: Path, model: type[PackT]) -> PackT:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")  # noqa: TRY004 -- bad file content, not a caller type error
    pack = model.model_validate(data)
    if isinstance(pack, MarketPack):
        _warn_if_market_pack_is_stale(pack)
    return pack


def _warn_if_market_pack_is_stale(pack: MarketPack) -> None:
    if pack.last_verified is None:
        logger.warning("packs.market_verification_missing", market=pack.code)
    elif pack.last_verified < datetime.now(UTC).date() - MARKET_PACK_STALE_AFTER:
        logger.warning(
            "packs.market_verification_stale",
            market=pack.code,
            last_verified=pack.last_verified.isoformat(),
        )


def load_market_pack(path: Path) -> MarketPack:
    """Load and validate one market pack."""
    return _load_pack(path, MarketPack)


def load_role_pack(path: Path) -> RolePack:
    """Load and validate one role pack."""
    return _load_pack(path, RolePack)


def load_persona_pack(path: Path) -> PersonaPack:
    """Load and validate one persona pack."""
    return _load_pack(path, PersonaPack)


def load_market_packs(directory: Path) -> list[MarketPack]:
    """Load every market pack in a directory, sorted by file name."""
    return [load_market_pack(path) for path in sorted(directory.glob("*.yaml"))]


def load_role_packs(directory: Path) -> list[RolePack]:
    """Load every role pack in a directory, sorted by file name."""
    return [load_role_pack(path) for path in sorted(directory.glob("*.yaml"))]


def load_persona_packs(directory: Path) -> list[PersonaPack]:
    """Load every persona pack in a directory, sorted by file name."""
    return [load_persona_pack(path) for path in sorted(directory.glob("*.yaml"))]
