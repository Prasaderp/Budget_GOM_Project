"""Subschema-specific prompt customizations for 22353408 - Welfare of the Elderly"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration"""
    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None

# Schema Pattern: DIFFERENT - revised_estimate_2025_26, HAS expenditure_2024_25
PROMPT_CONFIG = PromptConfig(
    custom_context={
        'data_relationships': """- district_expenditure_22353408: District-wise elderly welfare expenditure
  * CRITICAL: Uses "revised_estimate_2025_26" (सुधारित अंदाज) - NOT "revised_grant"
  * HAS expenditure_2024_25 column (3-year historical data)
  * COLUMNS:
    - "fiscal_year" (CHAR(7)): e.g. '2025-26'
    - "scheme_code" (VARCHAR): '2235'
    - "sub_scheme_code" (VARCHAR): '22353408'
    - "district" (VARCHAR): District name
    - "expenditure_2022_23", "expenditure_2023_24", "expenditure_2024_25" (BIGINT): 3-year expenditure history
    - "budget_grant_2025_26" (BIGINT): budget allocation for 2025-26
    - "revised_estimate_2025_26" (BIGINT): revised estimate for 2025-26 (CRITICAL: 'estimate' not 'grant')
    - "budget_estimate_2026_27" (BIGINT): projected budget for 2026-27
    - "remarks" (VARCHAR): optional notes
  * RELATIONSHIPS:
    - Single-table structure
    - One row per district per fiscal year
    - Division total: SUM across 7 districts (exclude DCO Staff)""",
        
        'common_patterns': """- Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
- Division Total: Exclude DCO Staff from Konkan Division aggregations
- Scheme: Welfare of the Elderly (वृद्धांचे कल्याण)
- Marathi to English:
  * जिल्हा → district
  * प्रत्यक्ष खर्च → expenditure
  * अर्थसंकल्पीय अनुदान 2025-26 → budget_grant_2025_26
  * सुधारित अंदाज 2025-26 → revised_estimate_2025_26 (CRITICAL: 'estimate' not 'grant')
  * अर्थसंकल्पीय अंदाज 2026-27 → budget_estimate_2026_27
  * कोकण विभाग → Konkan Division
  * वृद्ध → elderly
  * शेरा → remarks
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Current fiscal year for filtering: '2025-26'
- HAS 2024-25 expenditure data (3-year history available)""",
        
        'examples': """Question: रत्नागिरीचा 2024-25 चा खर्च
SQL Query: SELECT de."district", de."expenditure_2024_25"
FROM district_expenditure_22353408 de
WHERE de."fiscal_year" = '2025-26' AND de."district" = 'Ratnagiri'
LIMIT {top_k};

Question: सुधारित अंदाज 2025-26 सिंधुदुर्गसाठी
SQL Query: SELECT de."district", de."revised_estimate_2025_26"
FROM district_expenditure_22353408 de
WHERE de."fiscal_year" = '2025-26' AND de."district" = 'Sindhudurg'
LIMIT {top_k};

Question: 2022-23 ते 2024-25 खर्च ट्रेंड मुंबई उपनगरसाठी
SQL Query: SELECT de."district", 
       de."expenditure_2022_23", 
       de."expenditure_2023_24", 
       de."expenditure_2024_25"
FROM district_expenditure_22353408 de
WHERE de."fiscal_year" = '2025-26' AND de."district" = 'Mumbai Suburban'
LIMIT {top_k};

Question: कोकण विभाग एकूण अर्थसंकल्पीय अनुदान 2025-26
SQL Query: SELECT SUM(de."budget_grant_2025_26") as total_budget
FROM district_expenditure_22353408 de
WHERE de."fiscal_year" = '2025-26'
  AND de."district" IN ('Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg')
  AND de."district" != 'DCO Staff'
LIMIT {top_k};

Question: बजेट अनुदान आणि सुधारित अंदाज तुलना
SQL Query: SELECT de."district", 
       de."budget_grant_2025_26", 
       de."revised_estimate_2025_26",
       (de."revised_estimate_2025_26" - de."budget_grant_2025_26") as difference
FROM district_expenditure_22353408 de
WHERE de."fiscal_year" = '2025-26'
ORDER BY difference DESC
LIMIT {top_k};"""
    },
    table_names={
        'district_expenditure_table': 'district_expenditure_22353408'
    }
)
