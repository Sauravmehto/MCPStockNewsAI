"""Central fallback orchestration for stock-domain provider calls."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from mcp_server.providers.http import ProviderError
from mcp_server.services.base import ErrorEnvelope, ServiceContext, ServiceResult
from mcp_server.services.provider_status import ProviderStatus

T = TypeVar("T")
LOGGER = logging.getLogger(__name__)
RATE_LIMIT_PATTERNS = (
    "rate limit",
    "requests per day",
    "api credits",
    "premium plan",
    "limit exceeded",
)
DEFAULT_RATE_LIMIT_DISABLE_SECONDS = 60 * 60 * 24


@dataclass(frozen=True)
class ProviderAttempt(Generic[T]):
    key: str
    label: str
    call: Callable[[], T | None]


class FallbackManager:
    def __init__(
        self,
        ctx: ServiceContext,
        provider_status: ProviderStatus,
        rate_limit_disable_seconds: dict[str, int] | None = None,
    ) -> None:
        self._ctx = ctx
        self._provider_status = provider_status
        self._rate_limit_disable_seconds = rate_limit_disable_seconds or {}

    def execute(self, operation: str, symbol: str, attempts: list[ProviderAttempt[T]]) -> ServiceResult[T]:
        had_fallback = False
        for attempt in attempts:
            if self._provider_status.is_disabled(attempt.key):
                had_fallback = True
                disabled_until = self._provider_status.get_disabled_until(attempt.key)
                LOGGER.info(
                    "provider skipped (disabled window): op=%s symbol=%s provider=%s disabled_until=%s",
                    operation,
                    symbol,
                    attempt.key,
                    disabled_until,
                )
                continue

            started = time.perf_counter()
            try:
                self._ctx.rate_limiter.wait(attempt.key)
                value = attempt.call()
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                LOGGER.info(
                    "provider attempt complete: op=%s symbol=%s provider=%s success=%s latency_ms=%s",
                    operation,
                    symbol,
                    attempt.key,
                    value is not None,
                    elapsed_ms,
                )
                if value is not None:
                    warning = "Used fallback provider due to upstream issue." if had_fallback else None
                    return ServiceResult(
                        data=value,
                        source=attempt.label,
                        warning=warning,
                        fetched_at=time.time(),
                        data_provider=attempt.label,
                        data_license="Provider terms apply",
                    )
                had_fallback = True
            except ProviderError as error:
                had_fallback = True
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                LOGGER.warning(
                    "provider attempt failed: op=%s symbol=%s provider=%s code=%s status=%s latency_ms=%s",
                    operation,
                    symbol,
                    attempt.key,
                    error.code,
                    error.status,
                    elapsed_ms,
                )
                if self.is_rate_limited(error):
                    ttl_seconds = self._rate_limit_disable_seconds.get(attempt.key, DEFAULT_RATE_LIMIT_DISABLE_SECONDS)
                    disabled_until = self._provider_status.disable_provider(attempt.key, ttl_seconds)
                    LOGGER.warning(
                        "provider disabled after rate limit: provider=%s disabled_until=%s op=%s symbol=%s",
                        attempt.key,
                        disabled_until,
                        operation,
                        symbol,
                    )
            except Exception:
                had_fallback = True
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                LOGGER.exception(
                    "provider attempt unexpected failure: op=%s symbol=%s provider=%s latency_ms=%s",
                    operation,
                    symbol,
                    attempt.key,
                    elapsed_ms,
                )

        return ServiceResult(
            data=None,
            error=ErrorEnvelope(
                code="UPSTREAM",
                message="All stock data providers are currently unavailable. Please try again later.",
                retriable=True,
            ),
        )

    @staticmethod
    def is_rate_limited(error: ProviderError) -> bool:
        if error.code == "RATE_LIMIT" or error.status == 429:
            return True
        message = (error.message or "").lower()
        return any(pattern in message for pattern in RATE_LIMIT_PATTERNS)


