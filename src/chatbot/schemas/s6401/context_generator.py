from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    @staticmethod
    def get_table_names(config: BaseSchemeConfig) -> Dict[str, str]:
        return {name: form.table_name for name, form in config.forms.items() if form.table_name} if config.forms else {}

    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s6401_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]
        
        _CONTEXT_CACHE[cache_key] = {
            'table_name': ", ".join(SchemaContextGenerator.get_table_names(config).values()),
            'data_relationships': '',
            'common_patterns': '',
            'examples': ''
        }
        return _CONTEXT_CACHE[cache_key]
