"""Schema context generator for 7610 - unified schema across all 4 subschemes"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates schema-specific context for 7610 subschemes (all identical)"""
    
    @staticmethod
    def get_table_name(config: BaseSchemeConfig) -> str:
        """Extract table name from config based on subscheme code"""
        sub_code = config.code
        return f"district_expenditure_{sub_code}"
    
    @staticmethod
    def generate_data_relationships(table_name: str) -> str:
        """Generate data relationships - uniform across all 4 subschemes"""
        return f"""- {table_name}: District-wise public health program expenditure
  * Structure: One row per district (7 Konkan districts + DCO Staff)
  * Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
  * 3-year expenditure history: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25
  * CRITICAL: budget_estimate (NO year suffix - represents current/2025-26)
  * CRITICAL: revised_estimate (NO year suffix - represents current/2025-26)
  * budget_estimate_2026_27 (WITH year suffix - future projection)
  * COLUMNS:
    - "fiscal_year" (CHAR(7)): e.g. '2025-26'
    - "district" (VARCHAR): District name
    - "expenditure_2022_23", "expenditure_2023_24", "expenditure_2024_25" (BIGINT)
    - "budget_estimate" (BIGINT): Budget estimate for current year (NO _2025_26 suffix!)
    - "revised_estimate" (BIGINT): Revised estimate for current year (NO _2025_26 suffix!)
    - "budget_estimate_2026_27" (BIGINT): Future year projection
    - "remarks" (VARCHAR): Optional notes
  * All amounts in Indian Rupees (BIGINT)
  * For totals: SUM() aggregation across districts"""
    
    @staticmethod
    def generate_common_patterns() -> str:
        """Generate common patterns - same for all 4 subschemes"""
        return """- Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Marathi terms:
  * जिल्हा → district
  * प्रत्यक्ष खर्च → expenditure
  * अर्थसंकल्पीय अंदाज → budget_estimate (CRITICAL: NO _2025_26 suffix!)
  * सुधारित अंदाज → revised_estimate (CRITICAL: NO _2025_26 suffix!)
  * अर्थसंकल्पीय अंदाज 2026-27 → budget_estimate_2026_27
  * शेरा → remarks
- Current fiscal year for filtering: '2025-26'
- Column naming: budget_estimate and revised_estimate have NO year suffixes (unique to scheme 7610)"""
    
    @staticmethod
    def generate_examples(table_name: str) -> str:
        """Generate practical SQL examples"""
        return f"""Example 1: Budget estimate query (NO year suffix!)
Question: ठाणे चा अर्थसंकल्पीय अंदाज
SQL: SELECT district, budget_estimate FROM {table_name} 
WHERE fiscal_year = '2025-26' AND district = 'Thane';

Example 2: Revised estimate for all districts
Question: सुधारित अंदाज सर्व जिल्ह्यांसाठी
SQL: SELECT district, revised_estimate FROM {table_name}
WHERE fiscal_year = '2025-26'
ORDER BY revised_estimate DESC LIMIT {{top_k}};

Example 3: Expenditure 2024-25
Question: 2024-25 चा खर्च मुंबई शहरासाठी
SQL: SELECT district, expenditure_2024_25 FROM {table_name}
WHERE fiscal_year = '2025-26' AND district = 'Mumbai City';

Example 4: Future year budget
Question: 2026-27 चा अर्थसंकल्पीय अंदाज
SQL: SELECT district, budget_estimate_2026_27 FROM {table_name}
WHERE fiscal_year = '2025-26'
ORDER BY budget_estimate_2026_27 DESC LIMIT {{top_k}};

Example 5: Total across all districts
Question: एकूण अर्थसंकल्पीय अंदाज
SQL: SELECT SUM(budget_estimate) as total_budget FROM {table_name}
WHERE fiscal_year = '2025-26';"""
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary with module-level caching"""
        sub_scheme_code = config.code
        cache_key = f"s7610_{sub_scheme_code}"
        
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
