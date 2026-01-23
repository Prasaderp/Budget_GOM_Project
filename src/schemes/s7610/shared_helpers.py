"""Shared utilities for scheme 7610 sub-schemes.

Provides common functions across all 76100149, 76100158, 76100167, 76101871 sub-schemes.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.config import DCO_STAFF_IDENTIFIER, DISTRICTS
from src.utils_district import get_district_from_taluka, check_edit_permission

MAX_INPUT_VALUE = 999_999_999_999
KONKAN_DISTRICTS = DISTRICTS


def get_allowed_districts_for_user(auth_level: str, auth_unit: str, districts: List[str] = KONKAN_DISTRICTS) -> List[str]:
    """Get list of districts user can access based on auth level."""
    if auth_level == "district" and auth_unit:
        return [auth_unit] if auth_unit in districts else []
    if auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        return [district_name] if district_name and district_name in districts else []
    if auth_level == "dco":
        return districts
    return []


def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session, scheme_code: str) -> bool:
    """Unified permission check for scheme."""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, scheme_code)


def validate_numeric_input(value: Optional[str], field_name: str = "field") -> int:
    """Validate and parse numeric input from form. Returns parsed int or raises HTTPException."""
    if value in (None, ""):
        return 0
    try:
        val = int(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid value for {field_name}")
    if val < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Negative values not allowed for {field_name}")
    if val > MAX_INPUT_VALUE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Value too large for {field_name}")
    return val
