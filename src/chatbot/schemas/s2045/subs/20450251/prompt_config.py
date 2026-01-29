"""Subschema-specific prompt customizations for 20450251."""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration"""
    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None

# Custom context with subschema-specific details for 20450251
PROMPT_CONFIG = PromptConfig(
    custom_context={
        'common_patterns': """- Districts (5 Konkan - NO MUMBAI): 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg'
- CRITICAL: This scheme does NOT include Mumbai City or Mumbai Suburban
- Scheme: 2045 0251 - महा. शिक्षण उपकर अधि कलम 23 अन्वये ग्रामपंचायतीना प्रदाने (Education Cess Grants to Village Panchayats)
- Single table structure: district_expenditure_20450251
- Expenditure columns: expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 (BIGINT)
- Budget columns: budget_estimate_2025_26, quarterly_expenditure_apr_jul_2025, budget_estimate_2026_27 (BIGINT)
- All amounts in Indian Rupees (₹), stored as BIGINT
- Fiscal year filter: fiscal_year = '2025-26'
- For totals: use SUM() aggregation across 5 districts (no Mumbai)""",
        
        'examples': """Question: What is the budget estimate for Thane in 2026-27?
SQL Query: SELECT district, budget_estimate_2026_27 FROM district_expenditure_20450251 WHERE fiscal_year = '2025-26' AND district = 'Thane' LIMIT {top_k};

Question: Show total expenditure for 2023-24 across all districts
SQL Query: SELECT SUM(expenditure_2023_24) as total FROM district_expenditure_20450251 WHERE fiscal_year = '2025-26';

Question: Compare expenditure for Palghar across all years
SQL Query: SELECT district, expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 FROM district_expenditure_20450251 WHERE fiscal_year = '2025-26' AND district = 'Palghar' LIMIT {top_k};

Question: Quarterly expenditure for Raigad
SQL Query: SELECT district, quarterly_expenditure_apr_jul_2025 FROM district_expenditure_20450251 WHERE fiscal_year = '2025-26' AND district = 'Raigad' LIMIT {top_k};"""
    },
    table_names={
        'district_expenditure_table': 'district_expenditure_20450251'
    }
)
