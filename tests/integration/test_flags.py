"""Global flags and the market rollout gate (US-2.9 AC2) against the test database."""

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobradar import admin
from jobradar.admin import service
from jobradar.core.errors import GuardFailedError, ValidationFailedError
from jobradar.core.packs.conformance import CheckResult, PackReport

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


def rows(engine: Engine, sql: str) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(sql))]


async def test_a_market_failing_conformance_cannot_be_enabled(
    session_factory: async_sessionmaker[AsyncSession], admin_engine: Engine
) -> None:
    with pytest.raises(GuardFailedError, match="germany fails conformance") as error:
        await admin.set_global_flag(
            "market.germany.enabled", True, reason="try", factory=session_factory
        )

    assert error.value.guard == "conformance_failing"
    assert rows(admin_engine, "SELECT key FROM settings_flags") == []
    assert rows(admin_engine, "SELECT action FROM audit_log") == []


async def test_a_passing_market_is_enabled_and_audited(
    session_factory: async_sessionmaker[AsyncSession],
    admin_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    green = PackReport("market", "uae", [CheckResult("provenance", passed=True)])
    monkeypatch.setattr(service, "conformance_reports", lambda _clock=None: [green])

    await admin.set_global_flag(
        "market.uae.enabled", True, reason="UAE ready", factory=session_factory
    )
    await admin.set_global_flag(
        "market.uae.enabled", False, reason="pause", factory=session_factory
    )

    flags = await admin.list_global_flags(factory=session_factory)
    assert [(f.key, f.value) for f in flags] == [("market.uae.enabled", False)]
    audit = rows(admin_engine, "SELECT action, detail FROM audit_log ORDER BY created_at, id")
    assert [detail for _action, detail in audit] == [
        {"key": "market.uae.enabled", "old": None, "new": True, "reason": "UAE ready"},
        {"key": "market.uae.enabled", "old": True, "new": False, "reason": "pause"},
    ]


async def test_disabling_and_other_flags_are_not_gated(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await admin.set_global_flag(
        "market.germany.enabled", False, reason="off", factory=session_factory
    )
    await admin.set_global_flag(
        "apply.live_submit.enabled", False, reason="safe", factory=session_factory
    )

    assert len(await admin.list_global_flags(factory=session_factory)) == 2


@pytest.mark.parametrize(
    ("key", "reason", "message"),
    [
        ("Market.UAE", "x", "not a flag key"),
        ("market.uae.enabled", " ", "reason"),
        ("market.atlantis.enabled", "x", "no market pack named atlantis"),
    ],
)
async def test_invalid_changes_are_rejected(
    key: str, reason: str, message: str, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    with pytest.raises(ValidationFailedError, match=message):
        await admin.set_global_flag(key, True, reason=reason, factory=session_factory)
