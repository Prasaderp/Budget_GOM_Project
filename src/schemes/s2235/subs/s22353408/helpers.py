"""Shared helper utilities for sub-scheme 22353408"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from .config import SCHEME_CONFIG, KONKAN_DISTRICTS
from .models import DistrictExpenditure22353408, SCHEME_CODE, SUB_SCHEME_CODE

from src.schemes.s2235.shared_utils import validate_numeric_input, log_audit_async

def get_allowed_districts_for_user(auth_level: str, auth_unit: str) -> List[str]:
    """Get list of districts user can access based on auth level"""
    if auth_level == "district" and auth_unit:
        return [auth_unit] if auth_unit in KONKAN_DISTRICTS else []
    if auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        return [district_name] if district_name and district_name in KONKAN_DISTRICTS else []
    if auth_level == "dco":
        return KONKAN_DISTRICTS
    return KONKAN_DISTRICTS

def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    """Ensure base rows exist for all configured districts for the given fiscal year."""
    exists = (
        db.query(DistrictExpenditure22353408.id)
        .filter(
            DistrictExpenditure22353408.fiscal_year == fiscal_year,
            DistrictExpenditure22353408.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    rows: List[DistrictExpenditure22353408] = [
        DistrictExpenditure22353408(
            fiscal_year=fiscal_year,
            scheme_code=SCHEME_CODE,
            sub_scheme_code=SUB_SCHEME_CODE,
            district=d,
        )
        for d in KONKAN_DISTRICTS
    ]
    db.bulk_save_objects(rows)
    db.flush()
    from src.core.taluka.provisioning import ensure_contribution_rows
    for d in KONKAN_DISTRICTS:
        ensure_contribution_rows(db, DistrictExpenditure22353408, d, fiscal_year)
    db.commit()

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 22353408"""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

