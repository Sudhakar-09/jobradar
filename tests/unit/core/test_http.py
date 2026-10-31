from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
import structlog

from jobradar.core.errors import (
    ExternalServiceError,
    PolicyDeniedError,
    RateLimitedError,
    UnsafeUrlError,
)
from jobradar.core.http import PoliteClient
from jobradar.core.settings import Settings
from jobradar.core.source_policies import AccessMode, load_source_policies

pytestmark = pytest.mark.anyio
ROOT = Path(__file__).resolve().parents[3]
REGISTRY = load_source_policies(ROOT / "config" / "source_policies.yaml")
GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/example/jobs"
PUBLIC_IP = "93.184.216.34"


class FakeTime:
    """Deterministic monotonic clock whose sleep advances time and records the waits."""

    def __init__(self) -> None:
        self.now = 1_000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeResolver:
    def __init__(self, mapping: dict[str, list[str]] | None = None) -> None:
        self.mapping = mapping or {}

    async def resolve(self, host: str) -> list[str]:
        return self.mapping.get(host, [PUBLIC_IP])


Handler = Callable[[httpx.Request], httpx.Response]


def make_client(
    handler: Handler,
    *,
    resolver: FakeResolver | None = None,
    fake_time: FakeTime | None = None,
    **settings: object,
) -> tuple[PoliteClient, FakeTime]:
    clock = fake_time or FakeTime()
    config = Settings.model_validate({"http_contact": "ops@example.org", **settings})
    client = PoliteClient(
        REGISTRY,
        config,
        transport=httpx.MockTransport(handler),
        resolver=resolver or FakeResolver(),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    return client, clock


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_get_json_returns_body_and_sends_user_agent() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"jobs": []})

    client, _ = make_client(handler)
    async with client:
        body = await client.get_json(GREENHOUSE, mode=AccessMode.ATS_FEED)

    assert body == {"jobs": []}
    assert seen[0].headers["User-Agent"] == "JobRadar/0.1 (+ops@example.org)"


async def test_policy_denies_mode_without_sending_request() -> None:
    calls: list[httpx.Request] = []
    client, _ = make_client(lambda r: calls.append(r) or httpx.Response(200))

    async with client:
        with pytest.raises(PolicyDeniedError):
            await client.get("https://www.linkedin.com/jobs/view/1", mode=AccessMode.ATS_FEED)

    assert calls == []


async def test_unknown_host_is_refused_for_feeds() -> None:
    client, _ = make_client(lambda _: httpx.Response(200))

    async with client:
        with pytest.raises(PolicyDeniedError):
            await client.get("https://careers.example.org/jobs", mode=AccessMode.ATS_FEED)


async def test_plain_http_is_refused() -> None:
    client, _ = make_client(lambda _: httpx.Response(200))

    async with client:
        with pytest.raises(UnsafeUrlError, match="https"):
            await client.get(GREENHOUSE.replace("https", "http"), mode=AccessMode.ATS_FEED)


@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.5",
        "127.0.0.1",
        "169.254.169.254",
        "192.168.1.1",
        "::1",
        "::ffff:10.0.0.1",
        "fd00::1",
        "100.64.0.1",
    ],
)
async def test_non_public_addresses_are_refused(address: str) -> None:
    resolver = FakeResolver({"boards-api.greenhouse.io": [PUBLIC_IP, address]})
    client, _ = make_client(lambda _: httpx.Response(200), resolver=resolver)

    async with client:
        with pytest.raises(UnsafeUrlError, match="non-public"):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)


async def test_redirect_to_disallowed_host_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "https://www.linkedin.com/x"})

    client, _ = make_client(handler)
    async with client:
        with pytest.raises(PolicyDeniedError):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)


async def test_redirect_to_private_address_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "https://boards.greenhouse.io/x"})

    resolver = FakeResolver({"boards.greenhouse.io": ["10.1.2.3"]})
    client, _ = make_client(handler, resolver=resolver)
    async with client:
        with pytest.raises(UnsafeUrlError):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)


