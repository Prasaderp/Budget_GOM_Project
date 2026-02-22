"""Shared helper utilities for sub-scheme 20290046"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control
from src.utils_cache import memory_cache
from src.audit_service import AuditService
from .config import SCHEME_CONFIG

MAX_INPUT_VALUE = 999999999

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 20290046"""
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

