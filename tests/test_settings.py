import pytest

from jobradar.core.settings import Settings


def test_settings_load_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Test JobRadar")
    monkeypatch.setenv("REDIS_PORT", "6380")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test JobRadar"
    assert settings.redis_port == 6380


def test_settings_ignore_local_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_PORT", raising=False)
    settings = Settings(_env_file=None)

    assert settings.redis_port == 6379
