"""In-memory provider disable windows for fallback orchestration."""

from __future__ import annotations

import threading
import time


class ProviderStatus:
    """Tracks temporary provider disable windows after rate-limit events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._disabled_until: dict[str, float] = {}

    def disable_provider(self, provider: str, ttl_seconds: int) -> float:
        until = time.time() + max(1, ttl_seconds)
        with self._lock:
            current = self._disabled_until.get(provider, 0.0)
            self._disabled_until[provider] = max(current, until)
            return self._disabled_until[provider]

    def is_disabled(self, provider: str) -> bool:
        with self._lock:
            until = self._disabled_until.get(provider)
            if not until:
                return False
            if until <= time.time():
                self._disabled_until.pop(provider, None)
                return False
            return True

    def get_disabled_until(self, provider: str) -> float | None:
        with self._lock:
            until = self._disabled_until.get(provider)
            if not until or until <= time.time():
                return None
            return until


