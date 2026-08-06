from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status
from concurrent.futures import ThreadPoolExecutor

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from .config import (
    SCHEME_CONFIG, KONKAN_DISTRICTS, EXTRA_DISTRICT, SECTION3_DISTRICTS,
    get_districts_for_section, get_all_table_sections, get_section3_table_sections,
    ROW_TYPE_DC, ROW_TYPE_ZP, ROW_TYPE_SUBTOTAL, ROW_TYPE_DIVISION, ROW_TYPE_GRAND_TOTAL,
)
from .models import DistrictExpenditure2245, SCHEME_CODE, SUB_SCHEME_CODE

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s2245")

MAX_INPUT_VALUE = 999_999_999_999

def get_allowed_districts_for_user(auth_level: str, auth_unit: str, table_section_code: Optional[str] = None) -> List[str]:
    base_districts = []
    if auth_level == "district" and auth_unit:
        base_districts = [auth_unit] if auth_unit in KONKAN_DISTRICTS or auth_unit == EXTRA_DISTRICT else []
    elif auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        base_districts = [district_name] if district_name and (district_name in KONKAN_DISTRICTS or district_name == EXTRA_DISTRICT) else []
    elif auth_level == "dco":
        base_districts = KONKAN_DISTRICTS + [EXTRA_DISTRICT]
    else:
        return []

    if table_section_code:
        section_districts = get_districts_for_section(table_section_code)
        return [d for d in base_districts if d in section_districts]
    return base_districts

def build_section3_district_key(district: str, row_type: str) -> str:
    return f"{district}|{row_type}"

def parse_section3_district_key(key: str) -> tuple:
    if "|" not in key:
        return key, None
    parts = key.split("|", 1)
    return parts[0], parts[1] if len(parts) > 1 else None

