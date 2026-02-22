from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.utils_district import check_edit_permission, validate_access_control
from .config import SCHEME_CONFIG
from src.schemes.s2053.subs.s20530028.shared.services.cache_service import CacheService
from src.schemes.s2053.subs.s20530028.shared.utils.response_utils import get_no_cache_headers
from src.schemes.s2053.subs.s20530028.shared.utils.validators import validate_numeric_inputs

MAX_INPUT_VALUE = 999999999

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[list] = None):
    CacheService.invalidate_scheme_cache(district, patterns)

