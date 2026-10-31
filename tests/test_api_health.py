from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from jobradar.api import app as api

client = TestClient(api.app)


def test_health_is_liveness_only(monkeypatch: pytest.MonkeyPatch) -> None:
    check_database = Mock()
    check_queue = Mock()
    check_redis = Mock()
    monkeypatch.setattr(api, "check_database", check_database)
    monkeypatch.setattr(api, "check_queue", check_queue)
    monkeypatch.setattr(api, "check_redis", check_redis)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    check_database.assert_not_called()
    check_queue.assert_not_called()
    check_redis.assert_not_called()


def test_ready_reports_ready_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "check_database", lambda: None)
    monkeypatch.setattr(api, "check_queue", lambda: None)
    monkeypatch.setattr(api, "check_redis", lambda: None)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "ok", "queue": "ok"},
    }


def test_ready_reports_unavailable_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    def database_unavailable() -> None:
        raise ConnectionError("database is unavailable")

    monkeypatch.setattr(api, "check_database", database_unavailable)
    monkeypatch.setattr(api, "check_queue", lambda: None)
    monkeypatch.setattr(api, "check_redis", lambda: None)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"database": "unavailable", "redis": "ok", "queue": "ok"},
    }


def test_health_returns_correlation_id() -> None:
    correlation_id = "1a8bb5cc-841d-4c54-a014-6be83f821f33"

    response = client.get("/health", headers={"X-Correlation-ID": correlation_id})

    assert response.headers["X-Correlation-ID"] == correlation_id
