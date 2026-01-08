"""Shared validation utilities for sub-scheme 20530028"""
from typing import Tuple, Any, Optional

MAX_INPUT_VALUE = 999999999


def validate_numeric_inputs(*values: Any, max_value: int = MAX_INPUT_VALUE) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric inputs are non-negative and within max value
    
    Args:
        *values: Variable number of numeric values to validate
        max_value: Maximum allowed value (default: 999999999)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    for v in values:
        if v is None:
            continue
        if v < 0:
            return False, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
        if v > max_value:
            return False, "मूल्य खूप मोठे आहे"
    return True, None

