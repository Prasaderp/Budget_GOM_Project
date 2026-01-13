import time
import hashlib
from typing import Callable, Any, Dict, Tuple, Optional
from functools import wraps
import threading
from collections import OrderedDict

class MemoryCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self._store: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, *args, context_params: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """
        Generate cache key from arguments and context parameters.
        
        Args:
            *args: Positional arguments
            context_params: Optional dict of context parameters (e.g., fiscal_year)
            **kwargs: Keyword arguments
        
        Returns:
            Hexadecimal hash string
        """
        key_parts = []
        
        # Include context params first (e.g., fiscal_year) for better cache isolation
        if context_params:
            for k in sorted(context_params.keys()):
                v = context_params[k]
                if v is not None:  # Only include non-None values
                    key_parts.append(f"ctx_{k}:{v}")
        
        # Add positional args
        key_parts.extend(str(arg) for arg in args)
        
        # Add keyword args
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        key_str = "|".join(key_parts)
        return hashlib.blake2b(key_str.encode(), digest_size=16).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if expired/missing
        """
        if not key:
            return None
        
        with self._lock:
            cached = self._store.get(key)
            if cached is None:
                self._misses += 1
                return None
            
            expires_at, value = cached
            if expires_at > time.monotonic():
                self._store.move_to_end(key)
                self._hits += 1
                return value
            
            # Expired - remove it
            del self._store[key]
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (uses default if None)
        """
        if not key:
            return
        
        with self._lock:
            # Evict expired entries before checking size
            if len(self._store) >= self._max_size:
                self._evict_expired(time.monotonic())
                # If still full, remove oldest entry
                if len(self._store) >= self._max_size:
                    self._store.popitem(last=False)
            
            expires_at = time.monotonic() + (ttl or self._default_ttl)
            self._store[key] = (expires_at, value)
            self._store.move_to_end(key)
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if not key:
            return False
        
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()
    
    def _evict_expired(self, now: float) -> None:
        """Evict expired entries (checks oldest 10 entries)."""
        to_delete = [
            key for key, (expires_at, _) 
            in list(self._store.items())[:10] 
            if expires_at <= now
        ]
        for key in to_delete:
            del self._store[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._store),
                "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0
            }

# Global cache instance
memory_cache = MemoryCache(max_size=2000, default_ttl=120)

def ttl_cache(
    ttl_seconds: int = 60, 
    max_size: int = 500, 
    use_global: bool = True,
    include_fiscal_year: bool = True
) -> Callable:
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl_seconds: Time to live in seconds
        max_size: Maximum cache size (ignored if use_global=True)
        use_global: Use global cache instance
        include_fiscal_year: Include fiscal_year from kwargs in cache key
    
    Returns:
        Decorator function
    
    Example:
        @ttl_cache(ttl_seconds=180, include_fiscal_year=True)
        def get_district_data(db: Session, district: str, fiscal_year: str):
            return db.query(...).all()
    """
    if use_global:
        cache = memory_cache
    else:
        cache = MemoryCache(max_size=max_size, default_ttl=ttl_seconds)
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract context parameters
            context_params = {}
            if include_fiscal_year and 'fiscal_year' in kwargs:
                fy = kwargs.get('fiscal_year')
                if fy is not None:
                    context_params['fiscal_year'] = str(fy)
            
            # Generate cache key with context
            cache_key = cache._make_key(
                func.__name__, 
                *args, 
                context_params=context_params,
                **kwargs
            )
            
            # Try cache first
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Cache miss - execute function
            result = func(*args, **kwargs)
            
            # Only cache non-None results
            if result is not None:
                cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        # Attach utility methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.get_stats
        return wrapper
    
    return decorator

def cache_key_wrapper(prefix: str, *args, **kwargs) -> str:
    """Generate cache key for manual cache operations."""
    if not prefix:
        raise ValueError("prefix cannot be empty")
    return memory_cache._make_key(prefix, *args, **kwargs)

def invalidate_cache_pattern(pattern: str) -> None:
    """
    Invalidate all cache entries matching pattern.
    
    Args:
        pattern: Pattern to match in cache keys
    """
    if not pattern:
        return
    
    with memory_cache._lock:
        to_delete = [k for k in list(memory_cache._store.keys()) if pattern in k]
        for key in to_delete:
            memory_cache._store.pop(key, None)


def get_cache_stats() -> dict:
    """Get global cache statistics."""
    stats = memory_cache.get_stats()
    stats["keys"] = len(memory_cache._store)
    return stats


def clear_all_cache() -> int:
    """
    Clear all entries from global cache.
    
    Returns:
        Number of entries cleared
    """
    with memory_cache._lock:
        count = len(memory_cache._store)
        memory_cache._store.clear()
        return count

