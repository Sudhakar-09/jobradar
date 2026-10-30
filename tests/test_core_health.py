from unittest.mock import MagicMock, Mock

import pytest

from jobradar.core import health


def test_check_database_executes_select(monkeypatch: pytest.MonkeyPatch) -> None:
    connection_context = MagicMock()
    connection = connection_context.__enter__.return_value
    engine = Mock()
    engine.connect.return_value = connection_context
    monkeypatch.setattr(health, "get_engine", lambda: engine)

    health.check_database()

    assert str(connection.execute.call_args.args[0]) == "SELECT 1"


def test_check_redis_sends_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_socket = Mock()
    redis_socket.__enter__ = Mock(return_value=redis_socket)
    redis_socket.__exit__ = Mock(return_value=None)
    redis_socket.recv.return_value = b"+PONG\r\n"
    create_connection = Mock(return_value=redis_socket)
    monkeypatch.setattr(health.socket, "create_connection", create_connection)

    health.check_redis()

    assert create_connection.call_args.args[0] == ("localhost", 6379)
    assert redis_socket.sendall.call_args.args[0] == b"*1\r\n$4\r\nPING\r\n"


def test_check_redis_rejects_unexpected_response(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_socket = Mock()
    redis_socket.__enter__ = Mock(return_value=redis_socket)
    redis_socket.__exit__ = Mock(return_value=None)
    redis_socket.recv.return_value = b"-ERR unavailable\r\n"
    monkeypatch.setattr(health.socket, "create_connection", Mock(return_value=redis_socket))

    with pytest.raises(ConnectionError, match="unexpected health-check response"):
        health.check_redis()


def test_check_queue_connects_to_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = MagicMock()
    monkeypatch.setattr(health.celery_app, "connection_for_read", Mock(return_value=connection))

    health.check_queue()

    connection.__enter__().ensure_connection.assert_called_once_with(max_retries=0)