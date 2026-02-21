from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s0029_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]

        table_names = {}
        for form_name, form_config in config.forms.items():
            table_names[form_name] = form_config.table_name

        context = {
            'district_revenue_table': table_names.get('district_revenue', ''),
        }

        _CONTEXT_CACHE[cache_key] = context
        return context
