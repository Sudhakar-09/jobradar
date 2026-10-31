import json
from pathlib import Path

import httpx
import pytest
import structlog

from jobradar.connectors.gmail import (
    GmailAlertInbox,
    GmailAuthError,
    OAuthClient,
    gmail_query,
    load_inboxes_file,
    load_oauth_client,
)
from jobradar.core.errors import ExternalServiceError
from jobradar.core.source_policies import AccessMode
from tests.support.fake_gmail import FakeGoogle
from tests.support.fake_http import ROOT, polite_client

pytestmark = pytest.mark.anyio
GMAIL = load_inboxes_file(ROOT / "config" / "inboxes.yaml").gmail
CLIENT = OAuthClient(client_id="client-1", client_secret="secret-1")
SENDERS = ["jobalerts-noreply@linkedin.com", "alerts@bayt.com"]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def inbox(fake: FakeGoogle, http: object) -> GmailAlertInbox:
    return GmailAlertInbox(http, GMAIL, CLIENT, "refresh-xyz", SENDERS)  # type: ignore[arg-type]


def test_query_is_limited_to_alert_senders_and_recent_days() -> None:
    assert gmail_query(SENDERS, 3) == (
        "from:(alerts@bayt.com OR jobalerts-noreply@linkedin.com) newer_than:3d"
    )


async def test_fetch_new_refreshes_token_lists_and_decodes_messages() -> None:
    fake = FakeGoogle(["linkedin", "bayt", "naukri"], page_size=2)

    async with polite_client(fake) as http:
        messages = [m async for m in inbox(fake, http).fetch_new()]

    assert [m.provider_message_id for m in messages] == ["gm-linkedin", "gm-bayt", "gm-naukri"]
    assert messages[0].html is not None
    assert "Senior Java Backend Engineer" in messages[0].html
    token_call = fake.requests[0]
    assert token_call.method == "POST"
    form = dict(pair.split("=") for pair in token_call.content.decode().split("&"))
    assert form["grant_type"] == "refresh_token"
    assert form["refresh_token"] == "refresh-xyz"
    list_calls = [r for r in fake.requests if r.url.path.endswith("/messages")]
    assert len(list_calls) == 2  # two pages
    assert list_calls[0].url.params["q"].startswith("from:(")
    assert all(
        r.url.params.get("format") == "raw" for r in fake.requests[3:] if "/messages/" in r.url.path
    )


async def test_max_messages_caps_a_run() -> None:
    fake = FakeGoogle(["linkedin", "bayt", "naukri", "foundit"], page_size=2)
    capped = GMAIL.model_copy(update={"max_messages": 2})

    async with polite_client(fake) as http:
        gmail = GmailAlertInbox(http, capped, CLIENT, "refresh-xyz", SENDERS)
        messages = [m async for m in gmail.fetch_new()]

    assert len(messages) == 2


async def test_rejected_refresh_token_is_an_auth_error() -> None:
    fake = FakeGoogle(["linkedin"], token_status=400)

    async with polite_client(fake) as http:
        with pytest.raises(GmailAuthError):
            await inbox(fake, http).access_token()


async def test_unauthorised_api_call_is_an_auth_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "stale"})
        return httpx.Response(401)

    async with polite_client(handler) as http:
        gmail = GmailAlertInbox(http, GMAIL, CLIENT, "refresh-xyz", SENDERS)
        with pytest.raises(GmailAuthError):
            [m async for m in gmail.fetch_new()]


async def test_revoke_posts_the_refresh_token() -> None:
    fake = FakeGoogle([])

    async with polite_client(fake) as http:
        await inbox(fake, http).revoke()

    assert fake.revoked == ["refresh-xyz"]


async def test_post_form_never_logs_the_form_and_does_not_follow_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "https://oauth2.googleapis.com/x"})

    with structlog.testing.capture_logs() as logs:
        async with polite_client(handler) as http:
            with pytest.raises(ExternalServiceError, match="redirect on POST"):
                await http.post_form(
                    GMAIL.token_url, mode=AccessMode.API, data={"refresh_token": "very-secret"}
                )

    assert "very-secret" not in str(logs)


def test_oauth_client_file_must_be_a_desktop_client(tmp_path: Path) -> None:
    good = tmp_path / "client.json"
    good.write_text(json.dumps({"installed": {"client_id": "a", "client_secret": "b"}}))
    web = tmp_path / "web.json"
    web.write_text(json.dumps({"web": {"client_id": "a", "client_secret": "b"}}))

    assert load_oauth_client(good) == OAuthClient(client_id="a", client_secret="b")
    with pytest.raises(ValueError, match="Desktop app"):
        load_oauth_client(web)
