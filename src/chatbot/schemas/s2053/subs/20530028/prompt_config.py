"""Subschema-specific prompt customizations for 20530028"""
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
- DCO Staff: 'DCO Staff' is a separate budget entity - excluded from division-level aggregations and reports like संवर्गनिहाय माहिती and जिल्हानिहाय गोषवारा
- Categories: 'Permanent', 'Temporary' (case-sensitive)
- Classes: 'Class-1 & 2', 'Class-3', 'Class-4' (use exact format from schema)
- Post Status: 'Filled', 'Vacant'
- Designations: 'Collector', 'Tehsildar', 'Deputy Collector', 'Assistant Collector', 'Naib Tehsildar', 'Accounts Officer', 'Clerk', 'Vehicle Driver', 'Peon', etc. (use exact English names from schema)
- Years: 2021_22, 2022_23, 2023_24, 2024_25, 2025_26
- Unit Accounts: '01- Salary', '02- Medical', '03- Dearness Allowance', 'Computer', 'Festival Advance', etc.
- Divisions: Konkan Division = all 7 regular districts combined (excludes DCO Staff), Mumbai Division = Mumbai City + Mumbai Suburban
- Marathi to English mapping: 'जिल्हाधिकारी' → 'Collector', 'लिपिक' → 'Clerk', 'वाहन चालक' → 'Vehicle Driver', 'शिपाई' → 'Peon'""",
        
        'examples': """Question: What is the basic pay for Collector in Mumbai City?
SQL Query: SELECT bpd."basic_pay", bpd."designation", bpd."district", bpd."category" FROM budget_post_details_20530028 bpd WHERE bpd."district" = 'Mumbai City' AND bpd."designation" = 'Collector' LIMIT {top_k};

Question: Show salary expenditure for Palghar in 2022-23
SQL Query: SELECT ue."district", ue."unit_account", ue."expenditure_2022_23" FROM unit_expenditure_20530028 ue WHERE ue."district" = 'Palghar' AND ue."unit_account" = '01- Salary' LIMIT {top_k};

Question: Total filled temporary Class 4 posts in Thane
SQL Query: SELECT SUM(pe."filled_posts") as total_filled, pe."district", pe."category", pe."class_type" FROM post_expenses_20530028 pe WHERE pe."district" = 'Thane' AND pe."category" = 'Temporary' AND pe."class_type" = '4' GROUP BY pe."district", pe."category", pe."class_type";

Question: How many vacant posts in Mumbai Suburban?
SQL Query: SELECT SUM(pe."vacant_posts") as total_vacant, pe."district" FROM post_expenses_20530028 pe WHERE pe."district" = 'Mumbai Suburban' GROUP BY pe."district";

Question: Total number of posts of Collector in Thane district
SQL Query: SELECT SUM(bpd."sanctioned_posts_2024_25" + bpd."sanctioned_posts_2025_26") as total_posts, bpd."district", bpd."designation" FROM budget_post_details_20530028 bpd WHERE bpd."district" = 'Thane' AND bpd."designation" = 'Collector' GROUP BY bpd."district", bpd."designation" LIMIT {top_k};

Question: Medical expenses for Mumbai City
SQL Query: SELECT "district", MAX("medical_expenses") as medical_expenses FROM post_expenses_20530028 WHERE "district" = 'Mumbai City' GROUP BY "district" LIMIT {top_k};

Question: जिल्हाधिकारी posts in Mumbai City
SQL Query: SELECT SUM("sanctioned_posts_2024_25" + "sanctioned_posts_2025_26") as total_posts, "district", "designation" FROM budget_post_details_20530028 WHERE "district" = 'Mumbai City' AND "designation" = 'Collector' GROUP BY "district", "designation" LIMIT {top_k};

Question: Give the districtwise data of Class-3 employees of Konkan Division
SQL Query: SELECT bpd."district", bpd."designation", bpd."category", bpd."sanctioned_posts_2024_25", bpd."basic_pay" FROM budget_post_details_20530028 bpd WHERE bpd."class_type" = 'Class-3' AND bpd."district" IN ('Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg') AND bpd."district" != 'DCO Staff' ORDER BY bpd."district", bpd."designation" LIMIT 100;"""
    },
    table_names={
        'budget_post_details_table': 'budget_post_details_20530028',
        'post_status_table': 'post_status_20530028',
        'post_expenses_table': 'post_expenses_20530028',
        'unit_expenditure_table': 'unit_expenditure_20530028'
    }
)

