"""
Cache manager using in-memory TTL cache
"""

import logging
from functools import lru_cache
from typing import Any, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class CacheManager:
    """In-memory TTL cache manager"""

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        self.memory_cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl)
        self._default_ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        return self.memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # cachetools TTLCache uses a single TTL per cache instance;
        # store without per-key TTL override for simplicity
        self.memory_cache[key] = value

    def delete(self, key: str) -> None:
        self.memory_cache.pop(key, None)

    def clear(self) -> None:
        self.memory_cache.clear()


@lru_cache()
def get_cache_manager(ttl: int = 300, max_size: int = 1000) -> CacheManager:
    """Return a shared CacheManager instance"""
    return CacheManager(ttl=ttl, max_size=max_size)
