"""Subschema-specific prompt customizations for 20450091"""
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
        'common_patterns': """- Districts: 'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg', 'DCO Staff'
- Regular Districts (for division aggregations): 'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg' (excludes DCO Staff)
- DCO Staff: 'DCO Staff' is a separate budget entity - excluded from division-level aggregations
- Categories: 'Permanent', 'Temporary' (case-sensitive)
- Classes: 'Class-1 & 2', 'Class-3', 'Class-4' (use exact format from schema)
- Post Status: 'Filled', 'Vacant'
- Designations: 'Sub-District Officer', 'Head Clerk/Awwal Karkun', 'Cashier', 'Clerk', 'Peon', 'Deputy Commissioner', 'Tehsildar/Tax Collection Officer', 'Naib Tehsildar/Asst Tax Collection Officer', 'Stenographer (Lower Grade)', 'Inspector', 'Vehicle Driver' (use exact English names from schema)
- Years: 2021_22, 2022_23, 2023_24, 2024_25, 2025_26
- Unit Accounts: '01- Salary', '03- Extra allowance', '06- Telephone, Electricity, Water And Charges', etc.
- Divisions: Konkan Division = all 7 regular districts combined (excludes DCO Staff)""",
        
        'examples': """Question: What is the basic pay for Sub-District Officer in Mumbai City?
SQL Query: SELECT bpd."basic_pay", bpd."designation", bpd."district", bpd."category" FROM budget_post_details_20450091 bpd WHERE bpd."district" = 'Mumbai City' AND bpd."designation" = 'Sub-District Officer' LIMIT {top_k};

Question: Show salary expenditure for Palghar in 2022-23
SQL Query: SELECT ue."district", ue."unit_account", ue."expenditure_2022_23" FROM unit_expenditure_20450091 ue WHERE ue."district" = 'Palghar' AND ue."unit_account" = '01- Salary' LIMIT {top_k};

Question: Total filled temporary Class 4 posts in Thane
SQL Query: SELECT SUM(pe."filled_posts") as total_filled, pe."district", pe."category", pe."class_type" FROM post_expenses_20450091 pe WHERE pe."district" = 'Thane' AND pe."category" = 'Temporary' AND pe."class_type" = '4' GROUP BY pe."district", pe."category", pe."class_type";

Question: Medical expenses for Mumbai City
SQL Query: SELECT "district", MAX("medical_expenses") as medical_expenses FROM post_expenses_20450091 WHERE "district" = 'Mumbai City' GROUP BY "district" LIMIT {top_k};"""
    },
    table_names={
        'budget_post_details_table': 'budget_post_details_20450091',
        'post_status_table': 'post_status_20450091',
        'post_expenses_table': 'post_expenses_20450091',
        'unit_expenditure_table': 'unit_expenditure_20450091'
    }
)
