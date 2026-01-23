from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    
    @staticmethod
    def get_table_names(config: BaseSchemeConfig) -> Dict[str, str]:
        return {
            "sub_head": "sub_head_expenditure_2075",
            "district": "district_expenditure_2075"
        }
    
    @staticmethod
    def generate_data_relationships(tables: Dict[str, str]) -> str:
        return f"""- {tables['sub_head']}: Sub-head expenditure (249 - DCO only, single row)
  * Filter: sub_scheme_code = '20750249'
  * NO district filtering
  * Expenditure columns: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25
  * Budget columns: budget_estimate, revised_estimate, budget_estimate_2026_27

- {tables['district']}: District-wise expenditure (294 - 4 districts)
  * Filter: sub_scheme_code = '20750294'
  * Districts: Thane, Palghar, Raigad, Sindhudurg
  * Same expenditure and budget columns as sub_head table
  * Filter by district column for specific districts"""
    
    @staticmethod
    def generate_common_patterns() -> str:
        return """- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Budget types: budget_estimate (अर्थसंकल्पीय अंदाज), revised_estimate (सुधारित अंदाज)
- All amounts in thousands (हजार) stored as BIGINT
- Scheme 2075: Miscellaneous General Services - Pension Expenditure
- Two sub-schemes: 249 (sub-head) and 294 (district-wise)
- Current fiscal year: '2025-26'"""
    
    @staticmethod
    def generate_examples(tables: Dict[str, str]) -> str:
        return f"""Example 1: Sub-head expenditure (DCO only)
Question: What is the sub-head expenditure in 2022-23?
SQL: SELECT sub_head, expenditure_2022_23 
FROM {tables['sub_head']}
WHERE fiscal_year = '2025-26' AND sub_scheme_code = '20750249';

Example 2: District-wise totals
Question: Total budget estimate across all districts
SQL: SELECT SUM(budget_estimate) as total 
FROM {tables['district']}
WHERE fiscal_year = '2025-26' AND sub_scheme_code = '20750294';

Example 3: Specific district expenditure
Question: Show Thane district expenditure trends
SQL: SELECT district, expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 
FROM {tables['district']}
WHERE fiscal_year = '2025-26' AND sub_scheme_code = '20750294' AND district = 'Thane';

Example 4: Combined total from both tables
Question: Total pension expenditure across both sub-schemes
SQL: 
SELECT 'Sub-head' as type, SUM(expenditure_2024_25) as total 
FROM {tables['sub_head']} 
WHERE fiscal_year = '2025-26' AND sub_scheme_code = '20750249'
UNION ALL
SELECT 'Districts' as type, SUM(expenditure_2024_25) as total 
FROM {tables['district']} 
WHERE fiscal_year = '2025-26' AND sub_scheme_code = '20750294';"""
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cache_key = f"s2075_{config.code}"
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]
        
        tables = SchemaContextGenerator.get_table_names(config)
        custom = custom_context or {}
        
        context = {
            'table_name': f"{tables['sub_head']}, {tables['district']}",
            'data_relationships': custom.get('data_relationships') or SchemaContextGenerator.generate_data_relationships(tables),
            'common_patterns': custom.get('common_patterns') or SchemaContextGenerator.generate_common_patterns(),
            'examples': custom.get('examples') or SchemaContextGenerator.generate_examples(tables)
        }
        
        _CONTEXT_CACHE[cache_key] = context
        return context
