from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig
from ...cache import TTLCache

_CONTEXT_CACHE = TTLCache(maxsize=20, ttl=900)

class SchemaContextGenerator:
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s0029_{config.code}"
        cached = _CONTEXT_CACHE.get(cache_key)
        if cached:
            return cached

        table_names = {}
        for form_name, form_config in config.forms.items():
            table_names[form_name] = form_config.table_name

        context = {
            'district_revenue_table': table_names.get('district_revenue', ''),
        }

        _CONTEXT_CACHE.put(cache_key, context)
        return context
