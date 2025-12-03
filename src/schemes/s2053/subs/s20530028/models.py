"""Database models for sub-scheme 20530028 - District Administration (Voted)

These models reference the existing shared tables but with scheme-specific defaults.
The actual table structures are in src/models.py for backward compatibility.
"""
from src.models import BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure

# Model references with scheme defaults
SCHEME_CODE = "2053"
SUB_SCHEME_CODE = "20530028"

# Re-export models for scheme-specific use
# These use the shared tables but queries should filter by sub_scheme_code
BudgetPostDetailsModel = BudgetPostDetails
PostStatusModel = PostStatus
PostExpensesModel = PostExpenses
UnitExpenditureModel = UnitExpenditure

# Table name constants for this scheme
BUDGET_POST_DETAILS_TABLE = "budget_post_details"
POST_STATUS_TABLE = "post_status"
POST_EXPENSES_TABLE = "post_expenses"
UNIT_EXPENDITURE_TABLE = "unit_expenditure"

def get_scheme_filter():
    """Returns common filter kwargs for this scheme"""
    return {"sub_scheme_code": SUB_SCHEME_CODE}

