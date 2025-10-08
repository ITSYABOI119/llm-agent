"""
Caching Utility
Simple in-memory cache with TTL for performance optimization
"""

from typing import Any, Optional, Callable, Dict
from datetime import datetime, timedelta
import hashlib
import logging
import functools


class Cache:
    """
    Simple in-memory cache with TTL (Time To Live).

    Stores values with expiration times to speed up expensive operations
    like system info queries, file searches, and network requests.
    """

    def __init__(self, ttl: int = 300):
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds (default: 5 minutes)
        """
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/not found
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check if expired
        if datetime.now() > entry['expires']:
            del self._cache[key]
            self.logger.debug(f"Cache expired: {key}")
            return None

        self.logger.debug(f"Cache hit: {key}")
        return entry['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL (uses default if None)
        """
        if ttl is None:
            ttl = self.ttl

        self._cache[key] = {
            'value': value,
            'expires': datetime.now() + timedelta(seconds=ttl),
            'created': datetime.now()
        }

        self.logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def invalidate(self, key: str) -> None:
        """
        Remove key from cache.

        Args:
            key: Cache key to remove
        """
        if key in self._cache:
            del self._cache[key]
            self.logger.debug(f"Cache invalidated: {key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self.logger.info(f"Cache cleared: {count} entries removed")

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (total, valid, expired entries)
        """
        now = datetime.now()
        valid = sum(1 for e in self._cache.values() if now <= e['expires'])

        return {
            'total_entries': len(self._cache),
            'valid_entries': valid,
            'expired_entries': len(self._cache) - valid,
            'hit_rate': 0.0  # Could be enhanced with hit/miss tracking
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [k for k, v in self._cache.items() if now > v['expires']]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


def cached(ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results.

    Args:
        ttl: Cache TTL in seconds
        key_func: Optional function to generate cache key from args

    Example:
        @cached(ttl=60)
        def expensive_operation(param1, param2):
            # ... expensive work ...
            return result
    """
    cache = Cache(ttl=ttl)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash of function name + args
                key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Call function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result)

            return result

        # Expose cache for manual invalidation
        wrapper.cache = cache
        return wrapper

    return decorator


# Global cache instance for shared use
_global_cache = Cache(ttl=300)


def get_global_cache() -> Cache:
    """
    Get the global cache instance.

    Returns:
        Global Cache instance
    """
    return _global_cache
