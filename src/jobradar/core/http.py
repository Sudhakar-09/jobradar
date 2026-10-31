"""The only way JobRadar makes outbound HTTP requests (docs/coding-standards.md §6).

`PoliteClient` enforces, on every request and every redirect hop:
- the source policy for the requested access mode (ADR-0022);
- HTTPS only, and no private, loopback, link-local or otherwise non-public addresses (SSRF);
- a per-policy rate limit, connect/read/total timeouts and a response size cap;
- retries with exponential backoff and jitter for retryable failures, honouring Retry-After;
- a clear User-Agent.
Logs carry host and path only: query strings can contain API keys.

Residual risk: DNS can change between the address check and the connection (DNS rebinding).
Phase 7 adds an egress proxy that enforces the same address rules at connect time.
"""

import asyncio
import ipaddress
import json
import socket
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Final, Protocol

import httpx
import structlog
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception, stop_after_attempt
from tenacity.wait import wait_exponential_jitter

from jobradar.core.errors import (
    ExternalServiceError,
    PolicyDeniedError,
    RateLimitedError,
    UnsafeUrlError,
)
from jobradar.core.settings import Settings
from jobradar.core.source_policies import AccessMode, RateLimit, SourcePolicyRegistry

RETRYABLE_STATUS: Final = frozenset({500, 502, 503, 504})
TOO_MANY_REQUESTS: Final = 429
REDIRECT_STATUS: Final = frozenset({301, 302, 303, 307, 308})
SECONDS_PER_MINUTE: Final = 60.0
TOKEN_EPSILON: Final = 1e-9  # float refill error; without it a wait can shrink to nothing
_BODY_ENCODING_HEADERS: Final = frozenset(
    {"content-encoding", "content-length", "transfer-encoding"}
)
BACKOFF_INITIAL_SECONDS: Final = 0.5
BACKOFF_MAX_SECONDS: Final = 10.0
logger = structlog.get_logger(__name__)
_BACKOFF: Final = wait_exponential_jitter(
    multiplier=BACKOFF_INITIAL_SECONDS, max=BACKOFF_MAX_SECONDS
)

Sleep = Callable[[float], Awaitable[None]]
Monotonic = Callable[[], float]


class Resolver(Protocol):
    """Resolves a host name to IP address strings."""

    async def resolve(self, host: str) -> list[str]:
        """Return every address the host resolves to."""
        ...


class SystemResolver:
    """DNS resolution through the operating system."""

    async def resolve(self, host: str) -> list[str]:
        """Return every address the host resolves to (IPv4 and IPv6)."""
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return sorted({str(info[4][0]) for info in infos})


class _TokenBucket:
    """In-process rate limiter for one policy (Redis-backed buckets arrive with workers)."""

    def __init__(self, limit: RateLimit, monotonic: Monotonic, sleep: Sleep) -> None:
        self._rate = limit.per_minute / SECONDS_PER_MINUTE
        self._capacity = float(limit.burst)
        self._tokens = float(limit.burst)
        self._monotonic = monotonic
        self._sleep = sleep
        self._updated = monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = self._monotonic()
                elapsed = now - self._updated
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._updated = now
                if self._tokens >= 1 - TOKEN_EPSILON:
                    self._tokens = max(0.0, self._tokens - 1)
                    return
                await self._sleep((1 - self._tokens) / self._rate)


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _retry_after_seconds(response: httpx.Response, now: float) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    if value.strip().isdigit():
        return float(value)
    try:
        return max(0.0, parsedate_to_datetime(value).timestamp() - now)
    except (TypeError, ValueError):
        return None


def _is_retryable(error: BaseException) -> bool:
    return isinstance(error, ExternalServiceError) and error.retryable


@dataclass(frozen=True, slots=True)
class _Call:
    """One logical request (retried as a unit)."""

    method: str
    url: httpx.URL
    mode: AccessMode
    headers: dict[str, str]
    data: dict[str, str] | None = None


