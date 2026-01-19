"""Cache service for sub-scheme 20530313."""
from typing import Optional, List
from src.utils_cache import memory_cache


class CacheService:
    """Scheme-specific cache operations."""

    SCHEME_PREFIX = "s20530313"

    @staticmethod
    def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[List[str]] = None):
        """Invalidate scheme-related cache entries."""
        default_patterns = [
            "budget_summary", "budget_details", "unit_exp_summary",
            "unit_exp_charts", "post_status", "post_expenses"
        ]
        patterns_to_invalidate = patterns or default_patterns

        for pattern in patterns_to_invalidate:
            if district:
                memory_cache.delete(f"{CacheService.SCHEME_PREFIX}|{pattern}|{district}")
            else:
                for key in list(memory_cache._cache.keys()):
                    if pattern in key and CacheService.SCHEME_PREFIX in key:
                        memory_cache.delete(key)


def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[List[str]] = None):
    """Shortcut function for cache invalidation."""
    CacheService.invalidate_scheme_cache(district, patterns)
