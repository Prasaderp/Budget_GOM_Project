"""Shared helper utilities for sub-scheme 20290262"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request
from concurrent.futures import ThreadPoolExecutor
import os

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from src.utils_cache import memory_cache
from src.audit_service import AuditService
from .config import SCHEME_CONFIG

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s20290262")

MAX_INPUT_VALUE = 999999999

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 20290262"""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[list] = None):
    """Invalidate cache entries for scheme-related data"""
    default_patterns = ["budget_summary", "budget_details", "unit_exp_summary", "unit_exp_charts", "post_status", "post_expenses"]
    if patterns:
        default_patterns.extend(patterns)
    if district:
        default_patterns.extend([f"district_budget|{district}", f"district_summary|{district}", f"district_charts|{district}"])
    
    with memory_cache._lock:
        keys = [k for k in list(memory_cache._store.keys()) if any(p in k for p in default_patterns)]
        for k in keys:
            memory_cache._store.pop(k, None)

def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str]
):
    """Async audit logging using thread pool"""
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
                action='UPDATE',
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

def get_no_cache_headers() -> Dict[str, str]:
    """Get standard no-cache headers for responses"""
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

def validate_numeric_inputs(*values, max_value: int = MAX_INPUT_VALUE) -> tuple:
    """Validate numeric inputs are non-negative and within max value"""
    if any(v < 0 for v in values if v is not None):
        return False, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
    if any(v > max_value for v in values if v is not None):
        return False, "मूल्य खूप मोठे आहे"
    return True, None

