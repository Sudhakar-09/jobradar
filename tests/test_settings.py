from jobradar.core.settings import Settings


def test_settings_load_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "Test JobRadar")
    monkeypatch.setenv("REDIS_PORT", "6380")

    settings = Settings()

    assert settings.app_name == "Test JobRadar"
    assert settings.redis_port == 6380