"""Formatting utilities for budget post details"""
from typing import Union


def format_basic_pay(val: Union[int, float, None]) -> Union[int, float]:
    """
    Format basic pay value for display
    
    Args:
        val: Basic pay value (in thousands or full amount)
        
    Returns:
        Formatted value (in thousands)
    """
    if val is None:
        return 0
    fval = float(val)
    if fval >= 1000:
        fval = round(round(fval / 100) / 10, 1)
    return int(fval) if fval == int(fval) else fval

