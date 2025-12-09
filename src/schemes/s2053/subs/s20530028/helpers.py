"""Shared helper utilities for sub-scheme 20530028"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission
from .config import SCHEME_CONFIG
from .shared.services.cache_service import CacheService
from .shared.services.audit_service import AuditService
from .shared.utils.request_utils import get_request_info as _get_request_info_new
from .shared.utils.response_utils import get_no_cache_headers

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 20530028"""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

def validate_access_control(
    record_district: str,
    auth_level: str,
    auth_unit: str,
    db: Session
) -> tuple:
    """Validate access control for district/taluka users. Returns (allowed, error_message)"""
    if auth_level == 'district' and auth_unit:
        if auth_unit == DCO_STAFF_IDENTIFIER:
            if record_district != DCO_STAFF_IDENTIFIER:
                return False, "Access denied"
        elif record_district != auth_unit or record_district == DCO_STAFF_IDENTIFIER:
            return False, "Access denied"
    
    if auth_level == 'taluka' and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        if not district_name or record_district != district_name or record_district == DCO_STAFF_IDENTIFIER:
            return False, "Access denied"
    
    return True, None

# Backward compatibility wrappers - delegate to new shared services
def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[list] = None):
    """Invalidate cache entries for scheme-related data (delegates to CacheService)"""
    CacheService.invalidate_scheme_cache(district, patterns)

def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str]
):
    """Async audit logging using thread pool (delegates to AuditService)"""
    AuditService.log_audit_async(table, record_id, username, old_vals, new_vals, req_info)

def get_request_info(request: Request) -> Dict[str, str]:
    """Extract request information for audit logging (delegates to shared utils)"""
    return _get_request_info_new(request)

