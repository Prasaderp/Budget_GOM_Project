"""Validators module for input validation."""
from typing import Tuple


def validate_numeric_inputs(*values) -> Tuple[bool, str]:
    """Validate numeric inputs are non-negative."""
    for val in values:
        if val is None:
            continue
        try:
            num_val = float(val)
            if num_val < 0:
                return False, "Negative values are not allowed"
        except (ValueError, TypeError):
            return False, f"Invalid numeric value: {val}"

    return True, ""
