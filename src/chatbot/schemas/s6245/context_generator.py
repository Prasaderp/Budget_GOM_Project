"""62450017-specific schema context generator for single-table loan structure"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig
from src.schemes.s6245.subs.s62450017.config import KONKAN_DISTRICTS

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates 62450017 schema-specific context for prompts from BaseSchemeConfig"""
    
    @staticmethod
    def get_table_name(config: BaseSchemeConfig) -> str:
        """Extract table name from config - 62450017 uses single table"""
        return "district_expenditure_62450017"
    
    @staticmethod
    def generate_data_relationships(table_name: str) -> str:
        """Generate data relationships context for single-table loan structure"""
        return f"""- {table_name}: District-wise loan expenditure for natural calamities
  * Structure: One row per district (5 districts ONLY)
  * Districts: Thane, Palghar, Raigad, Ratnagiri, Sindhudurg (NO Mumbai City/Suburban)
  * Expenditure columns: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 (BIGINT)
  * Budget columns: budget_grant_2025_26, revised_estimate_2025_26, budget_estimate_2026_27 (BIGINT)
  * CRITICAL: For totals use SUM() aggregation across 5 districts
  * CRITICAL: This is LOAN scheme, not direct relief assistance"""
    
    @staticmethod
    def generate_common_patterns() -> str:
        """Generate common data patterns and constants"""
        districts = ', '.join(f"'{d}'" for d in KONKAN_DISTRICTS)
        return f"""- Districts (5 Konkan subset): {districts}
- CRITICAL: NO Mumbai City or Mumbai Suburban in this scheme
- Marathi district names mapped to English equivalents
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Budget types: budget_grant_2025_26 (अर्थसंकल्पीय अनुदान), revised_estimate_2025_26 (सुधारित अंदाज)
- Scheme: Loans for natural calamities (not direct assistance)
- All amounts in Indian Rupees (₹), stored as BIGINT
- Current fiscal year for filtering: '2025-26'"""
    
    @staticmethod
    def generate_examples(table_name: str) -> str:
        """Generate practical SQL examples for 62450017 queries"""
        return f"""Example 1: Single district expenditure
Question: What is the loan expenditure for Thane in 2022-23?
SQL: SELECT district, expenditure_2022_23 FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Thane';

Example 2: Total across all 5 districts
Question: Total budget grant for 2025-26
SQL: SELECT SUM(budget_grant_2025_26) as total 
FROM {table_name} 
WHERE fiscal_year = '2025-26';

Example 3: Multi-year comparison
Question: Show expenditure trends for Raigad
SQL: SELECT district, expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Raigad';"""
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary for 62450017 prompts (cached)"""
        cache_key = f"s6245_{config.code}"
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
