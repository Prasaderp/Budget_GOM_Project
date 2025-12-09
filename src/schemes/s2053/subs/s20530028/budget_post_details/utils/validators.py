"""Validation utilities for budget post details"""
from typing import Tuple
from ...shared.utils.validators import validate_numeric_inputs


def validate_hra_rate(hra_rate: str) -> str:
    """
    Validate and normalize HRA rate
    
    Args:
        hra_rate: HRA rate value (X, Y, or Z)
        
    Returns:
        Validated HRA rate (defaults to 'X' if invalid)
    """
    if hra_rate not in ('X', 'Y', 'Z'):
        return 'X'
    return hra_rate