async def test_allowed_redirect_is_followed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "boards-api.greenhouse.io":
            return httpx.Response(301, headers={"Location": "https://boards.greenhouse.io/x"})
        return httpx.Response(200, json={"ok": True})

    client, _ = make_client(handler)
    async with client:
        assert await client.get_json(GREENHOUSE, mode=AccessMode.ATS_FEED) == {"ok": True}


async def test_too_many_redirects_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": GREENHOUSE})

    client, _ = make_client(handler, http_max_redirects=2)
    async with client:
        with pytest.raises(ExternalServiceError, match="too many redirects"):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)


async def test_retryable_status_is_retried_with_backoff() -> None:
    responses = iter([httpx.Response(503), httpx.Response(502), httpx.Response(200, json=[])])
    client, clock = make_client(lambda _: next(responses))

    async with client:
        assert await client.get_json(GREENHOUSE, mode=AccessMode.ATS_FEED) == []

    assert len(clock.sleeps) == 2


async def test_retry_after_is_honoured_and_capped() -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "7"}),
            httpx.Response(429, headers={"Retry-After": "600"}),
            httpx.Response(200, json={}),
        ]
    )
    client, clock = make_client(lambda _: next(responses), http_retry_after_cap_seconds=30)

    async with client:
        await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)

    assert clock.sleeps[0] >= 7
    assert clock.sleeps[1] == 30


async def test_retries_stop_after_max_attempts() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429)

    client, _ = make_client(handler, http_max_attempts=3)
    async with client:
        with pytest.raises(RateLimitedError):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)

    assert len(calls) == 3


async def test_client_error_is_not_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404)

    client, _ = make_client(handler)
    async with client:
        with pytest.raises(ExternalServiceError) as error:
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)

    assert error.value.retryable is False
    assert len(calls) == 1


async def test_transport_timeout_is_retryable_then_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client, clock = make_client(handler, http_max_attempts=2)
    async with client:
        with pytest.raises(ExternalServiceError) as error:
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)

    assert error.value.retryable is True
    assert len(clock.sleeps) == 1


async def test_dns_failure_is_retryable() -> None:
    class BrokenResolver(FakeResolver):
        async def resolve(self, host: str) -> list[str]:
            raise OSError("no such host")

    client, _ = make_client(
        lambda _: httpx.Response(200), resolver=BrokenResolver(), http_max_attempts=1
    )
    async with client:
        with pytest.raises(ExternalServiceError, match="DNS"):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)


async def test_oversized_response_is_refused() -> None:
    client, _ = make_client(
        lambda _: httpx.Response(200, content=b"x" * 2_000), http_max_response_bytes=1_000
    )
    async with client:
        with pytest.raises(ExternalServiceError, match="too large"):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)


async def test_invalid_json_is_not_retryable() -> None:
    client, _ = make_client(lambda _: httpx.Response(200, content=b"<html>"))
    async with client:
        with pytest.raises(ExternalServiceError, match="invalid JSON"):
            await client.get_json(GREENHOUSE, mode=AccessMode.ATS_FEED)


async def test_rate_limit_waits_after_burst() -> None:
    client, clock = make_client(lambda _: httpx.Response(200, json={}))
    burst = REGISTRY.get("greenhouse").rate_limit.burst

    async with client:
        for _ in range(burst + 1):
            await client.get(GREENHOUSE, mode=AccessMode.ATS_FEED)

    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == pytest.approx(60 / REGISTRY.get("greenhouse").rate_limit.per_minute)


async def test_logs_never_contain_query_strings() -> None:
    client, _ = make_client(lambda _: httpx.Response(200, json={}))

    with structlog.testing.capture_logs() as logs:
        async with client:
            await client.get(
                "https://api.adzuna.com/v1/api/jobs/in/search/1",
                mode=AccessMode.API,
                params={"app_key": "secret-key-value", "what": "java"},
            )

    assert logs
    assert "secret-key-value" not in str(logs)
    assert logs[-1]["path"] == "/v1/api/jobs/in/search/1"
