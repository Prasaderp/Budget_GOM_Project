"""Subschema-specific prompt customizations for 20750249."""
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration."""

    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None


# Custom context with subschema-specific details for single-table sub-head expenditure.
PROMPT_CONFIG = PromptConfig(
    custom_context={
        "data_relationships": """- sub_head_expenditure_20750249: Single-table sub-head/minor-head expenditure for scheme 2075, sub-scheme 20750249.
  * GRAIN: Each row represents a single (fiscal_year, sub_head) combination scoped to this sub-scheme (sub_scheme_code = '20750249').
  * COLUMNS:
    - "fiscal_year" (CHAR(7)): e.g. '2025-26'
    - "scheme_code" (VARCHAR): always '2075' for this table
    - "sub_scheme_code" (VARCHAR): always '20750249'
    - "sub_head" (VARCHAR): descriptive Marathi sub-head text
    - "expenditure_2022_23", "expenditure_2023_24", "expenditure_2024_25" (BIGINT): actual expenditure for past years
    - "budget_estimate" (BIGINT): current budget estimate
    - "revised_estimate" (BIGINT): current revised estimate
    - "budget_estimate_2026_27" (BIGINT): projected BE for 2026-27
    - "remarks" (VARCHAR): optional explanatory note
  * RELATIONSHIPS:
    - There are NO district, category, class, or designation columns.
    - Analysis is always over sub-heads and fiscal years only.""",
        "common_patterns": """- Scope: This subscheme is DCO-only, with no district-wise breakdown.
- Use only columns from sub_head_expenditure_20750249; do NOT reference 2053-style tables.
- Grouping:
  * For totals per sub-head: GROUP BY "sub_head" (and optionally "fiscal_year").
  * For year-wise trends: GROUP BY "fiscal_year" and/or "sub_head".
- Aggregations:
  * Use SUM() over expenditure or estimate columns when combining multiple sub-heads.
  * Use COALESCE(column, 0) when you need to treat NULL as zero.
- Filtering:
  * Filter by "fiscal_year" when the question specifies a year like 2025-26.
  * Filter by "sub_head" using ILIKE '%...%' when the question mentions partial text.
- Important:
  * There are no district, category, or class constraints; never invent such filters.
  * All queries must stay within sub_head_expenditure_20750249.
- Marathi to English mapping (UI terms):
  * "उपशिर्ष / गौणशिर्ष" → sub head
  * "प्रत्यक्ष खर्च" / "खर्च" → expenditure
  * "अर्थसंकल्पीय अंदाज" → budget estimate
  * "सुधारीत अंदाज" → revised estimate
  * "शेरा" → remarks
  * Years like "२०२५-२६" → 2025-26""",
        "examples": """Question: Show all sub-heads with their 2024-25 expenditure and budget estimates for 2025-26.
SQL Query: SELECT
  she."sub_head",
  she."expenditure_2024_25",
  she."budget_estimate",
  she."revised_estimate"
FROM sub_head_expenditure_20750249 she
WHERE she."fiscal_year" = '2025-26'
ORDER BY she."sub_head"
LIMIT {top_k};

Question: उपशिर्ष नुसार प्रत्यक्ष खर्च 2023-24 दाखवा
SQL Query: SELECT
  she."sub_head",
  she."expenditure_2023_24"
FROM sub_head_expenditure_20750249 she
WHERE she."fiscal_year" = '2025-26'
ORDER BY she."sub_head"
LIMIT {top_k};

Question: अर्थसंकल्पीय अंदाज 2025-26 आणि सुधारीत अंदाज तुलना करा
SQL Query: SELECT
  she."sub_head",
  she."budget_estimate",
  she."revised_estimate"
FROM sub_head_expenditure_20750249 she
WHERE she."fiscal_year" = '2025-26'
ORDER BY she."sub_head"
LIMIT {top_k};

Question: Total expenditure in 2022-23 across all sub-heads for this sub-scheme.
SQL Query: SELECT
  SUM(she."expenditure_2022_23") AS total_expenditure_2022_23
FROM sub_head_expenditure_20750249 she
WHERE she."sub_scheme_code" = '20750249'
LIMIT {top_k};

Question: List sub-heads where revised estimate is higher than budget estimate.
SQL Query: SELECT
  she."sub_head",
  she."budget_estimate",
  she."revised_estimate"
FROM sub_head_expenditure_20750249 she
WHERE she."revised_estimate" > she."budget_estimate"
  AND she."fiscal_year" = '2025-26'
ORDER BY she."revised_estimate" - she."budget_estimate" DESC
LIMIT {top_k};""",
    },
    table_names={
        # Map all logical tables used by the base prompt to this single physical table
        "budget_post_details_table": "sub_head_expenditure_20750249",
        "post_status_table": "sub_head_expenditure_20750249",
        "post_expenses_table": "sub_head_expenditure_20750249",
        "unit_expenditure_table": "sub_head_expenditure_20750249",
    },
)


