"""Gmail as an alert inbox (read-only; ADR-0008).

Only messages from configured alert senders in the last few days are listed; each is fetched in
raw form, decoded in memory and handed to the parsers. Calls go through `PoliteClient` (source
policy `gmail_api`, timeouts, retries, no URLs or tokens in logs). A rejected refresh token raises
`GmailAuthError` so the inbox can be marked for reconnection.
"""

import base64
import json
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from jobradar.connectors.mime import parse_mime
from jobradar.connectors.schemas import InboundMessage
from jobradar.core.errors import ExternalServiceError
from jobradar.core.http import PoliteClient
from jobradar.core.source_policies import AccessMode

AUTH_REJECTED_STATUS: Final = frozenset({400, 401})
MILLISECONDS_PER_SECOND: Final = 1000


class GmailAuthError(ExternalServiceError):
    """Google rejected the stored grant (revoked, expired or wrong client): reconnect needed."""

    def __init__(self, message: str = "Gmail access was revoked or expired") -> None:
        """Create a non-retryable authorisation error."""
        super().__init__("gmail", message, retryable=False)


class GmailSettings(BaseModel):
    """`config/inboxes.yaml` → gmail."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: str
    token_url: str
    revoke_url: str
    messages_url: str
    message_url: str
    lookback_days: int = Field(ge=1, le=30)
    max_messages: int = Field(ge=1, le=1000)
    page_size: int = Field(ge=1, le=500)


class InboxesFile(BaseModel):
    """`config/inboxes.yaml`."""

    model_config = ConfigDict(extra="forbid")

    gmail: GmailSettings


def load_inboxes_file(path: Path) -> InboxesFile:
    """Load and validate the inbox endpoint configuration."""
    return InboxesFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


class OAuthClient(BaseModel):
    """The installed-app OAuth client from Google Cloud (client JSON, `installed` section)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)


def load_oauth_client(path: Path) -> OAuthClient:
    """Read the client id and secret from the JSON file downloaded from Google Cloud."""
    data = json.loads(path.read_text(encoding="utf-8"))
    section = data.get("installed") if isinstance(data, dict) else None
    if not isinstance(section, dict):
        raise ValueError("the OAuth client file must be a Desktop app client ('installed')")  # noqa: TRY004 -- bad file content
    return OAuthClient.model_validate(section)


class _Token(BaseModel):
    model_config = ConfigDict(extra="ignore")
    access_token: str


class _MessageRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str


class _MessageList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    messages: list[_MessageRef] = []
    nextPageToken: str | None = None  # noqa: N815 -- API field name


class _RawMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    raw: str
    internalDate: str | None = None  # noqa: N815 -- epoch milliseconds as text


def gmail_query(senders: Sequence[str], lookback_days: int) -> str:
    """Gmail search limited to the alert senders and recent days (never the whole mailbox)."""
    return f"from:({' OR '.join(sorted(senders))}) newer_than:{lookback_days}d"


def _decode_raw(message: _RawMessage) -> InboundMessage:
    padded = message.raw + "=" * (-len(message.raw) % 4)
    raw = base64.urlsafe_b64decode(padded)
    fallback = datetime.now(UTC)
    if message.internalDate and message.internalDate.isdigit():
        fallback = datetime.fromtimestamp(
            int(message.internalDate) / MILLISECONDS_PER_SECOND, tz=UTC
        )
    return parse_mime(raw, message.id, received_fallback=fallback)


class GmailAlertInbox:
    """Lists and fetches recent alert emails for one user's Gmail connection."""

    def __init__(
        self,
        http: PoliteClient,
        settings: GmailSettings,
        client: OAuthClient,
        refresh_token: str,
        senders: Sequence[str],
    ) -> None:
        """Bind the client to one user's grant and the alert sender allowlist."""
        self._http = http
        self._settings = settings
        self._client = client
        self._refresh_token = refresh_token
        self._senders = list(senders)

    async def access_token(self) -> str:
        """Exchange the stored refresh token for a short-lived access token."""
        try:
            response = await self._http.post_form(
                self._settings.token_url,
                mode=AccessMode.API,
                data={
                    "client_id": self._client.client_id,
                    "client_secret": self._client.client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        except ExternalServiceError as exc:
            if exc.status_code in AUTH_REJECTED_STATUS:
                raise GmailAuthError from exc
            raise
        try:
            return _Token.model_validate_json(response.content).access_token
        except ValidationError as exc:
            raise GmailAuthError("token response had no access token") from exc

    async def _get(self, url: str, token: str, params: dict[str, str | int]) -> object:
        try:
            return await self._http.get_json(
                url,
                mode=AccessMode.API,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        except ExternalServiceError as exc:
            if exc.status_code == 401:  # noqa: PLR2004 -- HTTP Unauthorized
                raise GmailAuthError from exc
            raise

    async def _message_ids(self, token: str) -> list[str]:
        ids: list[str] = []
        page_token: str | None = None
        query = gmail_query(self._senders, self._settings.lookback_days)
        while len(ids) < self._settings.max_messages:
            params: dict[str, str | int] = {"q": query, "maxResults": self._settings.page_size}
            if page_token:
                params["pageToken"] = page_token
            page = _MessageList.model_validate(
                await self._get(self._settings.messages_url, token, params)
            )
            ids.extend(ref.id for ref in page.messages)
            page_token = page.nextPageToken
            if not page_token:
                break
        return ids[: self._settings.max_messages]

    async def fetch_new(self) -> AsyncIterator[InboundMessage]:
        """Yield recent alert emails, decoded in memory (nothing is written to disk)."""
        token = await self.access_token()
        for message_id in await self._message_ids(token):
            yield await self._fetch(message_id, token)

    async def fetch_ids(self, message_ids: Sequence[str]) -> AsyncIterator[InboundMessage]:
        """Yield the given emails again (e.g. to re-parse after a parser fix), in memory only."""
        token = await self.access_token()
        for message_id in message_ids:
            yield await self._fetch(message_id, token)

    async def _fetch(self, message_id: str, token: str) -> InboundMessage:
        body = await self._get(
            self._settings.message_url.format(id=message_id), token, {"format": "raw"}
        )
        return _decode_raw(_RawMessage.model_validate(body))

    async def revoke(self) -> None:
        """Ask Google to revoke the grant (used when the user disconnects)."""
        await self._http.post_form(
            self._settings.revoke_url, mode=AccessMode.API, data={"token": self._refresh_token}
        )
