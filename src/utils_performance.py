import time
import logging
from functools import wraps
from typing import Callable, Any
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

_SLOW_THRESHOLD_MS = 500
_metrics_lock = threading.Lock()
_endpoint_metrics = defaultdict(lambda: {"count": 0, "total_ms": 0, "max_ms": 0, "slow_count": 0})


def track_performance(endpoint_name: str = None):
    def decorator(func: Callable) -> Callable:
        name = endpoint_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _record_metric(name, elapsed_ms)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _record_metric(name, elapsed_ms)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def _record_metric(name: str, elapsed_ms: float):
    with _metrics_lock:
        m = _endpoint_metrics[name]
        m["count"] += 1
        m["total_ms"] += elapsed_ms
        m["max_ms"] = max(m["max_ms"], elapsed_ms)
        if elapsed_ms > _SLOW_THRESHOLD_MS:
            m["slow_count"] += 1
            logger.warning(f"SLOW: {name} took {elapsed_ms:.1f}ms")


def get_performance_stats() -> dict:
    with _metrics_lock:
        result = {}
        for name, m in _endpoint_metrics.items():
            if m["count"] > 0:
                result[name] = {
                    "count": m["count"],
                    "avg_ms": round(m["total_ms"] / m["count"], 1),
                    "max_ms": round(m["max_ms"], 1),
                    "slow_count": m["slow_count"]
                }
        return result


def reset_performance_stats():
    with _metrics_lock:
        _endpoint_metrics.clear()


class QueryTimer:
    __slots__ = ('name', 'start', 'threshold_ms')
    
    def __init__(self, name: str, threshold_ms: float = 200):
        self.name = name
        self.threshold_ms = threshold_ms
        self.start = None
    
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        elapsed_ms = (time.perf_counter() - self.start) * 1000
        if elapsed_ms > self.threshold_ms:
            logger.warning(f"SLOW_QUERY: {self.name} took {elapsed_ms:.1f}ms")

