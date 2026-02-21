from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}


class SchemaContextGenerator:
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s2045_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]

        table_names = {}
        for form_name, form_config in config.forms.items():
            table_names[form_name] = form_config.table_name

        context = {
            'budget_post_details_table': table_names.get('budget_post_details', ''),
            'post_status_table': table_names.get('post_status', ''),
            'post_expenses_table': table_names.get('post_expenses', ''),
            'unit_expenditure_table': table_names.get('unit_expenditure', ''),
            'district_expenditure_table': table_names.get('district_expenditure', ''),
        }

        _CONTEXT_CACHE[cache_key] = context
        return context