def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    exists = (
        db.query(DistrictExpenditure2245.id)
        .filter(
            DistrictExpenditure2245.fiscal_year == fiscal_year,
            DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    sections = get_all_table_sections()
    rows: List[DistrictExpenditure2245] = []
    for section in sections:
        if section.get("is_section3"):
            districts = get_districts_for_section(section["code"])
            for district in districts:
                for row_type in [ROW_TYPE_DC, ROW_TYPE_ZP]:
                    rows.append(
                        DistrictExpenditure2245(
                            fiscal_year=fiscal_year,
                            scheme_code=SCHEME_CODE,
                            sub_scheme_code=SUB_SCHEME_CODE,
                            table_section_code=section["code"],
                            district=build_section3_district_key(district, row_type),
                        )
                    )
        else:
            districts = get_districts_for_section(section["code"])
            for district in districts:
                rows.append(
                    DistrictExpenditure2245(
                        fiscal_year=fiscal_year,
                        scheme_code=SCHEME_CODE,
                        sub_scheme_code=SUB_SCHEME_CODE,
                        table_section_code=section["code"],
                        district=district,
                    )
                )
    db.bulk_save_objects(rows)
    db.flush()
    from src.core.taluka.provisioning import ensure_contribution_rows
    for d in {r.district for r in rows}:
        ensure_contribution_rows(db, DistrictExpenditure2245, d, fiscal_year)
    db.commit()

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

def build_section3_table_data(
    db: Session,
    fiscal_year: str,
    table_section_code: str,
    allowed_districts: List[str],
) -> Dict[str, Any]:
    from .config import get_table_section
    
    section = get_table_section(table_section_code)
    if not section or not section.get("is_section3"):
        return None
    
    base_districts = SECTION3_DISTRICTS
    allowed_base = [d for d in base_districts if d in allowed_districts]
    
    rows_data = []
    district_totals = {}
    division_totals = {
        "exp_prev3": 0,
        "exp_prev2": 0,
        "exp_prev1": 0,
        "budget_estimate_curr": 0,
        "revised_estimate_curr": 0,
        "budget_estimate_next": 0,
    }
    
    for district in base_districts:
        if district not in allowed_base:
            continue
        
        dc_key = build_section3_district_key(district, ROW_TYPE_DC)
        zp_key = build_section3_district_key(district, ROW_TYPE_ZP)
        
        dc_record = (
            db.query(DistrictExpenditure2245)
            .filter(
                DistrictExpenditure2245.fiscal_year == fiscal_year,
                DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2245.table_section_code == table_section_code,
                DistrictExpenditure2245.district == dc_key,
            )
            .first()
        )
        
        zp_record = (
            db.query(DistrictExpenditure2245)
            .filter(
                DistrictExpenditure2245.fiscal_year == fiscal_year,
                DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2245.table_section_code == table_section_code,
                DistrictExpenditure2245.district == zp_key,
            )
            .first()
        )
        
        dc_data = {
            "exp_prev3": dc_record.exp_prev3 or 0 if dc_record else 0,
            "exp_prev2": dc_record.exp_prev2 or 0 if dc_record else 0,
            "exp_prev1": dc_record.exp_prev1 or 0 if dc_record else 0,
            "budget_estimate_curr": dc_record.budget_estimate_curr or 0 if dc_record else 0,
            "revised_estimate_curr": dc_record.revised_estimate_curr or 0 if dc_record else 0,
            "budget_estimate_next": dc_record.budget_estimate_next or 0 if dc_record else 0,
        } if dc_record else {
            "exp_prev3": 0, "exp_prev2": 0, "exp_prev1": 0,
            "budget_estimate_curr": 0, "revised_estimate_curr": 0, "budget_estimate_next": 0,
        }
        
        zp_data = {
            "exp_prev3": zp_record.exp_prev3 or 0 if zp_record else 0,
            "exp_prev2": zp_record.exp_prev2 or 0 if zp_record else 0,
            "exp_prev1": zp_record.exp_prev1 or 0 if zp_record else 0,
            "budget_estimate_curr": zp_record.budget_estimate_curr or 0 if zp_record else 0,
            "revised_estimate_curr": zp_record.revised_estimate_curr or 0 if zp_record else 0,
            "budget_estimate_next": zp_record.budget_estimate_next or 0 if zp_record else 0,
        } if zp_record else {
            "exp_prev3": 0, "exp_prev2": 0, "exp_prev1": 0,
            "budget_estimate_curr": 0, "revised_estimate_curr": 0, "budget_estimate_next": 0,
        }
        
        rows_data.append({
            "district": district,
            "row_type": ROW_TYPE_DC,
            "record_id": dc_record.id if dc_record else None,
            "record": dc_record,
            **dc_data,
        })
        
        rows_data.append({
            "district": district,
            "row_type": ROW_TYPE_ZP,
            "record_id": zp_record.id if zp_record else None,
            "record": zp_record,
            **zp_data,
        })
        
        district_total = {
            "exp_prev3": dc_data["exp_prev3"] + zp_data["exp_prev3"],
            "exp_prev2": dc_data["exp_prev2"] + zp_data["exp_prev2"],
            "exp_prev1": dc_data["exp_prev1"] + zp_data["exp_prev1"],
            "budget_estimate_curr": dc_data["budget_estimate_curr"] + zp_data["budget_estimate_curr"],
            "revised_estimate_curr": dc_data["revised_estimate_curr"] + zp_data["revised_estimate_curr"],
            "budget_estimate_next": dc_data["budget_estimate_next"] + zp_data["budget_estimate_next"],
        }
        
        district_totals[district] = district_total
        
        for key in division_totals:
            division_totals[key] += district_total[key]
        
        rows_data.append({
            "district": district,
            "row_type": ROW_TYPE_SUBTOTAL,
            "record_id": None,
            "record": None,
            **district_total,
        })
    
    return {
        "section": section,
        "rows": rows_data,
        "district_totals": district_totals,
        "division_totals": division_totals,
        "grand_totals": division_totals.copy(),
    }

def validate_numeric_input(value: Optional[str], field_name: str = "field") -> int:
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

def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str],
    action: str = "UPDATE",
):
    def _log():
        try:
            from src.models import AuditLog
            from src.database import SessionLocal

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
        except Exception:
            pass

    _audit_executor.submit(_log)
