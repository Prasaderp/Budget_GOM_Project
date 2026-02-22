"""Shared helper utilities for sub-scheme 2215."""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status

from src.audit_service import AuditService
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from .config import (
    SCHEME_CONFIG, KONKAN_DISTRICTS,
    get_districts_for_account_head, get_all_account_heads,
    DIVISION_TOTAL_DISTRICT,
)
from .models import DistrictExpenditure2215, SCHEME_CODE, SUB_SCHEME_CODE

MAX_INPUT_VALUE = 999_999_999_999


def get_allowed_districts_for_user(auth_level: str, auth_unit: str, account_head_code: Optional[str] = None) -> List[str]:
    """Get list of district offices user can access based on their level and account head.
    
    Returns full district office names (e.g., "Chief Executive Officer, Zilla Parishad Thane")
    that match the user's access level and the account head's district offices.
    """
    base_district_names = []
    if auth_level == "district" and auth_unit:
        # Map user's district to allowed districts
        base_district_names = [auth_unit] if auth_unit in KONKAN_DISTRICTS else []
    elif auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        base_district_names = [district_name] if district_name and district_name in KONKAN_DISTRICTS else []
    elif auth_level == "dco":
        base_district_names = KONKAN_DISTRICTS
    else:
        return []

    if account_head_code:
        # Get account head specific district offices (full names)
        account_district_offices = get_districts_for_account_head(account_head_code)
        # Match base district names to full office names
        # e.g., "Thane" matches "Chief Executive Officer, Zilla Parishad Thane"
        allowed = []
        for office in account_district_offices:
            for base_district in base_district_names:
                if base_district in office or office in base_district:
                    allowed.append(office)
        return list(set(allowed))  # Remove duplicates
    return base_district_names


def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    """Create skeleton records for all account heads and districts for a fiscal year."""
    exists = (
        db.query(DistrictExpenditure2215.id)
        .filter(
            DistrictExpenditure2215.fiscal_year == fiscal_year,
            DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    account_heads = get_all_account_heads()
    rows: List[DistrictExpenditure2215] = []
    
    for head in account_heads:
        districts = get_districts_for_account_head(head["code"])
        for district in districts:
            rows.append(
                DistrictExpenditure2215(
                    fiscal_year=fiscal_year,
                    scheme_code=SCHEME_CODE,
                    sub_scheme_code=SUB_SCHEME_CODE,
                    account_head_code=head["code"],
                    district=district,
                )
            )
    
    if rows:
        db.bulk_save_objects(rows)
        db.commit()


def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Check if user has edit permission for this scheme."""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)




def validate_numeric_input(value: Optional[str], field_name: str = "field") -> int:
    """Validate and convert numeric input string to integer."""
    if value in (None, ""):
        return 0
    try:
        val = int(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid value for {field_name}",
        )
    if val < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Negative values not allowed for {field_name}",
        )
    if val > MAX_INPUT_VALUE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value too large for {field_name}",
        )
    return val


def log_audit(
    db: Session,
    request: Request,
    table: str,
    record_id: int,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
):
    """Log audit entry using centralized AuditService."""
    from src.utils_auth import get_auth_user
    AuditService.log_edit(
        db, 
        request, 
        table, 
        record_id, 
        get_auth_user(request),
        old_vals, 
        new_vals
    )


def calculate_division_totals(
    db: Session,
    fiscal_year: str,
    auth_level: str,
    auth_unit: str,
) -> Dict[str, int]:
    """Calculate division totals across all account heads for a fiscal year.
    
    Aggregates expenditure and budget data from all account heads and districts
    that the user has access to. Returns totals in the same format as individual records.
    
    Args:
        db: Database session
        fiscal_year: Fiscal year to calculate totals for
        auth_level: User's authorization level (district/taluka/dco)
        auth_unit: User's authorization unit (district/taluka name)
    
    Returns:
        Dictionary with aggregated totals for all financial fields
    """
    account_heads = get_all_account_heads()
    
    # Aggregate totals across all account heads
    division_totals = {
        "expenditure_2022_23": 0,
        "expenditure_2023_24": 0,
        "expenditure_2024_25": 0,
        "budget_estimate_2025_26": 0,
        "revised_demand_2025_26": 0,
        "budget_estimate_2026_27": 0,
    }
    
    for head in account_heads:
        allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, head["code"])
        if not allowed_districts:
            continue
        
        items = (
            db.query(DistrictExpenditure2215)
            .filter(
                DistrictExpenditure2215.fiscal_year == fiscal_year,
                DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2215.account_head_code == head["code"],
                DistrictExpenditure2215.district.in_(allowed_districts),
            )
            .all()
        )
        
        # Sum totals for this account head
        division_totals["expenditure_2022_23"] += sum(item.expenditure_2022_23 or 0 for item in items)
        division_totals["expenditure_2023_24"] += sum(item.expenditure_2023_24 or 0 for item in items)
        division_totals["expenditure_2024_25"] += sum(item.expenditure_2024_25 or 0 for item in items)
        division_totals["budget_estimate_2025_26"] += sum(item.budget_estimate_2025_26 or 0 for item in items)
        division_totals["revised_demand_2025_26"] += sum(item.revised_demand_2025_26 or 0 for item in items)
        division_totals["budget_estimate_2026_27"] += sum(item.budget_estimate_2026_27 or 0 for item in items)
    
    return division_totals

