"""Validators for Post Status module"""
from typing import Tuple, Optional
from ...shared.utils.validators import MAX_INPUT_VALUE


def validate_post_status_inputs(
    posts: Optional[int] = None,
    salary: Optional[int] = None,
    grade_pay: Optional[int] = None,
    special_pay: Optional[int] = None,
    dearness_allowance: Optional[int] = None,
    local_supplementary_allowance: Optional[int] = None,
    house_rent_allowance: Optional[int] = None,
    travel_allowance: Optional[int] = None,
    other: Optional[int] = None,
    max_value: int = MAX_INPUT_VALUE
) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric inputs are non-negative and within max value
    
    Returns:
        tuple: (is_valid, error_message)
    """
    values = [
        posts, salary, grade_pay, special_pay, dearness_allowance,
        local_supplementary_allowance, house_rent_allowance,
        travel_allowance, other
    ]
    
    if any(v is not None and v < 0 for v in values):
        return False, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
    
    if any(v is not None and v > max_value for v in values):
        return False, "मूल्य खूप मोठे आहे"
    
    return True, None

