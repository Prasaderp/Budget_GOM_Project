from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.utils_district import check_edit_permission, validate_access_control, get_request_info
from .config import SCHEME_CONFIG
from .shared.services.cache_service import CacheService
from .shared.services.audit_service import AuditService
from .shared.utils.response_utils import get_no_cache_headers


def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)


def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[list] = None):
    CacheService.invalidate_scheme_cache(district, patterns)


def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str]
):
    AuditService.log_audit_async(table, record_id, username, old_vals, new_vals, req_info)

