"""Validators for post expenses input"""
from typing import Tuple, Optional
from ...shared.utils.validators import validate_numeric_inputs, MAX_INPUT_VALUE


def validate_nps_value(value: Optional[str]) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate and convert NPS value from string to float
    
    Returns:
        tuple: (is_valid, float_value, error_message)
    """
    if value is None or value.strip() == "":
        return True, None, None
    
    try:
        float_value = float(value)
        if float_value < 0:
            return False, None, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
        return True, float_value, None
    except (ValueError, TypeError):
        return False, None, f"Invalid number format: '{value}'"

