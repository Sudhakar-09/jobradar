"""Decode an RFC 822 email (Gmail `format=raw`, `.eml` files) into an in-memory InboundMessage."""

from datetime import UTC, datetime
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parsedate_to_datetime

from jobradar.connectors.schemas import InboundMessage


def _part_text(message: EmailMessage, subtype: str) -> str | None:
    part = message.get_body(preferencelist=(subtype,))
    if part is None:
        return None
    content = part.get_content()
    return content if isinstance(content, str) else None


def _received_at(message: EmailMessage, fallback: datetime) -> datetime:
    header = message.get("Date")
    if not header:
        return fallback
    try:
        parsed = parsedate_to_datetime(str(header))
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_mime(
    raw: bytes, provider_message_id: str, *, received_fallback: datetime
) -> InboundMessage:
    """Return the sender, subject, date and HTML/text bodies of a raw email.

    Bodies stay in memory for parsing only; callers never store them.
    """
    message = message_from_bytes(raw, policy=policy.default)
    if not isinstance(message, EmailMessage):  # pragma: no cover - policy.default guarantees it
        raise TypeError("expected an EmailMessage")
    return InboundMessage(
        provider_message_id=provider_message_id,
        sender=str(message.get("From", "")),
        received_at=_received_at(message, received_fallback),
        subject=str(message.get("Subject", "")),
        html=_part_text(message, "html"),
        text=_part_text(message, "plain"),
    )
