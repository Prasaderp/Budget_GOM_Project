from typing import Optional, TYPE_CHECKING
from src.config import DCO_STAFF_IDENTIFIER

if TYPE_CHECKING:
    from sqlalchemy.orm import Query, Session

def get_district_from_taluka(unit: str) -> Optional[str]:
    """Extract district name from taluka unit string."""
    return unit.split(' Taluka ')[0] if ' Taluka ' in unit else None

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

def check_edit_permission(auth_role: str, auth_level: str, auth_unit: str, db) -> bool:
    """
    Check if user has permission to edit data.
    Officers (officer1, officer2, dco) are read-only.
    Taluka users must have active taluka.
    Assistants must be within data filling period.
    """
    if auth_role in ("officer1", "officer2", "dco"):
        return False
    if auth_level == 'taluka' and auth_unit:
        from src.utils_taluka import is_taluka_allowed
        if not is_taluka_allowed(db, auth_unit):
            return False
    if auth_role == 'assistant':
        from src.utils_timing import check_data_filling_allowed
        is_allowed, _ = check_data_filling_allowed(db, auth_level, auth_role)
        return is_allowed
    return True

