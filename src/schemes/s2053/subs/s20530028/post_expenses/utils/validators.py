from typing import Tuple, Optional
from ...shared.utils.validators import validate_numeric_inputs, MAX_INPUT_VALUE


def validate_nps_value(value: Optional[str]) -> Tuple[bool, Optional[float], Optional[str]]:
    if value is None or value.strip() == "":
        return True, None, None

    try:
        float_value = float(value)
        if float_value < 0:
            return False, None, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
        if float_value > MAX_INPUT_VALUE:
            return False, None, "मूल्य खूप मोठे आहे"
        return True, float_value, None
    except (ValueError, TypeError):
        return False, None, f"Invalid number format: '{value}'"

