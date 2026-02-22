from typing import Optional, Dict, Tuple, TYPE_CHECKING
from urllib.parse import unquote
from fastapi import Request
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_auth import get_auth_level, get_auth_role, get_auth_unit

if TYPE_CHECKING:
    from sqlalchemy.orm import Query, Session

def get_district_from_taluka(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    decoded = unquote(unit)
    return decoded.split(' Taluka ')[0] if ' Taluka ' in decoded else None

def get_user_district(auth_level: str, auth_unit: str) -> Optional[str]:
    """Get user's district name for display purposes."""
    if not auth_unit:
        return None
    
    decoded_unit = unquote(auth_unit)
    
    if auth_level == 'taluka':
        district = get_district_from_taluka(decoded_unit)
        return district if district else decoded_unit
    elif auth_level == 'district':
        return decoded_unit if decoded_unit != DCO_STAFF_IDENTIFIER else None
    elif auth_level == 'dco':
        return "Konkan Division"
    
    return None

def validate_access_control(
    record_district: str,
    auth_level: str,
    auth_unit: str,
    db: "Session"
) -> Tuple[bool, Optional[str]]:
    """
    Centralized access control validation for district/taluka users.
    Returns (allowed, error_message).
    
    Taluka assistants can edit their parent district's data.
    """
    if auth_level == 'district' and auth_unit:
        if auth_unit == DCO_STAFF_IDENTIFIER:
            if record_district != DCO_STAFF_IDENTIFIER:
                return False, "Access denied"
        elif record_district != auth_unit or record_district == DCO_STAFF_IDENTIFIER:
            return False, "Access denied"
    
    if auth_level == 'taluka' and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        if not district_name:
            return False, "Invalid taluka configuration"
        if record_district == DCO_STAFF_IDENTIFIER:
            return False, "Access denied"
        if record_district != district_name:
            return False, "Access denied"
    
    return True, None

def get_request_info(request: Request) -> Dict[str, str]:
    """Extract request information for audit logging."""
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return {
        "level": get_auth_level(request),
        "role": get_auth_role(request),
        "unit": get_auth_unit(request),
        "ip": ip,
        "ua": request.headers.get("user-agent", "")[:200],
        "sid": request.cookies.get("session_id", "")
    }

def build_district_filter(query, auth_level: str, auth_unit: str, model):
    """
    Build district filter based on user level and unit.
    DCO Staff is treated as separate entity: district users see only their district,
    DCO Staff users see only DCO Staff, DCO level sees all including DCO Staff.
    """
    if auth_level == 'district' and auth_unit:
        if auth_unit == DCO_STAFF_IDENTIFIER:
            return query.filter(model.district == DCO_STAFF_IDENTIFIER)
        else:
            return query.filter(model.district == auth_unit).filter(model.district != DCO_STAFF_IDENTIFIER)
    elif auth_level == 'taluka' and auth_unit:
        district = get_district_from_taluka(auth_unit)
        if district and district != DCO_STAFF_IDENTIFIER:
            return query.filter(model.district == district).filter(model.district != DCO_STAFF_IDENTIFIER)
        return query.filter(model.id == -1)
    elif auth_level == 'dco':
        return query
    return query.filter(model.district != DCO_STAFF_IDENTIFIER)

def check_edit_permission(auth_role: str, auth_level: str, auth_unit: str, db, sub_scheme_code: str = None) -> bool:
    """
    Check if user has permission to edit data.
    Officers (officer1, officer2, dco) are read-only.
    Taluka assistants can edit their parent district's data.
    Assistants must be within data filling period.
    """
    if auth_role in ("officer1", "officer2", "dco"):
        return False
    if auth_role == 'assistant':
        from src.utils_timing import check_data_filling_allowed
        is_allowed, _ = check_data_filling_allowed(db, auth_level, auth_role, sub_scheme_code)
        return is_allowed
    return True

