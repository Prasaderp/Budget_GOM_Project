"""Subschema-specific prompt customizations for 20290037"""
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration"""

    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None


PROMPT_CONFIG = PromptConfig(
    custom_context={
        "common_patterns": """- Districts: 'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg'
- Categories: 'Permanent' (NO temporary positions in this sub-scheme)
- Classes: 'Class-1 & 2', 'Class-3', 'Class-4' (only Class-3 has designations)
- Post Status: 'Filled', 'Vacant'
- Designations: 'Head Clerk (Awwal Karkun)', 'Clerk' (only 2 designations, both Class-3)
- Years: 2021_22, 2022_23, 2023_24, 2024_25, 2025_26
- Unit Accounts: '01- Salary', '03- Extra allowance', '06- Telephone, Electricity, Water And Charges', '11- Domestic Travel Expenses', '13- Office Expenses', '14- Lease And Tax', '17- Computer Expenses', '26- Advertising And Publicity Expenses', '51- Motor Vehicles'
- Divisions: Konkan Division = all 7 districts combined""",
        "examples": """Question: What is the basic pay for Head Clerk in Mumbai City?
SQL Query: SELECT bpd."basic_pay", bpd."designation", bpd."district", bpd."category"
FROM budget_post_details_20290037 bpd
WHERE bpd."district" = 'Mumbai City'
  AND bpd."designation" = 'Head Clerk (Awwal Karkun)'
LIMIT {top_k};

Question: Show salary expenditure for Clerk posts in Palghar in 2022-23
SQL Query: SELECT ue."district", ue."unit_account", ue."expenditure_2022_23"
FROM unit_expenditure_20290037 ue
WHERE ue."district" = 'Palghar'
  AND ue."unit_account" = '01- Salary'
LIMIT {top_k};

Question: Total sanctioned posts in Thane district
SQL Query: SELECT SUM(bpd."sanctioned_posts_2024_25" + bpd."sanctioned_posts_2025_26") AS total_posts,
       bpd."district"
FROM budget_post_details_20290037 bpd
WHERE bpd."district" = 'Thane'
GROUP BY bpd."district"
LIMIT {top_k};

Question: Medical expenses for Mumbai City
SQL Query: SELECT pe."district",
       MAX(pe."medical_expenses") AS medical_expenses
FROM post_expenses_20290037 pe
WHERE pe."district" = 'Mumbai City'
GROUP BY pe."district"
LIMIT {top_k};

Question: Show all designations in Class-3 for Mumbai City
SQL Query: SELECT DISTINCT bpd."designation", bpd."class_type", bpd."district"
FROM budget_post_details_20290037 bpd
WHERE bpd."district" = 'Mumbai City'
  AND bpd."class_type" = 'Class-3'
LIMIT {top_k};""",
    },
    table_names={
        "budget_post_details_table": "budget_post_details_20290037",
        "post_status_table": "post_status_20290037",
        "post_expenses_table": "post_expenses_20290037",
        "unit_expenditure_table": "unit_expenditure_20290037",
    },
)
