"""Cache service for scheme cache invalidation."""
from typing import Optional
from src.utils_cache import memory_cache


class CacheService:
    """Service for cache invalidation operations."""

    @staticmethod
    def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[list] = None):
        """Invalidate cache entries for scheme-related data."""
        default_patterns = [
            "budget_summary", "budget_details", "unit_exp_summary",
            "unit_exp_charts", "post_status", "post_expenses"
        ]
        if patterns:
            default_patterns.extend(patterns)
        if district:
            default_patterns.extend([
                f"district_budget|{district}",
                f"district_summary|{district}",
                f"district_charts|{district}"
            ])

        with memory_cache._lock:
            keys = [
                k for k in list(memory_cache._store.keys())
                if any(p in k for p in default_patterns)
            ]
            for k in keys:
                memory_cache._store.pop(k, None)
