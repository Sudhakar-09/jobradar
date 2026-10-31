"""A fake Google OAuth + Gmail API serving alert-email fixtures."""

import base64
from collections.abc import Iterable
from urllib.parse import parse_qs

import httpx

from tests.support.fake_http import FIXTURES


def raw_message(name: str) -> str:
    data = (FIXTURES / "alerts" / f"{name}.eml").read_bytes()
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


class FakeGoogle:
    """Records requests; serves a token, a message list and raw messages."""

    def __init__(
        self, names: Iterable[str], *, token_status: int = 200, page_size: int = 100
    ) -> None:
        self.names = list(names)
        self.token_status = token_status
        self.page_size = page_size
        self.requests: list[httpx.Request] = []
        self.revoked: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.url.host == "oauth2.googleapis.com":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            if path == "/revoke":
                self.revoked.append(form["token"])
                return httpx.Response(200)
            if self.token_status != 200:
                return httpx.Response(self.token_status, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "access-1", "expires_in": 3599})
        if request.headers.get("Authorization") != "Bearer access-1":
            return httpx.Response(401)
        if path.endswith("/messages"):
            start = int(request.url.params.get("pageToken", "0"))
            chunk = self.names[start : start + self.page_size]
            body: dict[str, object] = {"messages": [{"id": f"gm-{n}"} for n in chunk]}
            if start + self.page_size < len(self.names):
                body["nextPageToken"] = str(start + self.page_size)
            return httpx.Response(200, json=body)
        name = path.rsplit("/", 1)[-1].removeprefix("gm-")
        return httpx.Response(
            200,
            json={"id": f"gm-{name}", "raw": raw_message(name), "internalDate": "1761800000000"},
        )
