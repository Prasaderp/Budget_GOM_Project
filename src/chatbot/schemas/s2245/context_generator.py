"""2245-specific schema context generator for single-table budget structure"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig
from src.schemes.s2245.subs.s2245.config import TABLE_SECTIONS
from src.schemes.common.utils import GLOBAL_DISTRICTS_MR

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates 2245 schema-specific context for prompts from BaseSchemeConfig"""
    
    @staticmethod
    def get_table_name(config: BaseSchemeConfig) -> str:
        """Extract table name from config - 2245 uses single table"""
        return "district_expenditure_2245"
    
    @staticmethod
    def generate_table_sections_context() -> str:
        """Generate context about 24 table sections with bilingual names"""
        lines = ["TABLE SECTIONS (24 total):"]
        for section in TABLE_SECTIONS:
            code = section['code']
            mr = section['text_mr'][:80] + ('...' if len(section['text_mr']) > 80 else '')
            en = section['text_en'][:80] + ('...' if len(section['text_en']) > 80 else '')
            lines.append(f"  {code}: {en}")
            lines.append(f"    मराठी: {mr}")
        return "\n".join(lines)
    
    @staticmethod
    def generate_data_relationships(table_name: str) -> str:
        """Generate data relationships context for single-table structure"""
        return f"""- {table_name}: District-wise expenditure and budget data by table sections
  * Structure: One row per (table_section_code, district) combination
  * Expenditure columns: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 (BIGINT)
  * Budget columns: budget_estimate, revised_estimate, budget_estimate_2026_27 (BIGINT)
  * CRITICAL: For totals across districts, use SUM() aggregation
  * CRITICAL: For totals across sections, use SUM() aggregation
  * Section filtering: Always filter by table_section_code when section is specified
  * Year filtering: Use specific expenditure column (e.g., expenditure_2022_23 for 2022-23)"""
    
    @staticmethod
    def generate_common_patterns() -> str:
        """Generate common data patterns and constants"""
        districts = ', '.join(f"'{d}'" for d in GLOBAL_DISTRICTS_MR.keys())
        return f"""- Districts (Konkan region): {districts}
- Marathi district names mapped to English equivalents
- Fiscal years: 2022-23, 2023-24, 2024-25, 2026-27
- Budget types: budget_estimate (अर्थसंकल्पीय), revised_estimate (सुधारीत)
- All amounts in Indian Rupees (₹), stored as BIGINT
- Current fiscal year for filtering: '2025-26'"""
    
    @staticmethod
    def generate_examples(table_name: str) -> str:
        """Generate practical SQL examples for 2245 queries"""
        return f"""Example 1: Single district expenditure
Question: What is the expenditure for Mumbai City in 2022-23?
SQL: SELECT district, expenditure_2022_23 FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Mumbai City' LIMIT 5;

Example 2: Total for a table section
Question: Total budget estimate for section 22450155
SQL: SELECT table_section_code, SUM(budget_estimate) as total 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND table_section_code = '22450155'
GROUP BY table_section_code;

Example 3: Multi-year comparison
Question: Show expenditure trends for Thane
SQL: SELECT district, expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 
FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Thane' LIMIT 10;"""
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary for 2245 prompts (cached)"""
        cache_key = f"s2245_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]
        
        table_name = SchemaContextGenerator.get_table_name(config)
        custom = custom_context or {}
        
        context = {
            'table_name': table_name,
            'table_sections': custom.get('table_sections') or SchemaContextGenerator.generate_table_sections_context(),
            'data_relationships': custom.get('data_relationships') or SchemaContextGenerator.generate_data_relationships(table_name),
            'common_patterns': custom.get('common_patterns') or SchemaContextGenerator.generate_common_patterns(),
            'examples': custom.get('examples') or SchemaContextGenerator.generate_examples(table_name)
        }
        
        _CONTEXT_CACHE[cache_key] = context
        return context
