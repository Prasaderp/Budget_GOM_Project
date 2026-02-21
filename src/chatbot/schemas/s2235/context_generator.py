from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}


class SchemaContextGenerator:
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s2235_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]

        table_name = f"district_expenditure_{config.code}"
        
        context = {
            'district_expenditure_table': table_name,
        }

        _CONTEXT_CACHE[cache_key] = context
        return context
