from collections.abc import Coroutine
from typing import Any
from uuid import UUID

import pytest

from jobradar import cli
from jobradar.connectors import SourceRunResult
from jobradar.connectors.repository import SyncCounts


def result(status: str, found: int = 3, new: int = 2) -> SourceRunResult:
    return SourceRunResult(
        run_id=UUID(int=1),
        connector="greenhouse",
        company_id=UUID(int=2),
        company_name="Example Logistics",
        status=status,  # type: ignore[arg-type]
        jobs_found=found,
        jobs_new=new,
        jobs_updated=0,
        items_invalid=0,
        http_status_counts={"200": 1},
    )


def fake_run(value: object) -> Any:
    def run(coroutine: Coroutine[Any, Any, Any]) -> object:
        coroutine.close()
        return value

    return run


def test_discover_prints_runs_and_succeeds(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "run", fake_run([result("ok"), result("failed", 0, 0)]))

    assert cli.main(["discover"]) == 0
    output = capsys.readouterr().out
    assert "Example Logistics" in output
    assert "Total: 3 jobs found, 2 new, across 2 runs." in output


def test_discover_fails_only_when_every_run_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "run", fake_run([result("failed", 0, 0), result("failed", 0, 0)]))

    assert cli.main(["discover", "--source", "greenhouse"]) == 1


def test_discover_without_companies_explains_what_to_do(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "run", fake_run([]))

    assert cli.main(["discover"]) == 0
    assert "jobradar companies sync" in capsys.readouterr().out


def test_companies_sync_reports_counts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "run", fake_run(SyncCounts(created=4, updated=1)))

    assert cli.main(["companies", "sync"]) == 0
    assert "4 new, 1 updated" in capsys.readouterr().out
