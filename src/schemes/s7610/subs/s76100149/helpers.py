"""Shared helper utilities for sub-scheme 76100149"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status
from concurrent.futures import ThreadPoolExecutor
import os

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from .config import SCHEME_CONFIG, KONKAN_DISTRICTS
from .models import DistrictExpenditure76100149, SCHEME_CODE, SUB_SCHEME_CODE

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s76100149")

MAX_INPUT_VALUE = 999_999_999_999

def get_allowed_districts_for_user(auth_level: str, auth_unit: str) -> List[str]:
    """Get list of districts user can access based on auth level"""
    if auth_level == "district" and auth_unit:
        return [auth_unit] if auth_unit in KONKAN_DISTRICTS else []
    if auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        return [district_name] if district_name and district_name in KONKAN_DISTRICTS else []
    if auth_level == "dco":
        return KONKAN_DISTRICTS
    return []


def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    """Ensure base rows exist for all configured districts for the given fiscal year."""
    exists = (
        db.query(DistrictExpenditure76100149.id)
        .filter(
            DistrictExpenditure76100149.fiscal_year == fiscal_year,
            DistrictExpenditure76100149.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    rows: List[DistrictExpenditure76100149] = [
        DistrictExpenditure76100149(
            fiscal_year=fiscal_year,
            scheme_code=SCHEME_CODE,
            sub_scheme_code=SUB_SCHEME_CODE,
            district=d,
        )
        for d in KONKAN_DISTRICTS
    ]
    db.bulk_save_objects(rows)
    db.commit()

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 76100149"""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)


def validate_numeric_input(value: Optional[str], field_name: str = "field") -> int:
    """Validate and parse numeric input from form. Returns parsed int or raises HTTPException"""
    if value in (None, ""):
        return 0
    try:
        val = int(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid value for {field_name}"
        )
    if val < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Negative values not allowed for {field_name}"
        )
    if val > MAX_INPUT_VALUE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value too large for {field_name}"
        )
    return val

def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str],
    action: str = "UPDATE"
):
    """Async audit logging using thread pool"""
    def _log():
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from src.models import AuditLog
            
            db_url = os.getenv("DATABASE_URL", "")
            if not db_url:
                return
            
            engine = create_engine(db_url, pool_pre_ping=True, pool_size=1)
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                changed = [
                    {"field": k, "old": old_vals.get(k), "new": new_vals.get(k)}
                    for k in set(old_vals) | set(new_vals)
                    if old_vals.get(k) != new_vals.get(k)
                ]
                if not changed:
                    return
                
                entry = AuditLog(
                    table_name=table,
                    record_id=record_id,
                    action=action,
                    username=username,
                    user_level=req_info.get('level', ''),
                    user_role=req_info.get('role', ''),
                    user_unit=req_info.get('unit', ''),
                    old_values=old_vals,
                    new_values=new_vals,
                    changed_fields=changed,
                    ip_address=req_info.get('ip', ''),
                    user_agent=req_info.get('ua', ''),
                    session_id=req_info.get('sid', '')
                )
                session.add(entry)
                session.commit()
            finally:
                session.close()
                engine.dispose()
        except Exception:
            pass
    
    _audit_executor.submit(_log)

