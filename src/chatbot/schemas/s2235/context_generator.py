"""Schema context generator for 2235 - handles multiple subschemes with schema variations"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates schema-specific context for 2235 subschemes"""
    
    @staticmethod
    def get_table_name(config: BaseSchemeConfig) -> str:
        """Extract table name from config based on subscheme code"""
        sub_code = config.code
        return f"district_expenditure_{sub_code}"
    
    @staticmethod
    def generate_data_relationships(table_name: str, sub_scheme_code: str) -> str:
        """Generate data relationships with schema-aware column documentation"""
        # Detect schema pattern
        has_exp_2024_25 = sub_scheme_code == '22353408'
        uses_revised_estimate = sub_scheme_code == '22353408'
        
        columns = [
            "expenditure_2022_23, expenditure_2023_24",
            "expenditure_2024_25," if has_exp_2024_25 else "",
            "budget_grant_2024_25," if not has_exp_2024_25 else "",
            "budget_grant_2025_26," if sub_scheme_code in ['22350338', '22353195', '22353408'] else "",
            "revised_estimate_2025_26" if uses_revised_estimate else "revised_grant_2025_26",
            ", budget_estimate_2026_27"
        ]
        
        col_list = ' '.join(columns).replace('  ', ' ').strip()
        revised_term = "revised_estimate_2025_26 (सुधारित अंदाज)" if uses_revised_estimate else "revised_grant_2025_26 (सुधारित अनुदान)"
        
        return f"""- {table_name}: District-wise social security expenditure
  * Structure: One row per district (7 Konkan districts + DCO Staff)
  * Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
  * CRITICAL: Uses {revised_term}
  * {'Has' if has_exp_2024_25 else 'Missing'} expenditure_2024_25 column
  * Columns: {col_list}
  * All amounts in BIGINT (Indian Rupees)
  * For totals: SUM() aggregation across districts
  * Division total: Exclude DCO Staff from Konkan Division aggregations"""
    
    @staticmethod
    def generate_common_patterns(sub_scheme_code: str) -> str:
        """Generate common patterns with subscheme-specific terminology"""
        uses_revised_estimate = sub_scheme_code == '22353408'
        revised_term_mr = "सुधारित अंदाज" if uses_revised_estimate else "सुधारित अनुदान"
        revised_col = "revised_estimate_2025_26" if uses_revised_estimate else "revised_grant_2025_26"
        
        return f"""- Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
- Division Total: Exclude DCO Staff from aggregations
- Konkan Division = all 7 districts (excluding DCO Staff)
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Marathi terms:
  * जिल्हा → district
  * प्रत्यक्ष खर्च → expenditure
  * अर्थसंकल्पीय अनुदान → budget grant
  * {revised_term_mr} → {revised_col}
  * अर्थसंकल्पीय अंदाज → budget estimate
  * कोकण विभाग → Konkan Division
  * शेरा → remarks
- Current fiscal year for filtering: '2025-26'"""
    
    @staticmethod
    def generate_examples(table_name: str, sub_scheme_code: str) -> str:
        """Generate practical SQL examples with schema-aware columns"""
        uses_revised_estimate = sub_scheme_code == '22353408'
        has_exp_2024_25 = sub_scheme_code == '22353408'
        revised_col = "revised_estimate_2025_26" if uses_revised_estimate else "revised_grant_2025_26"
        
        examples = f"""Example 1: Single district query
Question: ठाण्याचा खर्च 2022-23
SQL: SELECT district, expenditure_2022_23 FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Thane';

Example 2: Revised amount query
Question: मुंबई शहराचा सुधारित {'अंदाज' if uses_revised_estimate else 'अनुदान'} 2025-26
SQL: SELECT district, {revised_col} FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Mumbai City';

Example 3: Division total (exclude DCO Staff)
Question: कोकण विभाग एकूण 2022-23
SQL: SELECT SUM(expenditure_2022_23) as total 
FROM {table_name} 
WHERE fiscal_year = '2025-26' 
  AND district IN ('Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg')
  AND district != 'DCO Staff';"""

        if has_exp_2024_25:
            examples += f"""

Example 4: 2024-25 expenditure
Question: 2024-25 चा खर्च दाखवा
SQL: SELECT district, expenditure_2024_25 FROM {table_name}
WHERE fiscal_year = '2025-26'
ORDER BY expenditure_2024_25 DESC;"""

        return examples
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary with module-level caching"""
        sub_scheme_code = config.code
        cache_key = f"s2235_{sub_scheme_code}"
        
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]
        
        table_name = SchemaContextGenerator.get_table_name(config)
        custom = custom_context or {}
        
        context = {
            'table_name': table_name,
            'data_relationships': custom.get('data_relationships') or SchemaContextGenerator.generate_data_relationships(table_name, sub_scheme_code),
            'common_patterns': custom.get('common_patterns') or SchemaContextGenerator.generate_common_patterns(sub_scheme_code),
            'examples': custom.get('examples') or SchemaContextGenerator.generate_examples(table_name, sub_scheme_code)
        }
        
        _CONTEXT_CACHE[cache_key] = context
        return context
