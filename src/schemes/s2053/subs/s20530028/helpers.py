"""Shared helper utilities for sub-scheme 20530028"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from .config import SCHEME_CONFIG
from .shared.services.cache_service import CacheService
from .shared.services.audit_service import AuditService
from .shared.utils.request_utils import get_request_info as _get_request_info_new
from .shared.utils.response_utils import get_no_cache_headers

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 20530028"""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)


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

