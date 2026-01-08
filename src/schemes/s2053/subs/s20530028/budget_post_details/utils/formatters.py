"""Formatting utilities for budget post details"""
from typing import Union


def format_basic_pay(val: Union[int, float, None]) -> Union[int, float]:
    """
    Format basic pay from DB (thousands) for UI display
    
    Args:
        val: Basic pay in thousands (180 = ₹180,000)
        
    Returns:
        Formatted value in thousands for display
    """
    if val is None:
        return 0
    fval = float(val)
    return int(fval) if fval == int(fval) else fval
