"""
Cache management using in-memory TTL cache and optional Redis
"""

import logging
from typing import Optional, Any, Callable
from functools import wraps
from cachetools import TTLCache
import hashlib
import json

logger = logging.getLogger(__name__)


class CacheManager:
    """Unified cache manager with in-memory cache and optional Redis"""

    def __init__(
        self,
        ttl: int = 300,
        max_size: int = 1000,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize cache manager

        Args:
            ttl: Time to live in seconds
            max_size: Maximum cache size
            redis_client: Optional Redis client
        """
        self.memory_cache = TTLCache(maxsize=max_size, ttl=ttl)
        self.redis_client = redis_client
        self.ttl = ttl
        self.use_redis = redis_client is not None

        if self.use_redis:
            logger.info("Cache manager initialized with Redis")
        else:
            logger.info("Cache manager initialized with in-memory cache only")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Try Redis first if available
        if self.use_redis:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Fallback to memory cache
        return self.memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL (uses default if not provided)
        """
        ttl = ttl or self.ttl

        # Set in Redis if available
        if self.use_redis:
            try:
                self.redis_client.setex(
                    key, ttl, json.dumps(value, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # Always set in memory cache as fallback
        self.memory_cache[key] = value

    def delete(self, key: str) -> None:
        """
        Delete key from cache

        Args:
            key: Cache key to delete
        """
        if self.use_redis:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")

        if key in self.memory_cache:
            del self.memory_cache[key]

    def clear(self) -> None:
        """Clear all cache"""
        if self.use_redis:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")

        self.memory_cache.clear()

    def cached(self, key_prefix: str = "", ttl: Optional[int] = None):
        """
        Decorator for caching function results

        Args:
            key_prefix: Prefix for cache key
            ttl: Optional custom TTL

        Usage:
            @cache_manager.cached(key_prefix="predictions")
            def get_predictions(player_id: int):
                return expensive_operation(player_id)
        """

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                key_parts = [key_prefix or func.__name__]

                # Add args to key
                for arg in args:
                    key_parts.append(str(arg))

                # Add sorted kwargs to key
                for k in sorted(kwargs.keys()):
                    key_parts.append(f"{k}={kwargs[k]}")

                cache_key = ":".join(key_parts)

                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value

                # Compute value
                logger.debug(f"Cache miss: {cache_key}")
                result = func(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(
    ttl: int = 300, max_size: int = 1000, redis_client: Optional[Any] = None
) -> CacheManager:
    """
    Get or create global cache manager instance

    Args:
        ttl: Time to live in seconds
        max_size: Maximum cache size
        redis_client: Optional Redis client

    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(ttl, max_size, redis_client)
    return _cache_manager
