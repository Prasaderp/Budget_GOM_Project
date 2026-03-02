from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig
from ...cache import TTLCache

_CONTEXT_CACHE = TTLCache(maxsize=20, ttl=900)


class SchemaContextGenerator:
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s2235_{config.code}"
        cached = _CONTEXT_CACHE.get(cache_key)
        if cached:
            return cached

        table_name = f"district_expenditure_{config.code}"
        
        context = {
            'district_expenditure_table': table_name,
        }

        _CONTEXT_CACHE.put(cache_key, context)
        return context
