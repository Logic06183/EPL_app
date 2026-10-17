"""
Cache manager using an in-memory TTL cache with per-key expiry.
"""

import logging
import time
from typing import Any

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class CacheManager:
    """In-memory cache. `ttl` is the default and the upper bound; set(..., ttl=) can shorten it."""

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        self._default_ttl = ttl
        # Outer bound — entries can live at most max(ttl, 1h); per-key expiry is checked on read.
        self.memory_cache: TTLCache = TTLCache(maxsize=max_size, ttl=max(ttl, 3600))

    def get(self, key: str) -> Any | None:
        entry = self.memory_cache.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            self.memory_cache.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.memory_cache[key] = (time.monotonic() + (ttl or self._default_ttl), value)

    def delete(self, key: str) -> None:
        self.memory_cache.pop(key, None)

    def clear(self) -> None:
        self.memory_cache.clear()


_shared: CacheManager | None = None


def get_cache_manager(ttl: int = 300, max_size: int = 1000) -> CacheManager:
    """Return the process-wide CacheManager (first caller's settings win)."""
    global _shared
    if _shared is None:
        _shared = CacheManager(ttl=ttl, max_size=max_size)
    return _shared
