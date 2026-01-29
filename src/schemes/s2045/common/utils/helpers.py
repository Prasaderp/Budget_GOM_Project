"""Shared helper utilities for s2045 subschemes"""
from typing import Dict, Optional, Tuple
from fastapi import Request

MAX_INPUT_VALUE = 999999999

def get_no_cache_headers() -> Dict[str, str]:
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

def validate_numeric_inputs(*values, max_value: int = MAX_INPUT_VALUE) -> Tuple[bool, Optional[str]]:
    if any(v < 0 for v in values if v is not None):
        return False, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
    if any(v > max_value for v in values if v is not None):
        return False, "मूल्य खूप मोठे आहे"
    return True, None
