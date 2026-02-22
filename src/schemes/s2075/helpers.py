"""Shared helper utilities for scheme 2075 - Miscellaneous General Services.

Production-grade implementation with:
- Centralized permission checking
- Cache integration for performance
- Async audit logging via AuditService
- Input validation utilities
"""
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from src.utils_district import check_edit_permission, get_request_info
from src.utils_cache import ttl_cache, memory_cache
from src.audit_service import AuditService
from .config import SCHEME_CONFIG, DISTRICTS

MAX_INPUT_VALUE = 999_999_999_999


# ============================================================================
# PERMISSION HELPERS
# ============================================================================

def check_dco_access(auth_level: str) -> bool:
    """Check if user has DCO-level access."""
    return auth_level == "dco"


def get_allowed_districts(auth_level: str, auth_unit: str) -> List[str]:
    """Get list of districts user can access based on auth context."""
    if auth_level == "dco":
        return DISTRICTS
    if auth_level == "district" and auth_unit in DISTRICTS:
        return [auth_unit]
    return []


def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 2075."""
    if auth_level not in ("dco", "district"):
        return False
    if auth_level == "district" and auth_unit not in DISTRICTS:
        return False
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)


def validate_district_access(district: str, auth_level: str, auth_unit: str) -> Tuple[bool, Optional[str]]:
    """Validate user can access a specific district."""
    if auth_level == "dco":
        return True, None
    if auth_level == "district":
        if auth_unit == district:
            return True, None
        return False, "You can only access your own district"
    return False, "Access denied"


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_numeric_input(value: Optional[str], field_name: str = "field") -> int:
    """Validate and convert numeric input from form data."""
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


def validate_numeric_inputs(*values, max_value: int = MAX_INPUT_VALUE) -> Tuple[bool, Optional[str]]:
    """Validate multiple numeric inputs are non-negative and within max value."""
    if any(v < 0 for v in values if v is not None):
        return False, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
    if any(v > max_value for v in values if v is not None):
        return False, "मूल्य खूप मोठे आहे"
    return True, None


# ============================================================================
# DATA SEEDING
# ============================================================================

def ensure_sub_head_seeded(db: Session, fiscal_year: str) -> None:
    """Ensure sub-head record exists for the fiscal year."""
    from .models import SubHeadExpenditure2075, SCHEME_CODE
    from .config import SUB_HEAD_TEXT_249
    
    exists = db.query(SubHeadExpenditure2075.id).filter(
        SubHeadExpenditure2075.fiscal_year == fiscal_year,
        SubHeadExpenditure2075.sub_scheme_code == "20750249",
    ).limit(1).first()
    
    if not exists:
        row = SubHeadExpenditure2075(
            fiscal_year=fiscal_year,
            scheme_code=SCHEME_CODE,
            sub_scheme_code="20750249",
            sub_head=SUB_HEAD_TEXT_249,
        )
        db.add(row)
        db.commit()


def ensure_districts_seeded(db: Session, fiscal_year: str) -> None:
    """Ensure district records exist for the fiscal year."""
    from .models import DistrictExpenditure2075, SCHEME_CODE
    
    existing = db.query(DistrictExpenditure2075.district).filter(
        DistrictExpenditure2075.fiscal_year == fiscal_year,
        DistrictExpenditure2075.sub_scheme_code == "20750294",
    ).all()
    existing_set = {r[0] for r in existing}
    
    for district in DISTRICTS:
        if district not in existing_set:
            row = DistrictExpenditure2075(
                fiscal_year=fiscal_year,
                scheme_code=SCHEME_CODE,
                sub_scheme_code="20750294",
                district=district,
            )
            db.add(row)
    
    db.commit()


# ============================================================================
# AGGREGATION WITH CACHING
# ============================================================================

@ttl_cache(ttl_seconds=60, include_fiscal_year=True)
def get_aggregated_totals(db: Session, fiscal_year: str) -> Dict[str, int]:
    """Get aggregated totals for both sub-schemes with caching.
    
    Returns integer values only - no floats or decimals from SQL aggregation.
    """
    from .models import SubHeadExpenditure2075, DistrictExpenditure2075
    
    def _to_int(val: Any) -> int:
        """Safely convert SQL aggregation result to int."""
        return int(val if val is not None else 0)
    
    sub_head = db.query(
        func.coalesce(func.sum(SubHeadExpenditure2075.expenditure_2022_23), 0),
        func.coalesce(func.sum(SubHeadExpenditure2075.expenditure_2023_24), 0),
        func.coalesce(func.sum(SubHeadExpenditure2075.expenditure_2024_25), 0),
        func.coalesce(func.sum(SubHeadExpenditure2075.budget_estimate), 0),
        func.coalesce(func.sum(SubHeadExpenditure2075.revised_estimate), 0),
        func.coalesce(func.sum(SubHeadExpenditure2075.budget_estimate_2026_27), 0),
    ).filter(
        SubHeadExpenditure2075.fiscal_year == fiscal_year,
        SubHeadExpenditure2075.sub_scheme_code == "20750249",
    ).first()
    
    district = db.query(
        func.coalesce(func.sum(DistrictExpenditure2075.expenditure_2022_23), 0),
        func.coalesce(func.sum(DistrictExpenditure2075.expenditure_2023_24), 0),
        func.coalesce(func.sum(DistrictExpenditure2075.expenditure_2024_25), 0),
        func.coalesce(func.sum(DistrictExpenditure2075.budget_estimate), 0),
        func.coalesce(func.sum(DistrictExpenditure2075.revised_estimate), 0),
        func.coalesce(func.sum(DistrictExpenditure2075.budget_estimate_2026_27), 0),
    ).filter(
        DistrictExpenditure2075.fiscal_year == fiscal_year,
        DistrictExpenditure2075.sub_scheme_code == "20750294",
    ).first()
    
    return {
        "sub_head_expenditure_2022_23": _to_int(sub_head[0] if sub_head else 0),
        "sub_head_expenditure_2023_24": _to_int(sub_head[1] if sub_head else 0),
        "sub_head_expenditure_2024_25": _to_int(sub_head[2] if sub_head else 0),
        "sub_head_budget_estimate": _to_int(sub_head[3] if sub_head else 0),
        "sub_head_revised_estimate": _to_int(sub_head[4] if sub_head else 0),
        "sub_head_budget_estimate_2026_27": _to_int(sub_head[5] if sub_head else 0),
        "district_expenditure_2022_23": _to_int(district[0] if district else 0),
        "district_expenditure_2023_24": _to_int(district[1] if district else 0),
        "district_expenditure_2024_25": _to_int(district[2] if district else 0),
        "district_budget_estimate": _to_int(district[3] if district else 0),
        "district_revised_estimate": _to_int(district[4] if district else 0),
        "district_budget_estimate_2026_27": _to_int(district[5] if district else 0),
    }


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

def invalidate_scheme_cache(district: Optional[str] = None) -> None:
    """Invalidate cache entries for scheme 2075 data."""
    patterns = ["get_aggregated_totals", "s2075"]
    if district:
        patterns.append(district)
    
    with memory_cache._lock:
        keys = [k for k in list(memory_cache._store.keys()) if any(p in k for p in patterns)]
        for k in keys:
            memory_cache._store.pop(k, None)


# ============================================================================
# AUDIT LOGGING
# ============================================================================

def log_audit(db: Session, request: Any, table: str, record_id: int, 
              old_vals: Dict[str, Any], new_vals: Dict[str, Any]) -> None:
    """Log audit entry using centralized AuditService."""
    from src.utils_auth import get_auth_user
    AuditService.log_edit(db, request, table, record_id, 
                          get_auth_user(request),
                          old_vals, new_vals)


# ============================================================================
# RESPONSE HEADERS
# ============================================================================

def get_no_cache_headers() -> Dict[str, str]:
    """Get standard no-cache headers for responses."""
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
