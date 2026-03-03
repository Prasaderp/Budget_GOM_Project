"""Validation utilities for unit expenditure"""
from typing import Tuple, Optional
from ...shared.utils.validators import validate_numeric_inputs


def validate_unit_expenditure_inputs(
    expenditure_prev4: int = 0,
    expenditure_prev3: int = 0,
    expenditure_prev2: int = 0,
    budget_prev1: int = 0,
    forecast_prev1: int = 0,
    budget_curr_estimating_officer: int = 0,
    budget_curr_controlling_officer: int = 0,
    budget_curr_admin_dept: int = 0,
    budget_curr_finance_dept: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Validate unit expenditure numeric inputs
    
    Returns:
        tuple: (is_valid, error_message)
    """
    return validate_numeric_inputs(
        expenditure_prev4,
        expenditure_prev3,
        expenditure_prev2,
        budget_prev1,
        forecast_prev1,
        budget_curr_estimating_officer,
        budget_curr_controlling_officer,
        budget_curr_admin_dept,
        budget_curr_finance_dept
    )

