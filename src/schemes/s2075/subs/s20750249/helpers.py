"""Shared helper utilities for sub-scheme 20750249"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status
from concurrent.futures import ThreadPoolExecutor
import os

from src.utils_district import check_edit_permission
from .config import SCHEME_CONFIG
from .models import SubHeadExpenditure20750249, SCHEME_CODE, SUB_SCHEME_CODE

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s20750249")

MAX_INPUT_VALUE = 999_999_999_999


def check_dco_access(auth_level: str) -> bool:
    """Check if user has DCO level access (only DCO can access this scheme)"""
    return auth_level == "dco"


def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    """Ensure fixed row exists for the given fiscal year."""
    exists = (
        db.query(SubHeadExpenditure20750249.id)
        .filter(
            SubHeadExpenditure20750249.fiscal_year == fiscal_year,
            SubHeadExpenditure20750249.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    row = SubHeadExpenditure20750249(
        fiscal_year=fiscal_year,
        scheme_code=SCHEME_CODE,
        sub_scheme_code=SUB_SCHEME_CODE,
        sub_head='मागणी क्र.सी-4-2075- संकिर्ण-सर्वसाधारण सेवा 101 (01) इनामदार व इतर अनुदानग्राही 04-निवृत्ती वेतने-(00) (01) आयुक्त कोकण (20750249)',
    )
    db.add(row)
    db.commit()


def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 20750249 - only DCO main assistant"""
    if not check_dco_access(auth_level):
        return False
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


def get_request_info(request: Request) -> Dict[str, str]:
    """Extract request information for audit logging"""
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return {
        "level": request.cookies.get('auth_level', ''),
        "role": request.cookies.get('auth_role', ''),
        "unit": request.cookies.get('auth_unit', ''),
        "ip": ip,
        "ua": request.headers.get("user-agent", "")[:200],
        "sid": request.cookies.get("session_id", "")
    }


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

