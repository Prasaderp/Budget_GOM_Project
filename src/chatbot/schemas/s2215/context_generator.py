"""2215-specific schema context generator for water scarcity with account heads"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig
from src.schemes.s2215.subs.s2215.config import KONKAN_DISTRICTS, ACCOUNT_HEADS

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates 2215 schema-specific context for prompts from BaseSchemeConfig"""
    
    @staticmethod
    def get_table_name(config: BaseSchemeConfig) -> str:
        """Extract table name from config - 2215 uses single table"""
        return "account_head_district_expenditure_2215"
    
    @staticmethod
    def generate_account_heads_context() -> str:
        """Generate context about 2 account heads with district offices"""
        lines = ["ACCOUNT HEADS (2 total):"]
        for head in ACCOUNT_HEADS:
            code = head['code']
            en = head['text_en'][:100] + ('...' if len(head['text_en']) > 100 else '')
            lines.append(f"  {code}: {en}")
            lines.append(f"    Districts: {', '.join(head['district_offices'][:3])}... (5 total)")
        return "\n".join(lines)
    
    @staticmethod
    def generate_data_relationships(table_name: str) -> str:
        """Generate data relationships context for account head + district structure"""
        return f"""- {table_name}: District-wise water scarcity expenditure by account head
  * Structure: One row per (account_head_code, district_office) combination
  * Districts: 5 Konkan (Thane, Palghar, Raigad, Ratnagiri, Sindhudurg)
  * Account Heads: 2215A195 (Zilla Parishad grants), 2215A201 (Urban water scarcity)
  * Expenditure columns: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 (BIGINT)
  * Budget columns: budget_estimate_2025_26, revised_demand_2025_26, budget_estimate_2026_27 (BIGINT)
  * CRITICAL: Filter by account_head_code AND district_office for specific queries
  * For totals: Use SUM() with GROUP BY account_head_code or district_office"""
    
    @staticmethod
    def generate_common_patterns() -> str:
        """Generate common data patterns and constants"""
        districts = ', '.join(f"'{d}'" for d in KONKAN_DISTRICTS)
        account_codes = ', '.join(f"'{h['code']}'" for h in ACCOUNT_HEADS)
        return f"""- Districts (5 Konkan): {districts}
- Account Heads: {account_codes}
- Marathi district names mapped to English equivalents
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Budget types: budget_estimate (अर्थसंकल्पीय अंदाजपत्रक), revised_demand (सुधारित अंदाजपत्रक मागणी)
- Scheme: Water Scarcity relief for Konkan division
- All amounts in Indian Rupees (₹), stored as BIGINT
- Current fiscal year for filtering: '2025-26'"""
    
    @staticmethod
    def generate_examples(table_name: str) -> str:
        """Generate practical SQL examples for 2215 queries"""
        return f"""Example 1: Specific account head and district
Question: What is the expenditure for account head 2215A195 in Thane for 2024-25?
SQL: SELECT district_office, expenditure_2024_25 FROM {table_name} 
WHERE fiscal_year = '2025-26' AND account_head_code = '2215A195' 
AND district_office LIKE '%Thane%';

Example 2: Total for an account head across all districts
Question: Total budget for account head 2215A201
SQL: SELECT account_head_code, SUM(budget_estimate_2025_26) as total 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND account_head_code = '2215A201'
GROUP BY account_head_code;

Example 3: All account heads for a specific district
Question: Show all water scarcity expenditures for Palghar
SQL: SELECT account_head_code, district_office, expenditure_2024_25 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district_office LIKE '%Palghar%';"""
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary for 2215 prompts (cached)"""
        cache_key = f"s2215_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]
        
        table_name = SchemaContextGenerator.get_table_name(config)
        custom = custom_context or {}
        
        context = {
            'table_name': table_name,
            'account_heads': custom.get('account_heads') or SchemaContextGenerator.generate_account_heads_context(),
            'data_relationships': custom.get('data_relationships') or SchemaContextGenerator.generate_data_relationships(table_name),
            'common_patterns': custom.get('common_patterns') or SchemaContextGenerator.generate_common_patterns(),
            'examples': custom.get('examples') or SchemaContextGenerator.generate_examples(table_name)
        }
        
        _CONTEXT_CACHE[cache_key] = context
        return context
