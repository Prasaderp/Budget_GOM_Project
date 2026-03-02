from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig
from ...cache import TTLCache

_CONTEXT_CACHE = TTLCache(maxsize=20, ttl=900)

class SchemaContextGenerator:
    @staticmethod
    def get_table_names(config: BaseSchemeConfig) -> Dict[str, str]:
        tables = {}
        if config.forms:
            for form_name, form_config in config.forms.items():
                if form_config.table_name:
                    tables[form_name] = form_config.table_name
        return tables

    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s2215_{config.code}"
        cached = _CONTEXT_CACHE.get(cache_key)
        if cached:
            return cached
        
        tables = SchemaContextGenerator.get_table_names(config)
        table_names_str = ", ".join(t for t in tables.values() if t)
        
        context = {
            'table_name': table_names_str,
            'data_relationships': '',
            'common_patterns': '',
            'examples': ''
        }
        
        _CONTEXT_CACHE.put(cache_key, context)
        return context
