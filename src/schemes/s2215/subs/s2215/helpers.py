"""Shared helper utilities for sub-scheme 2215."""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status
from concurrent.futures import ThreadPoolExecutor
import os

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_taluka import is_taluka_allowed
from src.utils_district import get_district_from_taluka, check_edit_permission
from .config import (
    SCHEME_CONFIG, KONKAN_DISTRICTS,
    get_districts_for_account_head, get_all_account_heads,
    DIVISION_TOTAL_DISTRICT,
)
from .models import DistrictExpenditure2215, SCHEME_CODE, SUB_SCHEME_CODE
from typing import Dict, List, Tuple

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s2215")

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


def validate_access_control(
    record_district: str,
    auth_level: str,
    auth_unit: str,
    db: Session,
) -> tuple:
    """Validate user access to a specific district record."""
    if auth_level == "district" and auth_unit:
        if auth_unit == DCO_STAFF_IDENTIFIER:
            if record_district != DCO_STAFF_IDENTIFIER:
                return False, "Access denied"
        elif record_district != auth_unit and auth_unit not in record_district:
            return False, "Access denied"

    if auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        if not district_name or (district_name not in record_district and record_district != district_name):
            return False, "Access denied"

    return True, None


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


def get_request_info(request: Request) -> Dict[str, str]:
    """Extract request information for audit logging."""
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return {
        "level": request.cookies.get("auth_level", ""),
        "role": request.cookies.get("auth_role", ""),
        "unit": request.cookies.get("auth_unit", ""),
        "ip": ip,
        "ua": request.headers.get("user-agent", "")[:200],
        "sid": request.cookies.get("session_id", ""),
    }


def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str],
    action: str = "UPDATE",
):
    """Log audit trail asynchronously."""
    def _log():
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from src.models import AuditLog

            db_url = os.getenv("DATABASE_URL", "")
            if not db_url:
                return

            engine = create_engine(db_url, pool_pre_ping=True, pool_size=1)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
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
                    action=action,
                    username=username,
                    user_level=req_info.get("level", ""),
                    user_role=req_info.get("role", ""),
                    user_unit=req_info.get("unit", ""),
                    old_values=old_vals,
                    new_values=new_vals,
                    changed_fields=changed,
                    ip_address=req_info.get("ip", ""),
                    user_agent=req_info.get("ua", ""),
                    session_id=req_info.get("sid", ""),
                )
                session.add(entry)
                session.commit()
            finally:
                session.close()
                engine.dispose()
        except Exception:
            pass

    _audit_executor.submit(_log)


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

