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
    
    def _make_key(self, *args, **kwargs) -> str:
        key_parts = [str(arg) for arg in args] + [f"{k}:{v}" for k, v in sorted(kwargs.items())]
        key_str = "|".join(key_parts)
        return hashlib.blake2b(key_str.encode(), digest_size=16).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
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
            
            del self._store[key]
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            if len(self._store) >= self._max_size:
                self._evict_expired(time.monotonic())
                if len(self._store) >= self._max_size:
                    self._store.popitem(last=False)
            
            expires_at = time.monotonic() + (ttl or self._default_ttl)
            self._store[key] = (expires_at, value)
            self._store.move_to_end(key)
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
    
    def clear(self) -> None:
        with self._lock:
            self._store.clear()
    
    def _evict_expired(self, now: float) -> None:
        to_delete = [key for key, (expires_at, _) in list(self._store.items())[:10] if expires_at <= now]
        for key in to_delete:
            del self._store[key]
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._store),
                "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0
            }

memory_cache = MemoryCache(max_size=2000, default_ttl=120)

def ttl_cache(ttl_seconds: int = 60, max_size: int = 500, use_global: bool = True) -> Callable:
    if use_global:
        cache = memory_cache
    else:
        cache = MemoryCache(max_size=max_size, default_ttl=ttl_seconds)
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = cache._make_key(func.__name__, *args, **kwargs)
            result = cache.get(cache_key)
            
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result
        
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.get_stats
        return wrapper
    
    return decorator

def cache_key_wrapper(prefix: str, *args, **kwargs) -> str:
    return memory_cache._make_key(prefix, *args, **kwargs)

def invalidate_cache_pattern(pattern: str) -> None:
    with memory_cache._lock:
        to_delete = [k for k in list(memory_cache._store.keys()) if pattern in k]
        for key in to_delete:
            memory_cache._store.pop(key, None)


def get_cache_stats() -> dict:
    stats = memory_cache.get_stats()
    stats["keys"] = len(memory_cache._store)
    return stats


def clear_all_cache() -> int:
    with memory_cache._lock:
        count = len(memory_cache._store)
        memory_cache._store.clear()
        return count
