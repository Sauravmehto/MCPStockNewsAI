"""Shared service orchestration helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.providers.http import ProviderError
from mcp_server.utils.rate_limit import RateLimiterRegistry

SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
VALID_INTERVALS = {"1", "5", "15", "30", "60", "D", "W", "M"}
T = TypeVar("T")


@dataclass
class ErrorEnvelope:
    code: str
    message: str
    retriable: bool = True
    provider: str | None = None


@dataclass
class ServiceResult(Generic[T]):
    data: T | None
    source: str | None = None
    warning: str | None = None
    error: ErrorEnvelope | None = None


@dataclass
class ServiceContext:
    providers: dict[str, object]
    cache: TTLCache
    rate_limiter: RateLimiterRegistry
    cache_ttl_seconds: int = 60

    def get_provider(self, name: str) -> object | None:
        return self.providers.get(name)


def validate_symbol(symbol: str) -> str:
    clean = symbol.strip().upper()
    if not clean or len(clean) > 10 or not SYMBOL_PATTERN.match(clean):
        raise ValueError("Symbol must be 1-10 chars: A-Z, 0-9, dot, hyphen.")
    return clean


def validate_interval(interval: str) -> str:
    if interval not in VALID_INTERVALS:
        raise ValueError("Interval must be one of: 1, 5, 15, 30, 60, D, W, M.")
    return interval


def validate_range(from_unix: int, to_unix: int) -> None:
    if from_unix <= 0 or to_unix <= 0:
        raise ValueError("from/to must be positive unix timestamps.")
    if from_unix >= to_unix:
        raise ValueError("`from` must be less than `to`.")
    if to_unix - from_unix > 60 * 60 * 24 * 365 * 5:
        raise ValueError("Date window is too large. Maximum range is 5 years.")


def envelope_from_provider_error(error: ProviderError) -> ErrorEnvelope:
    retriable = error.code in {"RATE_LIMIT", "NETWORK", "UPSTREAM", "BAD_RESPONSE"}
    return ErrorEnvelope(code=error.code, message=error.message, retriable=retriable, provider=error.provider)


def run_with_cache(
    ctx: ServiceContext,
    cache_key: str,
    call: Callable[[], T],
    ttl_seconds: int | None = None,
) -> T:
    cached = ctx.cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    value = call()
    ctx.cache.set(cache_key, value, ttl_seconds=ttl_seconds or ctx.cache_ttl_seconds)
    return value


def execute_with_fallback(
    tool_name: str,
    providers: list[tuple[str, Callable[[], T | None]]],
    ctx: ServiceContext,
) -> ServiceResult[T]:
    errors: list[ProviderError] = []
    for provider_name, call in providers:
        try:
            ctx.rate_limiter.wait(provider_name)
            value = call()
            if value is not None:
                warning = None if not errors else "Used fallback provider due to upstream issue."
                return ServiceResult(data=value, source=provider_name, warning=warning)
        except ProviderError as error:
            errors.append(error)
    if errors:
        envelope = envelope_from_provider_error(errors[-1])
        envelope.message = f"{tool_name} failed: {envelope.message}"
        return ServiceResult(data=None, error=envelope)
    return ServiceResult(
        data=None,
        error=ErrorEnvelope(code="NOT_FOUND", message=f"{tool_name} failed: no provider returned data.", retriable=False),
    )