class PoliteClient:
    """Policy-checked, SSRF-guarded, rate-limited, retrying async HTTP client."""

    def __init__(
        self,
        registry: SourcePolicyRegistry,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Resolver | None = None,
        sleep: Sleep = asyncio.sleep,
        monotonic: Monotonic = time.monotonic,
    ) -> None:
        """Create a client; tests inject transport, resolver, sleep and monotonic."""
        self._registry = registry
        self._settings = settings
        self._resolver = resolver or SystemResolver()
        self._sleep = sleep
        self._monotonic = monotonic
        self._buckets: dict[str, _TokenBucket] = {}
        self._client = httpx.AsyncClient(
            transport=transport,
            follow_redirects=False,
            timeout=httpx.Timeout(
                settings.http_read_timeout_seconds,
                connect=settings.http_connect_timeout_seconds,
            ),
            headers={"User-Agent": settings.http_user_agent_header},
        )

    async def __aenter__(self) -> "PoliteClient":
        """Use the client as an async context manager."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the underlying connection pool."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        await self._client.aclose()

    async def get_json(
        self,
        url: str,
        *,
        mode: AccessMode,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> object:
        """GET ``url`` and decode a JSON body.

        Raises:
            PolicyDeniedError: the host's policy does not allow ``mode``.
            UnsafeUrlError: the URL is not HTTPS or resolves to a non-public address.
            ExternalServiceError: the request failed after retries, or the body is not JSON.
        """
        response = await self.get(url, mode=mode, params=params, headers=headers)
        try:
            return json.loads(response.content)
        except ValueError as exc:
            raise ExternalServiceError(response.url.host, "invalid JSON", retryable=False) from exc

    async def get(
        self,
        url: str,
        *,
        mode: AccessMode,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """GET ``url`` with every safeguard; returns a fully read response with status 2xx.

        Raises:
            PolicyDeniedError: the host's policy does not allow ``mode``.
            UnsafeUrlError: the URL is not HTTPS or resolves to a non-public address.
            ExternalServiceError: the request failed after retries.
        """
        request_url = httpx.URL(url)
        if params:  # merge: httpx.URL(url, params=...) would drop a query already in url
            request_url = request_url.copy_merge_params(params)
        return await self._retrying(_Call("GET", request_url, mode, dict(headers or {})))

    async def post_form(
        self,
        url: str,
        *,
        mode: AccessMode,
        data: Mapping[str, str],
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """POST a form (e.g. an OAuth token refresh) with the same safeguards as :meth:`get`.

        Redirects are not followed for POST. The form body is never logged.
        """
        call = _Call("POST", httpx.URL(url), mode, dict(headers or {}), dict(data))
        return await self._retrying(call)

    async def _retrying(self, call: _Call) -> httpx.Response:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._settings.http_max_attempts),
            wait=self._wait,
            retry=retry_if_exception(_is_retryable),
            sleep=self._sleep,
            reraise=True,
        )
        async for attempt in retrying:
            with attempt:
                return await self._attempt(call)
        raise AssertionError("unreachable: tenacity reraises the last error")  # pragma: no cover

    def _wait(self, state: RetryCallState) -> float:
        backoff = _BACKOFF(state)
        error = state.outcome.exception() if state.outcome else None
        if isinstance(error, RateLimitedError) and error.retry_after is not None:
            return min(max(backoff, error.retry_after), self._settings.http_retry_after_cap_seconds)
        return backoff

    async def _attempt(self, call: _Call) -> httpx.Response:
        url = call.url
        for _hop in range(self._settings.http_max_redirects + 1):
            await self._check_url(url, call.mode)
            response = await self._send(call, url)
            if response.status_code not in REDIRECT_STATUS:
                return self._checked(response)
            if call.method != "GET":
                raise ExternalServiceError(url.host, "redirect on POST", retryable=False)
            location = response.headers.get("Location")
            if not location:
                raise ExternalServiceError(url.host, "redirect without Location", retryable=False)
            url = url.join(location)
        raise ExternalServiceError(url.host, "too many redirects", retryable=False)

    async def _check_url(self, url: httpx.URL, mode: AccessMode) -> None:
        if url.scheme != "https":
            raise UnsafeUrlError(f"only https is allowed, got {url.scheme}")
        host = url.host
        policy = self._registry.policy_for(host)
        if mode not in policy.modes:
            raise PolicyDeniedError(f"{policy.id} does not allow {mode.value} on {host}")
        try:
            addresses = await self._resolver.resolve(host)
        except OSError as exc:
            raise ExternalServiceError(host, "DNS resolution failed", retryable=True) from exc
        if not addresses or not all(_is_public(address) for address in addresses):
            raise UnsafeUrlError(f"{host} resolves to a non-public address")
        await self._bucket(policy.id, policy.rate_limit).acquire()

    def _bucket(self, policy_id: str, limit: RateLimit) -> _TokenBucket:
        if policy_id not in self._buckets:
            self._buckets[policy_id] = _TokenBucket(limit, self._monotonic, self._sleep)
        return self._buckets[policy_id]

    async def _send(self, call: _Call, url: httpx.URL) -> httpx.Response:
        started = self._monotonic()
        try:
            async with asyncio.timeout(self._settings.http_total_timeout_seconds):
                request = self._client.build_request(
                    call.method, url, headers=call.headers, data=call.data
                )
                streamed = await self._client.send(request, stream=True)
                try:
                    body = await self._read_capped(streamed)
                finally:
                    await streamed.aclose()
                headers_out = {
                    key: value
                    for key, value in streamed.headers.items()
                    if key.lower() not in _BODY_ENCODING_HEADERS
                }
                response = httpx.Response(
                    streamed.status_code, headers=headers_out, content=body, request=request
                )
        except (TimeoutError, httpx.TimeoutException, httpx.TransportError) as exc:
            logger.warning(
                "http.request_failed", host=url.host, path=url.path, error=type(exc).__name__
            )
            raise ExternalServiceError(url.host, type(exc).__name__, retryable=True) from exc
        logger.info(
            "http.request_finished",
            host=url.host,
            path=url.path,
            status=response.status_code,
            duration_ms=round((self._monotonic() - started) * 1000),
        )
        return response

    async def _read_capped(self, response: httpx.Response) -> bytes:
        limit = self._settings.http_max_response_bytes
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():  # decoded: cap applies after decompression
            size += len(chunk)
            if size > limit:
                raise ExternalServiceError(response.url.host, "response too large", retryable=False)
            chunks.append(chunk)
        return b"".join(chunks)

    def _checked(self, response: httpx.Response) -> httpx.Response:
        status = response.status_code
        host = response.url.host
        if status == TOO_MANY_REQUESTS:
            raise RateLimitedError(host, _retry_after_seconds(response, time.time()))
        if status in RETRYABLE_STATUS:
            raise ExternalServiceError(host, f"HTTP {status}", retryable=True, status_code=status)
        if not response.is_success:
            raise ExternalServiceError(host, f"HTTP {status}", retryable=False, status_code=status)
        return response
