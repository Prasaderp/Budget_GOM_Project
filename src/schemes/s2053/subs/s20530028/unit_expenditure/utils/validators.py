"""Validation utilities for unit expenditure"""
from typing import Tuple, Optional
from ...shared.utils.validators import validate_numeric_inputs


def validate_unit_expenditure_inputs(
    expenditure_2021_22: int = 0,
    expenditure_2022_23: int = 0,
    expenditure_2023_24: int = 0,
    budget_2024_25: int = 0,
    forecast_2024_25: int = 0,
    budget_2025_26_estimating_officer: int = 0,
    budget_2025_26_controlling_officer: int = 0,
    budget_2025_26_admin_dept: int = 0,
    budget_2025_26_finance_dept: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Validate unit expenditure numeric inputs
    
    Returns:
        tuple: (is_valid, error_message)
    """
    return validate_numeric_inputs(
        expenditure_2021_22,
        expenditure_2022_23,
        expenditure_2023_24,
        budget_2024_25,
        forecast_2024_25,
        budget_2025_26_estimating_officer,
        budget_2025_26_controlling_officer,
        budget_2025_26_admin_dept,
        budget_2025_26_finance_dept
    )

