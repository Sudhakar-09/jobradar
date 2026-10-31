import json
from pathlib import Path

import pytest

from jobradar import admin, cli
from jobradar.core.errors import GuardFailedError
from jobradar.core.packs.conformance import CheckResult, PackReport

REPORTS = [
    PackReport("market", "uae", [CheckResult("provenance", passed=True)]),
    PackReport(
        "market", "germany", [CheckResult("sources", passed=False, detail="xing: no parser")]
    ),
]


def test_packs_check_prints_failures_and_writes_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(admin, "conformance_reports", lambda: REPORTS)
    out = tmp_path / "conformance-results.json"

    assert cli.main(["packs", "check", "--json", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "uae              PASS" in printed
    assert "sources: xing: no parser" in printed
    written = json.loads(out.read_text(encoding="utf-8"))
    assert [(r["code"], r["passed"]) for r in written] == [("uae", True), ("germany", False)]


def test_flags_set_reports_the_gate(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def refuse(*_: object, **__: object) -> None:
        raise GuardFailedError("conformance_failing", "market germany fails conformance")

    monkeypatch.setattr(admin, "set_global_flag", refuse)

    assert cli.main(["flags", "set", "market.germany.enabled", "true", "--reason", "x"]) == 2
    assert "fails conformance" in capsys.readouterr().out


def test_flags_set_and_list(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}

    async def setter(key: str, value: object, **kwargs: object) -> admin.FlagView:
        seen.update(key=key, value=value, **kwargs)
        return admin.FlagView(key, value, None)

    async def lister(**_: object) -> list[admin.FlagView]:
        return []

    monkeypatch.setattr(admin, "set_global_flag", setter)
    monkeypatch.setattr(admin, "list_global_flags", lister)

    assert cli.main(["flags", "set", "notify.digest.enabled", "false", "--reason", "quiet"]) == 0
    assert seen == {"key": "notify.digest.enabled", "value": False, "reason": "quiet"}
    assert cli.main(["flags", "set", "x.y", "not-json", "--reason", "r"]) == 2
    assert cli.main(["flags", "list"]) == 0
    assert "No global flags set." in capsys.readouterr().out
