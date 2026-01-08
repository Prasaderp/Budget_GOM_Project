"""64010018-specific schema context generator for district-wise expenditure structure"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates 64010018 schema-specific context for prompts from BaseSchemeConfig"""
    
    @staticmethod
    def get_table_name(config: BaseSchemeConfig) -> str:
        """Extract table name from config - 64010018 uses single table"""
        return "district_expenditure_64010018"
    
    @staticmethod
    def generate_data_relationships(table_name: str) -> str:
        """Generate data relationships context for district-wise expenditure structure"""
        return f"""- {table_name}: District-wise crop production loan expenditure for all Maharashtra districts
  * Structure: One row per district (7 Konkan districts + DCO Staff)
  * Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
  * Expenditure columns: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 (BIGINT)
  * Budget columns: budget_grant_2025_26, revised_estimate_2025_26, budget_estimate_2026_27 (BIGINT)
  * CRITICAL: For totals use SUM() aggregation across districts
  * CRITICAL: This is LOAN scheme for crop production (पीक उत्पादन कर्ज)"""
    
    @staticmethod
    def generate_common_patterns() -> str:
        """Generate common data patterns and constants"""
        return """- Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
- Marathi district names mapped to English equivalents
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Budget types: budget_grant_2025_26 (अर्थसंकल्पीय अनुदान), revised_estimate_2025_26 (सुधारित अंदाज)
- Scheme: Loans for crop production (पीक उत्पादन कर्ज)
- All amounts in Indian Rupees (₹), stored as BIGINT
- Current fiscal year for filtering: '2025-26'"""
    
    @staticmethod
    def generate_examples(table_name: str) -> str:
        """Generate practical SQL examples for 64010018 queries"""
        return f"""Example 1: Single district expenditure
Question: What is the loan expenditure for Thane in 2022-23?
SQL: SELECT district, expenditure_2022_23 FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Thane';

Example 2: Total across all districts
Question: Total budget grant for 2025-26
SQL: SELECT SUM(budget_grant_2025_26) as total 
FROM {table_name} 
WHERE fiscal_year = '2025-26';

Example 3: Multi-year comparison
Question: Show expenditure trends for Mumbai City
SQL: SELECT district, expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Mumbai City';

Example 4: Budget vs Revised comparison
Question: Compare budget grant and revised estimate for all districts
SQL: SELECT district, budget_grant_2025_26, revised_estimate_2025_26, 
       (revised_estimate_2025_26 - budget_grant_2025_26) as difference
FROM {table_name}
WHERE fiscal_year = '2025-26'
ORDER BY difference DESC;

Example 5: Aggregation with district breakdown
Question: Total expenditure in 2024-25 for each district
SQL: SELECT district, expenditure_2024_25
FROM {table_name}
WHERE fiscal_year = '2025-26'
ORDER BY expenditure_2024_25 DESC;"""
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary for 64010018 prompts (cached)"""
        cache_key = f"s6401_{config.code}"
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
