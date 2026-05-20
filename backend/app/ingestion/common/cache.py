"""Small async TTL cache for source pages that should not be refetched repeatedly."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class AsyncTTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, _CacheEntry[T]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> T | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                self._items.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: T) -> None:
        async with self._lock:
            self._items[key] = _CacheEntry(value=value, expires_at=monotonic() + self.ttl_seconds)
