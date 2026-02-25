"""Structured logging and health metrics aggregation."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class HealthSnapshot:
    uptime_seconds: float
    total_requests: int
    error_rate: float
    avg_latency_ms: float
    provider_status: dict[str, Any]


class ServerMetrics:
    def __init__(self, started_at: float | None = None) -> None:
        self.started_at = started_at or time.time()
        self._lock = threading.Lock()
        self.total_requests = 0
        self.error_requests = 0
        self.total_latency_ms = 0.0
        self.rate_limit_hits: dict[str, int] = {}

    def record(self, latency_ms: float, success: bool) -> None:
        with self._lock:
            self.total_requests += 1
            if not success:
                self.error_requests += 1
            self.total_latency_ms += max(0.0, latency_ms)

    def record_rate_limit_hit(self, client_id: str) -> None:
        with self._lock:
            self.rate_limit_hits[client_id] = self.rate_limit_hits.get(client_id, 0) + 1

    def snapshot(self, provider_status: dict[str, Any]) -> HealthSnapshot:
        with self._lock:
            requests = self.total_requests
            avg_latency = (self.total_latency_ms / requests) if requests else 0.0
            error_rate = (self.error_requests / requests) if requests else 0.0
        return HealthSnapshot(
            uptime_seconds=max(0.0, time.time() - self.started_at),
            total_requests=requests,
            error_rate=error_rate,
            avg_latency_ms=avg_latency,
            provider_status=provider_status,
        )


def log_tool_event(
    tool: str,
    symbol: str | None,
    latency_ms: float,
    success: bool,
    client_id: str,
    warning: str | None = None,
) -> None:
    payload = {
        "tool": tool,
        "symbol": symbol,
        "latency_ms": round(latency_ms, 3),
        "success": success,
        "client_id": client_id,
        "timestamp": int(time.time()),
    }
    if warning:
        payload["warning"] = warning
    print(json.dumps(payload, ensure_ascii=True))


