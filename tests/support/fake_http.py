"""Fakes for PoliteClient: deterministic time, DNS and canned HTTP responses."""

import json
from collections.abc import Callable
from pathlib import Path

import httpx

from jobradar.core.http import PoliteClient
from jobradar.core.settings import Settings
from jobradar.core.source_policies import SourcePolicyRegistry, load_source_policies

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
PUBLIC_IP = "93.184.216.34"
Handler = Callable[[httpx.Request], httpx.Response]


def registry() -> SourcePolicyRegistry:
    return load_source_policies(ROOT / "config" / "source_policies.yaml")


def fixture_json(*parts: str) -> object:
    return json.loads(FIXTURES.joinpath(*parts).read_text(encoding="utf-8"))


class FakeTime:
    """Monotonic clock whose sleep advances time and records the waits."""

    def __init__(self) -> None:
        self.now = 1_000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeResolver:
    """Resolves every host to a public address unless told otherwise."""

    def __init__(self, mapping: dict[str, list[str]] | None = None) -> None:
        self.mapping = mapping or {}

    async def resolve(self, host: str) -> list[str]:
        return self.mapping.get(host, [PUBLIC_IP])


def polite_client(handler: Handler, policies: SourcePolicyRegistry | None = None) -> PoliteClient:
    clock = FakeTime()
    return PoliteClient(
        policies or registry(),
        Settings.model_validate({}),
        transport=httpx.MockTransport(handler),
        resolver=FakeResolver(),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )


def routes(table: dict[str, object]) -> Handler:
    """Serve JSON bodies by URL path; a Response value is returned as is; unknown paths 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = table.get(request.url.path)
        if body is None:
            return httpx.Response(404)
        if isinstance(body, httpx.Response):
            return body
        return httpx.Response(200, json=body)

    return handler
