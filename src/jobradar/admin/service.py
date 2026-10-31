"""Feature flags with the market/role rollout gate (US-2.9 AC2, docs/lld/admin.md).

Turning on ``market.<code>.enabled`` or ``role.<code>.enabled`` requires the pack to pass the
conformance suite at that moment; the result is checked live (Stage 1 operator CLI). Every change
is audited with its reason. Turning a flag off is never gated.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar.admin.repository import FlagRepository
from jobradar.core.clock import Clock, SystemClock
from jobradar.core.db import operator_session
from jobradar.core.errors import GuardFailedError, ValidationFailedError
from jobradar.core.packs.conformance import ConformanceInputs, PackReport, run_conformance
from jobradar.core.settings import get_settings

ROLLOUT_FLAG: Final = re.compile(r"^(?P<kind>market|role)\.(?P<code>[a-z0-9_]+)\.enabled$")
FLAG_KEY: Final = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
logger = structlog.get_logger(__name__)
Factory = async_sessionmaker[AsyncSession] | None


@dataclass(frozen=True, slots=True)
class FlagView:
    """A global flag as shown to the operator."""

    key: str
    value: object
    updated_at: datetime | None


def conformance_inputs(clock: Clock | None = None) -> ConformanceInputs:
    """Where the live conformance check reads from (settings), as of today."""
    settings = get_settings()
    return ConformanceInputs(
        packs_dir=settings.packs_dir,
        config_dir=settings.config_dir,
        golden_dir=settings.golden_dir,
        today=(clock or SystemClock()).now().date(),
    )


def conformance_reports(clock: Clock | None = None) -> list[PackReport]:
    """The conformance report of every pack, as of today."""
    return run_conformance(conformance_inputs(clock))


def _gate(key: str, value: object, clock: Clock | None) -> None:
    match = ROLLOUT_FLAG.match(key)
    if match is None or value is not True:
        return
    kind, code = match["kind"], match["code"]
    report = next(
        (r for r in conformance_reports(clock) if r.kind == kind and r.code == code), None
    )
    if report is None:
        raise ValidationFailedError(f"no {kind} pack named {code}")
    if not report.passed:
        failing = "; ".join(f"{c.check}: {c.detail}" for c in report.failures())
        raise GuardFailedError("conformance_failing", f"{kind} {code} fails conformance: {failing}")


async def set_global_flag(
    key: str,
    value: object,
    *,
    reason: str,
    actor: UUID | None = None,
    clock: Clock | None = None,
    factory: Factory = None,
) -> FlagView:
    """Set a global flag; market/role enable flags must pass the rollout gate.

    Raises:
        ValidationFailedError: malformed key, missing reason, or unknown pack.
        GuardFailedError: ``conformance_failing`` when the pack does not pass conformance.
    """
    if not FLAG_KEY.match(key):
        raise ValidationFailedError(f"not a flag key: {key}")
    if not reason.strip():
        raise ValidationFailedError("give a reason for the change")
    _gate(key, value, clock)
    async with operator_session(factory=factory) as session:
        flags = FlagRepository(session)
        previous = await flags.get_global(key)
        old = previous.value if previous is not None else None
        flag = await flags.set_global(key, value, actor)
        await flags.audit(
            "flag.changed", actor, {"key": key, "old": old, "new": value, "reason": reason}
        )
        view = FlagView(flag.key, flag.value, None)
    logger.info("admin.flag_changed", key=key)
    return view


async def list_global_flags(*, factory: Factory = None) -> list[FlagView]:
    """Every global flag."""
    async with operator_session(factory=factory) as session:
        rows = await FlagRepository(session).all_global()
        return [FlagView(row.key, row.value, row.updated_at) for row in rows]
