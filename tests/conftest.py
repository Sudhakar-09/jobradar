import pytest

from jobradar.core.settings import Settings

# Prevent application modules imported during collection from reading the local .env.
Settings.model_config["env_file"] = None


@pytest.fixture(autouse=True)
def _keep_test_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop CLI tests from reconfiguring global logging.

    `cli.main()` configures structlog with cached loggers; doing that inside a test would make
    later `structlog.testing.capture_logs()` calls miss events from already-cached loggers.
    """
    monkeypatch.setattr("jobradar.cli.configure_logging", lambda _level: None)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Rewrite tests/golden/**/*.expected.json from the current output (review the diff).",
    )
