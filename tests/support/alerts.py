"""Load alert-email fixtures as in-memory messages."""

from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime

from jobradar.connectors.mime import parse_mime
from jobradar.connectors.schemas import InboundMessage
from tests.support.fake_http import FIXTURES

ALERT_FIXTURES = ("linkedin", "naukrigulf", "bayt", "gulftalent", "naukri", "instahyre", "foundit")
FALLBACK = datetime(2026, 10, 30, tzinfo=UTC)


def load_message(name: str) -> InboundMessage:
    raw = (FIXTURES / "alerts" / f"{name}.eml").read_bytes()
    return parse_mime(raw, f"msg-{name}", received_fallback=FALLBACK)


async def stream(names: Iterable[str]) -> AsyncIterator[InboundMessage]:
    for name in names:
        yield load_message(name)
