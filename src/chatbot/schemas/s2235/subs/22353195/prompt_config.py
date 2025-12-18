"""Subschema-specific prompt customizations for 22353195 - Social Security (District Expenditure)"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration"""
    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None

# Schema Pattern: Same as 22350338 - revised_grant_2025_26, extra budget_grant_2025_26
PROMPT_CONFIG = PromptConfig(
    custom_context={
        'data_relationships': """- district_expenditure_22353195: District-wise social security expenditure
  * CRITICAL: Uses "revised_grant_2025_26" (सुधारित अनुदान) - NOT "revised_estimate"
  * Missing expenditure_2024_25 column
  * EXTRA COLUMN: budget_grant_2025_26 (in addition to budget_grant_2024_25)
  * COLUMNS:
    - "fiscal_year" (CHAR(7)): e.g. '2025-26'
    - "scheme_code" (VARCHAR): '2235'
    - "sub_scheme_code" (VARCHAR): '22353195'
    - "district" (VARCHAR): District name
    - "expenditure_2022_23", "expenditure_2023_24" (BIGINT): historical expenditure
    - "budget_grant_2024_25" (BIGINT): budget allocation for 2024-25
    - "budget_grant_2025_26" (BIGINT): budget allocation for 2025-26
    - "revised_grant_2025_26" (BIGINT): revised allocation for 2025-26
    - "budget_estimate_2026_27" (BIGINT): projected budget for 2026-27
    - "remarks" (VARCHAR): optional notes
  * RELATIONSHIPS:
    - Single-table structure
    - One row per district per fiscal year
    - Division total: SUM across 7 districts (exclude DCO Staff)""",
        
        'common_patterns': """- Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
- Division Total: Exclude DCO Staff from Konkan Division aggregations
- Marathi to English:
  * जिल्हा → district
  * प्रत्यक्ष खर्च → expenditure
  * अर्थसंकल्पीय अनुदान 2024-25 → budget_grant_2024_25
  * अर्थसंकल्पीय अनुदान 2025-26 → budget_grant_2025_26 (EXTRA COLUMN)
  * सुधारित अनुदान 2025-26 → revised_grant_2025_26 (CRITICAL: Use 'grant' not 'estimate')
  * अर्थसंकल्पीय अंदाज 2026-27 → budget_estimate_2026_27
  * कोकण विभाग → Konkan Division
  * शेरा → remarks
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Current fiscal year for filtering: '2025-26'""",
        
        'examples': """Question: रायगडचा 2022-23 चा खर्च
SQL Query: SELECT de."district", de."expenditure_2022_23"
FROM district_expenditure_22353195 de
WHERE de."fiscal_year" = '2025-26' AND de."district" = 'Raigad'
LIMIT {top_k};

Question: सुधारित अनुदान सर्व जिल्ह्यांसाठी
SQL Query: SELECT de."district", de."revised_grant_2025_26"
FROM district_expenditure_22353195 de
WHERE de."fiscal_year" = '2025-26'
ORDER BY de."revised_grant_2025_26" DESC
LIMIT {top_k};

Question: कोकण विभाग एकूण खर्च 2023-24
SQL Query: SELECT SUM(de."expenditure_2023_24") as total_expenditure
FROM district_expenditure_22353195 de
WHERE de."fiscal_year" = '2025-26'
  AND de."district" IN ('Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg')
  AND de."district" != 'DCO Staff'
LIMIT {top_k};"""
    },
    table_names={
        'district_expenditure_table': 'district_expenditure_22353195'
    }
)
