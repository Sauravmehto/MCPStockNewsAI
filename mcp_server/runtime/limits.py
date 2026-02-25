"""Per-client rate limiting and bounded request queue controls."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = max(0.0, retry_after_seconds)
        super().__init__("Rate limit exceeded")


class RequestLimiter:
    def __init__(self, requests_per_minute: int = 100, queue_limit: int = 200) -> None:
        self.requests_per_minute = max(1, requests_per_minute)
        self.queue_limit = max(1, queue_limit)
        self._lock = threading.Lock()
        self._timestamps: dict[str, deque[float]] = defaultdict(deque)
        self._inflight = 0

    def acquire(self, client_id: str) -> None:
        now = time.time()
        window_start = now - 60.0
        with self._lock:
            if self._inflight >= self.queue_limit:
                raise RateLimitExceeded(retry_after_seconds=1.0)
            self._inflight += 1
            bucket = self._timestamps[client_id]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= self.requests_per_minute:
                retry_after = max(0.1, 60.0 - (now - bucket[0]))
                self._inflight -= 1
                raise RateLimitExceeded(retry_after_seconds=retry_after)
            bucket.append(now)

    def release(self) -> None:
        with self._lock:
            self._inflight = max(0, self._inflight - 1)


