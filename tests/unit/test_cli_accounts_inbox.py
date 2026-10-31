import json
from pathlib import Path
from uuid import UUID

import pytest

from jobradar import accounts, cli, connectors, privacy
from jobradar.core.crypto import generate_key
from jobradar.core.settings import get_settings

OWNER = accounts.OwnerAccount(user_id=UUID(int=9))


async def no_owner(**_: object) -> None:
    return None


async def an_owner(**_: object) -> accounts.OwnerAccount:
    return OWNER


@pytest.fixture
def configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = tmp_path / "client.json"
    client.write_text(json.dumps({"installed": {"client_id": "c", "client_secret": "s"}}))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_FILE", str(client))
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", generate_key())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_keys_generate_prints_an_env_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["keys", "generate"]) == 0
    assert "TOKEN_ENCRYPTION_KEY=" in capsys.readouterr().out


def test_inbox_connect_needs_an_owner(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accounts, "find_owner", no_owner)

    assert cli.main(["inbox", "connect", "gmail"]) == 2
    assert "bootstrap-owner" in capsys.readouterr().out


def test_inbox_connect_needs_the_client_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accounts, "find_owner", an_owner)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_FILE", raising=False)
    get_settings.cache_clear()

    assert cli.main(["inbox", "connect", "gmail"]) == 2
    assert "GOOGLE_OAUTH_CLIENT_FILE" in capsys.readouterr().out


def test_declining_consent_changes_nothing(
    configured: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accounts, "find_owner", an_owner)
    monkeypatch.setattr("builtins.input", lambda _prompt: "no")

    async def must_not_be_called(*_: object, **__: object) -> None:
        raise AssertionError("consent must not be recorded")

    monkeypatch.setattr(privacy, "grant_consent", must_not_be_called)

    assert cli.main(["inbox", "connect", "gmail"]) == 1
    output = capsys.readouterr().out
    assert "read-only access" in output  # the consent text was shown
    assert "Not connected." in output


def test_discover_reports_missing_owner_for_alerts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accounts, "find_owner", no_owner)

    assert cli.main(["discover", "--source", "alerts"]) == 0
    assert "Skipped alerts: no owner account yet" in capsys.readouterr().out


def test_alerts_ingest_without_inbox_explains_next_step(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accounts, "find_owner", an_owner)

    async def none(*_: object, **__: object) -> list[connectors.SourceRunResult]:
        return []

    monkeypatch.setattr(connectors, "ingest_alerts", none)

    assert cli.main(["alerts", "ingest"]) == 0
    assert "jobradar inbox connect gmail" in capsys.readouterr().out
