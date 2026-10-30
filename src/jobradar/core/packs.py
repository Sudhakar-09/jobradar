from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

import structlog
import yaml
from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
logger = structlog.get_logger(__name__)


class VisaRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: NonEmptyString
    summary: NonEmptyString
    sponsor_required: bool


class MarketPack(BaseModel):
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
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: NonEmptyString
    title_aliases: list[NonEmptyString]
    core_skills: list[NonEmptyString]
    signal_documents: list[NonEmptyString]
    assessment_types: list[NonEmptyString]
    resume_emphasis: list[NonEmptyString]


class PersonaPack(BaseModel):
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
        raise ValueError(f"{path} must contain a YAML mapping")
    pack = model.model_validate(data)
    if isinstance(pack, MarketPack):
        _warn_if_market_pack_is_stale(pack)
    return pack


def _warn_if_market_pack_is_stale(pack: MarketPack) -> None:
    if pack.last_verified is None:
        logger.warning("market_pack_verification_date_missing", market=pack.code)
    elif pack.last_verified < date.today() - timedelta(days=90):
        logger.warning(
            "market_pack_verification_stale",
            market=pack.code,
            last_verified=pack.last_verified.isoformat(),
        )


def load_market_pack(path: Path) -> MarketPack:
    return _load_pack(path, MarketPack)


def load_role_pack(path: Path) -> RolePack:
    return _load_pack(path, RolePack)


def load_persona_pack(path: Path) -> PersonaPack:
    return _load_pack(path, PersonaPack)


def load_market_packs(directory: Path) -> list[MarketPack]:
    return [load_market_pack(path) for path in sorted(directory.glob("*.yaml"))]


def load_role_packs(directory: Path) -> list[RolePack]:
    return [load_role_pack(path) for path in sorted(directory.glob("*.yaml"))]


def load_persona_packs(directory: Path) -> list[PersonaPack]:
    return [load_persona_pack(path) for path in sorted(directory.glob("*.yaml"))]
