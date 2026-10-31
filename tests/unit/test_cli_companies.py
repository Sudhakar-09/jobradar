from pathlib import Path
from uuid import UUID

import pytest
import yaml

from jobradar import accounts, cli, connectors

OWNER = accounts.OwnerAccount(user_id=UUID(int=9))
SUGGESTION_ID = UUID(int=7)
VERIFIED = connectors.CompanyCheck("Demo Air", "ashby", "demoair", "verified", 3, 2)
NO_POSTINGS = connectors.CompanyCheck("Sample Pay", "lever", "samplepay", "no_postings", 4, 0)


async def an_owner(**_: object) -> accounts.OwnerAccount:
    return OWNER


def test_verify_a_file_prints_each_board(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    candidates = tmp_path / "candidates.yaml"
    candidates.write_text(
        "companies:\n  - {name: Demo Air, ats: ashby, ats_slug: demoair, countries: [AE], "
        "source: test}\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    async def verify_entries(entries: list[object], **kwargs: object) -> list[object]:
        seen.update(entries=entries, **kwargs)
        return [VERIFIED]

    monkeypatch.setattr(connectors, "verify_entries", verify_entries)

    assert cli.main(["companies", "verify", "--file", str(candidates), "--country", "ae"]) == 0
    output = capsys.readouterr().out
    assert "ashby/demoair" in output
    assert "1 of 1 boards checked list jobs" in output
    assert seen["countries"] == frozenset({"AE"})


def test_verify_the_catalogue_passes_force(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}

    async def verify_companies(**kwargs: object) -> list[object]:
        seen.update(kwargs)
        return [NO_POSTINGS, connectors.CompanyCheck("Demo Air", "ashby", "demoair", "cached")]

    monkeypatch.setattr(connectors, "verify_companies", verify_companies)

    assert cli.main(["companies", "verify", "--force"]) == 0
    assert seen == {"countries": None, "force": True}
    output = capsys.readouterr().out
    assert "no_postings" in output
    assert "0 of 1 boards checked" in output
    assert "1 boards were checked in the last 24 hours" in output


def test_probe_writes_only_verified_boards_for_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    names = tmp_path / "names.txt"
    names.write_text("# comment\nDemo Air\n\nSample Pay\nDemo Air\n", encoding="utf-8")
    out = tmp_path / "probe.yaml"
    asked: list[str] = []

    async def probe_companies(names: list[str], **_: object) -> dict[str, object]:
        asked.extend(names)
        return {"Demo Air": VERIFIED, "Sample Pay": NO_POSTINGS, "Nobody": None}

    monkeypatch.setattr(connectors, "probe_companies", probe_companies)

    args = ["companies", "probe", "Nobody", "--names-file", str(names), "--write", str(out)]
    assert cli.main(args) == 0
    assert asked == ["Nobody", "Demo Air", "Sample Pay"]
    output = capsys.readouterr().out
    assert "No board found for: Nobody" in output
    written = yaml.safe_load(out.read_text(encoding="utf-8"))["companies"]
    assert [(c["name"], c["ats"], c["ats_slug"], c["countries"]) for c in written] == [
        ("Demo Air", "ashby", "demoair", ["AE"])
    ]
    assert written[0]["source"].endswith(": 2 postings in AE")


def test_probe_needs_names(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["companies", "probe"]) == 2
    assert "company names" in capsys.readouterr().out


def test_suggestions_list_probe_accept_and_reject(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accounts, "find_owner", an_owner)
    info = connectors.SuggestionInfo(
        SUGGESTION_ID, "Demo Air", "www.linkedin.com", "ashby", "demoair", 3, "pending"
    )
    decisions: list[dict[str, object]] = []

    async def listing(*_: object, **__: object) -> list[object]:
        return [info]

    async def decide(*_: object, **kwargs: object) -> object:
        decisions.append(kwargs)
        if not kwargs["accept"]:
            return None
        return connectors.CompanyRef(UUID(int=1), "Demo Air", "ashby", "demoair")

    monkeypatch.setattr(connectors, "list_company_suggestions", listing)
    monkeypatch.setattr(connectors, "probe_company_suggestions", listing)
    monkeypatch.setattr(connectors, "decide_company_suggestion", decide)

    assert cli.main(["companies", "suggestions", "list", "--status", "all"]) == 0
    assert "seen   3x  pending" in capsys.readouterr().out
    assert cli.main(["companies", "suggestions", "probe"]) == 0
    assert "Boards found for 1 suggestions" in capsys.readouterr().out
    accept = ["companies", "suggestions", "accept", str(SUGGESTION_ID), "--country", "AE"]
    assert cli.main([*accept, "--ats", "lever", "--slug", "demo-air"]) == 0
    assert "Added to the catalogue: Demo Air" in capsys.readouterr().out
    assert cli.main(["companies", "suggestions", "reject", str(SUGGESTION_ID)]) == 0
    assert "rejected" in capsys.readouterr().out
    assert decisions[0]["board"] == ("lever", "demo-air")
    assert decisions[0]["countries"] == ["AE"]
    assert decisions[1] == {"accept": False, "countries": (), "board": None}


def test_suggestions_list_when_empty(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accounts, "find_owner", an_owner)

    async def none(*_: object, **__: object) -> list[object]:
        return []

    monkeypatch.setattr(connectors, "list_company_suggestions", none)

    assert cli.main(["companies", "suggestions", "list"]) == 0
    assert "No company suggestions." in capsys.readouterr().out
