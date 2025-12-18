"""2075-specific schema context generator for sub-head expenditure tracking"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates 2075 schema-specific context for prompts from BaseSchemeConfig"""
    
    @staticmethod
    def get_table_name(config: BaseSchemeConfig) -> str:
        """Extract table name from config - 2075 uses sub-head expenditure table"""
        return "sub_head_expenditure_20750249"
    
    @staticmethod
    def generate_data_relationships(table_name: str) -> str:
        """Generate data relationships context for sub-head expenditure structure"""
        return f"""- {table_name}: Sub-head and minor-head expenditure tracking
  * Structure: One row per sub_head_code
  * NO district filtering (not district-specific)
  * Expenditure columns: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 (BIGINT)
  * Budget columns: budget_estimate_2025_26, revised_estimate_2025_26, budget_estimate_2026_27 (BIGINT)
  * CRITICAL: Filter by sub_head_code or sub_head_name when querying specific sub-heads
  * For totals: Use SUM() aggregation across all sub-heads"""
    
    @staticmethod
    def generate_common_patterns() -> str:
        """Generate common data patterns and constants"""
        return """- Fiscal years: 2021-22, 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Budget types: budget_estimate (अर्थसंकल्पीय अंदाज), revised_estimate (सुधारित अंदाज)
- Sub-head codes: Query by exact sub_head_code or sub_head_name
- All amounts in Indian Rupees (₹), stored as BIGINT
- Scheme: Sub-Head Expenditure tracking (उपशिर्ष / गौणशिर्ष खर्च)
- Current fiscal year for filtering: '2025-26'"""
    
    @staticmethod
    def generate_examples(table_name: str) -> str:
        """Generate practical SQL examples for 2075 queries"""
        return f"""Example 1: Specific sub-head expenditure
Question: What is the expenditure for sub-head code 20750249 in 2022-23?
SQL: SELECT sub_head_code, sub_head_name, expenditure_2022_23 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND sub_head_code = '20750249';

Example 2: Total across all sub-heads
Question: Total budget estimate for 2025-26
SQL: SELECT SUM(budget_estimate_2025_26) as total 
FROM {table_name} 
WHERE fiscal_year = '2025-26';

Example 3: Multi-year comparison for a sub-head
Question: Show expenditure trends for sub-head 20750249
SQL: SELECT sub_head_name, expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND sub_head_code = '20750249';"""
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary for 2075 prompts (cached)"""
        cache_key = f"s2075_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]
        
        table_name = SchemaContextGenerator.get_table_name(config)
        custom = custom_context or {}
        
        context = {
            'table_name': table_name,
            'data_relationships': custom.get('data_relationships') or SchemaContextGenerator.generate_data_relationships(table_name),
            'common_patterns': custom.get('common_patterns') or SchemaContextGenerator.generate_common_patterns(),
            'examples': custom.get('examples') or SchemaContextGenerator.generate_examples(table_name)
        }
        
        _CONTEXT_CACHE[cache_key] = context
        return context
