"""Runtime health service."""

from __future__ import annotations

from mcp_server.runtime.monitoring import HealthSnapshot
from mcp_server.services.base import ServiceContext
from mcp_server.services.provider_status import ProviderStatus


class RuntimeService:
    def __init__(self, ctx: ServiceContext) -> None:
        self.ctx = ctx

    def get_server_health(self) -> HealthSnapshot:
        provider_status_obj = self.ctx.get_provider("provider_status")
        provider_status: dict[str, float | None] = {}
        if isinstance(provider_status_obj, ProviderStatus):
            for provider in [
                "finnhub",
                "alphavantage",
                "fmp",
                "twelvedata",
                "marketstack",
                "newsapi",
                "yahoo",
                "fred",
            ]:
                provider_status[provider] = provider_status_obj.get_disabled_until(provider)
        metrics = self.ctx.server_metrics
        if metrics is None:
            return HealthSnapshot(
                uptime_seconds=0.0,
                total_requests=0,
                error_rate=0.0,
                avg_latency_ms=0.0,
                provider_status=provider_status,
            )
        return metrics.snapshot(provider_status)


