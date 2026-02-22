"""Shared utilities for all s2235 subschemes."""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from concurrent.futures import ThreadPoolExecutor

MAX_INPUT_VALUE = 999_999_999_999

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s2235")

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
    """Async audit logging using thread pool and shared DB session pool."""
    def _log():
        try:
            from src.database import SessionLocal
            from src.models import AuditLog
            
            session = SessionLocal()
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
        except Exception:
            pass
    
    _audit_executor.submit(_log)
