"""Shared helper utilities for scheme 0029"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status
from concurrent.futures import ThreadPoolExecutor
import os

from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from .config import SCHEME_CONFIG, KONKAN_DISTRICTS, get_districts_for_section, get_all_table_sections, get_section3_table_sections, get_section4_table_sections, get_jama_talmel_table_sections, JAMA_TALMEL_DISTRICTS
from .models import DistrictRevenue0029, DistrictRevenue0029Section3, DistrictRevenue0029Section4, DistrictRevenue0029JamaTalmel, SCHEME_CODE, SUB_SCHEME_CODE

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s0029")

MAX_INPUT_VALUE = 999_999_999_999


def get_allowed_districts_for_user(auth_level: str, auth_unit: str, table_section_code: Optional[str] = None) -> List[str]:
    base_districts = []
    if auth_level == "district" and auth_unit:
        base_districts = [auth_unit] if auth_unit in KONKAN_DISTRICTS else []
    elif auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        base_districts = [district_name] if district_name and district_name in KONKAN_DISTRICTS else []
    elif auth_level == "dco":
        base_districts = KONKAN_DISTRICTS
    else:
        return []

    if table_section_code:
        section_districts = get_districts_for_section(table_section_code)
        return [d for d in base_districts if d in section_districts]
    return base_districts


def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    exists = (
        db.query(DistrictRevenue0029.id)
        .filter(
            DistrictRevenue0029.fiscal_year == fiscal_year,
            DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    sections = get_all_table_sections()
    rows: List[DistrictRevenue0029] = []
    for section in sections:
        districts = get_districts_for_section(section["code"])
        for district in districts:
            rows.append(
                DistrictRevenue0029(
                    fiscal_year=fiscal_year,
                    scheme_code=SCHEME_CODE,
                    sub_scheme_code=SUB_SCHEME_CODE,
                    table_section_code=section["code"],
                    district=district,
                )
            )
    db.bulk_save_objects(rows)
    db.commit()


def check_dco_access(auth_level: str) -> bool:
    """Check if user has DCO level access"""
    return auth_level == "dco"

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

def check_edit_permission_for_section3(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Check edit permission for section 3 - only DCO assistant can edit"""
    if not check_dco_access(auth_level):
        return False
    if auth_role != "assistant":
        return False
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

def check_edit_permission_for_section5(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Check edit permission for section 5 - DCO assistant can edit all, district assistant can edit their district"""
    if auth_role != "assistant":
        return False
    if check_dco_access(auth_level):
        return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)
    if auth_level == "district" and auth_unit in JAMA_TALMEL_DISTRICTS:
        return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)
    if auth_level == "taluka" and auth_unit:
        from src.utils_district import get_district_from_taluka
        district_name = get_district_from_taluka(auth_unit)
        if district_name and district_name in JAMA_TALMEL_DISTRICTS:
            return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)
    return False




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

def ensure_fiscal_year_seeded_section3(db: Session, fiscal_year: str) -> None:
    exists = (
        db.query(DistrictRevenue0029Section3.id)
        .filter(
            DistrictRevenue0029Section3.fiscal_year == fiscal_year,
            DistrictRevenue0029Section3.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    sections = get_section3_table_sections()
    rows: List[DistrictRevenue0029Section3] = []
    for section in sections:
        rows.append(
            DistrictRevenue0029Section3(
                fiscal_year=fiscal_year,
                scheme_code=SCHEME_CODE,
                sub_scheme_code=SUB_SCHEME_CODE,
                table_section_code=section["code"],
            )
        )
    db.bulk_save_objects(rows)
    db.commit()

def ensure_fiscal_year_seeded_section4(db: Session, fiscal_year: str) -> None:
    exists = (
        db.query(DistrictRevenue0029Section4.id)
        .filter(
            DistrictRevenue0029Section4.fiscal_year == fiscal_year,
            DistrictRevenue0029Section4.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    sections = get_section4_table_sections()
    rows: List[DistrictRevenue0029Section4] = []
    for section in sections:
        rows.append(
            DistrictRevenue0029Section4(
                fiscal_year=fiscal_year,
                scheme_code=SCHEME_CODE,
                sub_scheme_code=SUB_SCHEME_CODE,
                table_section_code=section["code"],
            )
        )
    db.bulk_save_objects(rows)
    db.commit()

def ensure_fiscal_year_seeded_jama_talmel(db: Session, fiscal_year: str) -> None:
    exists = (
        db.query(DistrictRevenue0029JamaTalmel.id)
        .filter(
            DistrictRevenue0029JamaTalmel.fiscal_year == fiscal_year,
            DistrictRevenue0029JamaTalmel.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .limit(1)
        .first()
    )
    if exists:
        return

    sections = get_jama_talmel_table_sections()
    rows: List[DistrictRevenue0029JamaTalmel] = []
    for section in sections:
        rows.append(
            DistrictRevenue0029JamaTalmel(
                fiscal_year=fiscal_year,
                scheme_code=SCHEME_CODE,
                sub_scheme_code=SUB_SCHEME_CODE,
                table_section_code=section["code"],
            )
        )
    db.bulk_save_objects(rows)
    db.commit()

def get_user_editable_districts(auth_level: str, auth_unit: str) -> List[str]:
    if auth_level == "district" and auth_unit:
        return [auth_unit] if auth_unit in JAMA_TALMEL_DISTRICTS else []
    elif auth_level == "taluka" and auth_unit:
        from src.utils_district import get_district_from_taluka
        district_name = get_district_from_taluka(auth_unit)
        return [district_name] if district_name and district_name in JAMA_TALMEL_DISTRICTS else []
    elif auth_level == "dco":
        return JAMA_TALMEL_DISTRICTS.copy()
    return []

