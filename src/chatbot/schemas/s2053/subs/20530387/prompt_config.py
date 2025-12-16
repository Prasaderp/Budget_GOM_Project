"""Subschema-specific prompt customizations for 20530387"""
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration"""

    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None


# Custom context with subschema-specific details
PROMPT_CONFIG = PromptConfig(
    custom_context={
        "common_patterns": """- Pseudo-districts: 'DCO Main Office', 'DCO Staff' (no regular Konkan districts)
- NOTE: This subscheme only contains DCO-level data; it should not be used for district-wise or division-wise aggregations for Konkan Division.
- Categories: 'Permanent', 'Temporary' (case-sensitive)
- Classes: 'Class-1 & 2', 'Class-3', 'Class-4' (use exact format from schema)
- Post Status: 'Filled', 'Vacant'
- Example Designations (Class-1 & 2): 'Divisional Commissioner', 'Additional Commissioner', 'Tehsildar', 'Naib Tehsildar', 'Deputy Commissioner', 'Deputy Collector', 'Assistant Director Town Planning', 'Assistant Director', 'Accounts Officer', 'Assistant Accounts Officer', 'Law Officer (Honorarium)'
- Example Designations (Class-3): 'Stenographer (Higher)', 'Head Clerk (Awwal Karkun)', 'Clerk-Typist', 'Sub-Accountant', 'Stenographer (Selection Grade)', 'Stenographer (Lower)', 'Cashier/Senior Pay Scale', 'Vehicle Driver', 'Sanitation Inspector'
- Example Designations (Class-4): 'Peon/Naik/Havaldar', 'Watchman/Guard', 'Lift Operator', 'Porter', 'Sweeper/Cleaner', 'Worker', 'Laborer'
- Years: 2021_22, 2022_23, 2023_24, 2024_25, 2025_26
- Unit Accounts: '01- Salary', '03- Extra allowance', '06- Telephone, Electricity, Water And Charges', '10- Contractual Services', '11- Domestic Travel Expenses', '13- Office Expenses', '14- Lease And Tax', '16- Publications', '17- Computer Expenses', '20- Other Administrative Expenses', '24- Fuel Costs', '26- Advertising And Publicity Expenses', '36- Small Construction', '50- Other Expenses', '51- Motor Vehicles'
- IMPORTANT: For this subscheme, \"district\" column values are only 'DCO Main Office' and 'DCO Staff'. Do not expect regular districts like 'Mumbai City' here.""",
        "examples": """Question: What is the basic pay for Divisional Commissioner in DCO Main Office?
SQL Query: SELECT bpd."basic_pay", bpd."designation", bpd."district", bpd."category"
FROM budget_post_details_20530387 bpd
WHERE bpd."district" = 'DCO Main Office'
  AND bpd."designation" = 'Divisional Commissioner'
LIMIT {top_k};

Question: Show salary expenditure for DCO Staff in 2022-23
SQL Query: SELECT ue."district", ue."unit_account", ue."expenditure_2022_23"
FROM unit_expenditure_20530387 ue
WHERE ue."district" = 'DCO Staff'
  AND ue."unit_account" = '01- Salary'
LIMIT {top_k};

Question: Total sanctioned Class-3 posts in DCO Main Office
SQL Query: SELECT SUM(bpd."sanctioned_posts_2024_25" + bpd."sanctioned_posts_2025_26") AS total_posts,
       bpd."district",
       bpd."class_type"
FROM budget_post_details_20530387 bpd
WHERE bpd."district" = 'DCO Main Office'
  AND bpd."class_type" = 'Class-3'
GROUP BY bpd."district", bpd."class_type"
LIMIT {top_k};

Question: Medical expenses for DCO Staff
SQL Query: SELECT pe."district",
       MAX(pe."medical_expenses") AS medical_expenses
FROM post_expenses_20530387 pe
WHERE pe."district" = 'DCO Staff'
GROUP BY pe."district"
LIMIT {top_k};""",
    },
    table_names={
        "budget_post_details_table": "budget_post_details_20530387",
        "post_status_table": "post_status_20530387",
        "post_expenses_table": "post_expenses_20530387",
        "unit_expenditure_table": "unit_expenditure_20530387",
    },
)


