"""Subschema-specific prompt customizations for 76100158 - Public Health Program"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration"""
    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None

# Unified schema pattern (same as 76100149)
PROMPT_CONFIG = PromptConfig(
    custom_context={
        'data_relationships': """- district_expenditure_76100158: District-wise public health program expenditure
  * 3-year expenditure history: 2022-23, 2023-24, 2024-25
  * CRITICAL: budget_estimate (NO year suffix - represents current year/2025-26)
  * CRITICAL: revised_estimate (NO year suffix - represents current year/2025-26)
  * budget_estimate_2026_27 (WITH year suffix - future year projection)
  * COLUMNS:
    - "fiscal_year" (CHAR(7)): e.g. '2025-26'
    - "scheme_code" (VARCHAR): '7610'
    - "sub_scheme_code" (VARCHAR): '76100158'
    - "district" (VARCHAR): District name
    - "expenditure_2022_23", "expenditure_2023_24", "expenditure_2024_25" (BIGINT)
    - "budget_estimate" (BIGINT): NO _2025_26 suffix!
    - "revised_estimate" (BIGINT): NO _2025_26 suffix!
    - "budget_estimate_2026_27" (BIGINT): Future year with suffix
    - "remarks" (VARCHAR): optional notes
  * RELATIONSHIPS:
    - Single-table structure
    - One row per district per fiscal year""",
        
        'common_patterns': """- Districts: Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff
- Marathi to English:
  * जिल्हा → district
  * प्रत्यक्ष खर्च → expenditure
  * अर्थसंकल्पीय अंदाज → budget_estimate (NO _2025_26 suffix!)
  * सुधारित अंदाज → revised_estimate (NO _2025_26 suffix!)
  * अर्थसंकल्पीय अंदाज 2026-27 → budget_estimate_2026_27
  * शेरा → remarks
- Fiscal years: 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Current fiscal year for filtering: '2025-26'""",
        
        'examples': """Question: पालघरचा अर्थसंकल्पीय अंदाज
SQL Query: SELECT de."district", de."budget_estimate"
FROM district_expenditure_76100158 de
WHERE de."fiscal_year" = '2025-26' AND de."district" = 'Palghar'
LIMIT {top_k};

Question: सुधारित अंदाज मुंबई उपनगरासाठी
SQL Query: SELECT de."district", de."revised_estimate"
FROM district_expenditure_76100158 de
WHERE de."fiscal_year" = '2025-26' AND de."district" = 'Mumbai Suburban'
LIMIT {top_k};

Question: 2023-24 चा खर्च सर्व जिल्ह्यांसाठी
SQL Query: SELECT de."district", de."expenditure_2023_24"
FROM district_expenditure_76100158 de
WHERE de."fiscal_year" = '2025-26'
ORDER BY de."expenditure_2023_24" DESC
LIMIT {top_k};"""
    },
    table_names={
        'district_expenditure_table': 'district_expenditure_76100158'
    }
)
