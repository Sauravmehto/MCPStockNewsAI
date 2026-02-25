"""Simple per-provider minimum-interval limiter."""

from __future__ import annotations

import time
from threading import Lock


class RateLimiterRegistry:
    """Ensures calls for a provider respect a minimum interval."""

    def __init__(self, min_interval_seconds: float = 0.2) -> None:
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self._last_called: dict[str, float] = {}
        self._lock = Lock()

    def wait(self, provider: str) -> None:
        if self.min_interval_seconds <= 0:
            return
        with self._lock:
            last = self._last_called.get(provider)
            now = time.time()
            if last is not None:
                delta = now - last
                if delta < self.min_interval_seconds:
                    time.sleep(self.min_interval_seconds - delta)
            self._last_called[provider] = time.time()


