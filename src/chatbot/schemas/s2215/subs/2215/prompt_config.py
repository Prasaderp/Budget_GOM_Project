"""Subschema-specific prompt customizations for 2215 (Water Scarcity)."""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration."""

    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None


PROMPT_CONFIG = PromptConfig(
    custom_context={
        "data_relationships": """- district_expenditure_2215: Single-table district-wise expenditure and budget data for scheme 2215 (Water Scarcity).
  * GRAIN: Each row represents a single (fiscal_year, account_head_code, district) combination scoped to sub_scheme_code = '2215'.
  * KEY COLUMNS:
    - "fiscal_year" (CHAR(7)): e.g. '2025-26'
    - "scheme_code": always '2215'
    - "sub_scheme_code": always '2215'
    - "account_head_code": e.g. '2215A195', '2215A201'
    - "district": district office name (e.g., 'Chief Executive Officer, Zilla Parishad Thane', 'Collector Palghar')
  * FINANCIAL COLUMNS:
    - "expenditure_YYYY_YY": actual expenditure for past years
    - "budget_estimate_YYYY_YY": budget estimate for that year
    - "revised_demand_YYYY_YY": revised demand for that year
    - "budget_estimate_YYYY_YY": budget estimate for next year
  * RELATIONSHIPS:
    - No posts, classes, categories, or designations in this schema.
    - Analysis is always over districts, account_head_code, and fiscal_year / year columns.""",
        "common_patterns": """- Valid Konkan districts (base names): 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg'.
- District office names in the table are full titles, e.g. 'Chief Executive Officer, Zilla Parishad Thane', 'Collector Palghar'.
- Account heads:
  * '2215A195' - Zilla Parishad Water Scarcity relief grants (Konkan districts).
  * '2215A201' - Urban Water Scarcity relief (Collectors for Konkan districts).
- Grouping patterns:
  * Totals per district for a given account_head_code and fiscal_year:
    GROUP BY "district" (and optionally "account_head_code").
  * Totals per account_head_code across all Konkan districts:
    GROUP BY "account_head_code" (and optionally "fiscal_year").
  * Division (Konkan) totals:
    SUM across all relevant districts; do not use any special 'Total-Konkan Division' row unless present in schema_info.
- Filtering:
  * Use exact district names from context; do not invent districts.
  * Filter by "account_head_code" when a specific head is mentioned in the question.
  * Use "fiscal_year" plus the appropriate expenditure/budget columns for the years being compared.
- Value characteristics:
  * All financial columns are large non-negative integers; treat NULL as zero when aggregating (use COALESCE).
- Marathi to English mapping (UI terms):
  * "लेखाशिर्ष" → account head
  * "जिल्हा कार्यालय" → district office
  * "प्रत्यक्ष रक्कमा/खर्च" → expenditure
  * "अर्थसंकल्पीय अंदाजपत्रक" → budget estimate
  * "सुधारीत अंदाजपत्रक मागणी" → revised demand
  * "कोंकण विभाग" → Konkan Division
  * "एकूण-कोकण विभाग" → Total Konkan Division
  * Years like "२०२५-२६" → 2025-26""",
        "examples": """Question: What is the expenditure for account head 2215A195 in Palghar?
SQL Query: SELECT
  de."district",
  de."account_head_code",
  de."expenditure_YYYY_YY"
FROM district_expenditure_2215 de
WHERE de."sub_scheme_code" = '2215'
  AND de."account_head_code" = '2215A195'
  AND de."district" ILIKE '%Palghar%'
  AND de."fiscal_year" = 'YYYY-YY'
LIMIT {top_k};

Question: 2215A201 साठी कोंकण विभागाचा प्रत्यक्ष खर्च किती आहे?
SQL Query: SELECT
  de."account_head_code",
  SUM(de."expenditure_YYYY_YY") AS total_expenditure
FROM district_expenditure_2215 de
WHERE de."sub_scheme_code" = '2215'
  AND de."account_head_code" = '2215A201'
  AND de."district" IN ('Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg')
GROUP BY de."account_head_code"
LIMIT {top_k};

Question: लेखाशिर्ष 2215A195 साठी ठाणे जिल्हा बजेट अंदाज आणि सुधारीत मागणी तुलना
SQL Query: SELECT
  de."district",
  de."account_head_code",
  de."budget_estimate_YYYY_YY",
  de."revised_demand_YYYY_YY"
FROM district_expenditure_2215 de
WHERE de."sub_scheme_code" = '2215'
  AND de."account_head_code" = '2215A195'
  AND de."district" ILIKE '%Thane%'
  AND de."fiscal_year" = 'YYYY-YY'
LIMIT {top_k};

Question: कोंकण विभागासाठी बजेट अंदाज (2215A201)
SQL Query: SELECT
  de."district",
  de."account_head_code",
  de."budget_estimate_YYYY_YY"
FROM district_expenditure_2215 de
WHERE de."sub_scheme_code" = '2215'
  AND de."account_head_code" = '2215A201'
  AND de."fiscal_year" = 'YYYY-YY'
ORDER BY de."district"
LIMIT {top_k};""",
    },
    table_names=None,
)


