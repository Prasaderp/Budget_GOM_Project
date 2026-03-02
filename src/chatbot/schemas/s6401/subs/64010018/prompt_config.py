from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PromptConfig:
    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None

PROMPT_CONFIG = PromptConfig(
    custom_context={
        "data_relationships": """- district_expenditure_64010018: Single-table district-wise expenditure and budget data for scheme 64010018 (Loans for Crop Husbandry).
  * GRAIN: Each row represents a single (fiscal_year, sub_scheme_code, district) combination.
  * KEY COLUMNS:
    - "fiscal_year" (CHAR(7)): e.g. '2025-26'
    - "scheme_code": always '6401'
    - "sub_scheme_code": always '64010018'
    - "district": exact match for one of the 5 Konkan districts.
  * FINANCIAL COLUMNS:
    - "expenditure_YYYY_YY": actual expenditure for past years
    - "budget_grant_YYYY_YY": budget grant for that year
    - "revised_estimate_YYYY_YY": revised estimate for that year
    - "budget_estimate_YYYY_YY": budget estimate for next year
  * RELATIONSHIPS:
    - No posts, classes, categories, or designations in this schema.
    - Analysis is always over districts and fiscal_year / year columns.""",
        "common_patterns": """- Valid Konkan districts: 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg'.
- Grouping patterns:
  * Totals per district for a given fiscal_year:
    GROUP BY "district".
  * Division (Konkan) totals:
    SUM across all relevant districts; do not use any special 'Total' row unless present in schema_info.
- Filtering:
  * Use exact district names from context; do not invent districts.
  * Use "fiscal_year" plus the appropriate expenditure/budget columns for the years being compared.
- Value characteristics:
  * All financial columns are large non-negative integers; treat NULL as zero when aggregating (use COALESCE).
- Marathi to English mapping (UI terms):
  * "जिल्हा" → district
  * "पीक उत्पादन" → crop production
  * "कर्जे" → loans
  * "कोंकण विभाग" → Konkan Division
  * Years like "२०२५-२६" → 2025-26""",
        "examples": """Question: What is the expenditure for crop loans in Palghar?
SQL Query: SELECT de."district", de."expenditure_YYYY_YY" FROM district_expenditure_64010018 de WHERE de."district" ILIKE '%Palghar%' AND de."fiscal_year" = 'YYYY-YY' LIMIT {top_k};

Question: ठाणे जिल्हाचे पीक कर्ज बजेट किती आहे?
SQL Query: SELECT de."district", de."budget_grant_YYYY_YY" FROM district_expenditure_64010018 de WHERE de."district" ILIKE '%Thane%' AND de."fiscal_year" = 'YYYY-YY' LIMIT {top_k};""",
    },
    table_names=None,
)
