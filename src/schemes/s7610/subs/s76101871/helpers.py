"""Helper utilities for sub-scheme 76101871.

Uses shared utilities from parent scheme and centralized AuditService.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

from src.schemes.s7610.shared_helpers import (
    get_allowed_districts_for_user as _get_allowed_districts,
    check_edit_permission_for_scheme as _check_edit_permission,
    validate_numeric_input,
    KONKAN_DISTRICTS,
    MAX_INPUT_VALUE,
)
from src.utils_district import validate_access_control, get_request_info
from .config import SCHEME_CONFIG
from .models import DistrictExpenditure76101871, SCHEME_CODE, SUB_SCHEME_CODE


def get_allowed_districts_for_user(auth_level: str, auth_unit: str) -> List[str]:
    """Get list of districts user can access based on auth level."""
    return _get_allowed_districts(auth_level, auth_unit, KONKAN_DISTRICTS)


def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    """Ensure base rows exist for all configured districts for the given fiscal year."""
    exists = (
        db.query(DistrictExpenditure76101871.id)
        .filter(DistrictExpenditure76101871.fiscal_year == fiscal_year, DistrictExpenditure76101871.sub_scheme_code == SUB_SCHEME_CODE)
        .limit(1).first()
    )
    if exists:
        return
    rows = [
        DistrictExpenditure76101871(fiscal_year=fiscal_year, scheme_code=SCHEME_CODE, sub_scheme_code=SUB_SCHEME_CODE, district=d)
        for d in KONKAN_DISTRICTS
    ]
    db.bulk_save_objects(rows)
    db.commit()


def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Check if user has permission to edit scheme data."""
    return _check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)


def log_audit_async(
    table: str, record_id: int, username: str, 
    old_vals: Dict[str, Any], new_vals: Dict[str, Any], 
    req_info: Dict[str, str], action: str = "UPDATE"
) -> None:
    """Synchronous audit logging implementation."""
    from src.models import AuditLog
    from src.database import SessionLocal
    import logging
    logger = logging.getLogger(__name__)
    
    changed = [
        {"field": k, "old": old_vals.get(k), "new": new_vals.get(k)}
        for k in set(old_vals) | set(new_vals)
        if old_vals.get(k) != new_vals.get(k)
    ]
    if not changed and action == "UPDATE":
        return
    
    try:
        with SessionLocal() as db:
            entry = AuditLog(
                table_name=table, record_id=record_id, action=action,
                username=username,
                user_level=req_info.get("level", ""),
                user_role=req_info.get("role", ""),
                user_unit=req_info.get("unit", ""),
                old_values=old_vals, new_values=new_vals, changed_fields=changed,
                ip_address=req_info.get("ip", ""),
                user_agent=req_info.get("ua", ""),
                session_id=req_info.get("sid", "")
            )
            db.add(entry)
            db.commit()
    except Exception as e:
        logger.error(f"Audit log failed: {e}", exc_info=True)
