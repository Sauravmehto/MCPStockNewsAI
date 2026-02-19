"""Small in-memory TTL cache for stateless server runtime."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _CacheItem(Generic[T]):
    value: T
    expires_at: float


class TTLCache:
    """Thread-safe TTL cache keyed by string."""

    def __init__(self, default_ttl_seconds: int = 60) -> None:
        self.default_ttl_seconds = max(1, default_ttl_seconds)
        self._data: dict[str, _CacheItem[object]] = {}
        self._lock = Lock()

    def get(self, key: str) -> object | None:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            if item.expires_at < now:
                self._data.pop(key, None)
                return None
            return item.value

    def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else max(1, ttl_seconds)
        with self._lock:
            self._data[key] = _CacheItem(value=value, expires_at=time.time() + ttl)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


