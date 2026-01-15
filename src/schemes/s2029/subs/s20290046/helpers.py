"""Shared helper utilities for sub-scheme 20290046"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request
from concurrent.futures import ThreadPoolExecutor
import os
import logging

from src.config import DCO_STAFF_IDENTIFIER, DISTRICTS, CATEGORIES, STATUSES, CLASSES_SHEET1_2, CLASSES_SHEET3, PRIMARY_UNITS
from src.utils_district import get_district_from_taluka, check_edit_permission, validate_access_control, get_request_info
from src.utils_cache import memory_cache
from src.audit_service import AuditService
from .config import SCHEME_CONFIG, SCHEME_CODE, SUB_SCHEME_CODE, CLASS_DESIGNATIONS
from .models import BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure

logger = logging.getLogger(__name__)

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s20290046")

MAX_INPUT_VALUE = 999999999

def check_edit_permission_for_scheme(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    """Unified permission check for scheme 20290046"""
    return check_edit_permission(auth_role, auth_level, auth_unit, db, SCHEME_CONFIG.code)

def invalidate_scheme_cache(district: Optional[str] = None, patterns: Optional[list] = None):
    """Invalidate cache entries for scheme-related data"""
    default_patterns = ["budget_summary", "budget_details", "unit_exp_summary", "unit_exp_charts", "post_status", "post_expenses"]
    if patterns:
        default_patterns.extend(patterns)
    if district:
        default_patterns.extend([f"district_budget|{district}", f"district_summary|{district}", f"district_charts|{district}"])
    
    with memory_cache._lock:
        keys = [k for k in list(memory_cache._store.keys()) if any(p in k for p in default_patterns)]
        for k in keys:
            memory_cache._store.pop(k, None)

def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str]
):
    """Async audit logging using thread pool"""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models import AuditLog
        
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            return
        
        engine = create_engine(db_url, pool_pre_ping=True, pool_size=1)
        Session = sessionmaker(bind=engine)
        session = Session()
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
                action='UPDATE',
                username=username,
                user_level=req_info.get('level', ''),
                user_role=req_info.get('role', ''),
                user_unit=req_info.get('unit', ''),
                old_values=old_vals,
                new_values=new_vals,
                changed_fields=changed,
                ip_address=req_info.get('ip', ''),
                user_agent=req_info.get('ua', ''),
                session_id=req_info.get('sid', '')
            )
            session.add(entry)
            session.commit()
        finally:
            session.close()
            engine.dispose()
    except Exception:
        pass

def get_no_cache_headers() -> Dict[str, str]:
    """Get standard no-cache headers for responses"""
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

def validate_numeric_inputs(*values, max_value: int = MAX_INPUT_VALUE) -> tuple:
    """Validate numeric inputs are non-negative and within max value"""
    if any(v < 0 for v in values if v is not None):
        return False, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
    if any(v > max_value for v in values if v is not None):
        return False, "मूल्य खूप मोठे आहे"
    return True, None

def ensure_fiscal_year_seeded(db: Session, fiscal_year: str) -> None:
    """
    Ensure skeleton records exist for all 4 tables for the given fiscal year.
    
    This function seeds BudgetPostDetails, PostStatus, PostExpenses, and UnitExpenditure
    tables with zero-initialized records for all combinations of:
    - Districts (from config or global DISTRICTS)
    - Categories (Permanent, Temporary)
    - Classes (Class-1 & 2, Class-3, Class-4 for sheets 1&2; 1,2,3,4 for sheet 3)
    - Designations (from CLASS_DESIGNATIONS mapping or all designations)
    - Statuses (Filled, Vacant for PostStatus)
    - Primary Units (for UnitExpenditure)
    
    Args:
        db: Database session
        fiscal_year: Fiscal year string (e.g., "2025-26")
    
    Returns:
        None (raises exception on error)
    
    Note:
        This function is idempotent - it skips seeding if records already exist.
    """
    if not fiscal_year or not isinstance(fiscal_year, str):
        raise ValueError(f"Invalid fiscal_year: {fiscal_year}")
    
    # Idempotent check - skip if records already exist
    exists = db.query(BudgetPostDetails.id).filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == SUB_SCHEME_CODE
    ).limit(1).first()
    
    if exists:
        logger.info(f"Skipping {SUB_SCHEME_CODE} - records already exist for {fiscal_year}")
        return
    
    # Get configuration values with fallbacks
    scheme_designations = SCHEME_CONFIG.designations if SCHEME_CONFIG.designations else []
    scheme_classes = SCHEME_CONFIG.classes if SCHEME_CONFIG.classes else CLASSES_SHEET1_2
    scheme_categories = SCHEME_CONFIG.categories if SCHEME_CONFIG.categories else CATEGORIES
    scheme_statuses = STATUSES
    scheme_classes_sheet3 = CLASSES_SHEET3
    scheme_primary_units = SCHEME_CONFIG.primary_units if SCHEME_CONFIG.primary_units else PRIMARY_UNITS
    
    # Use scheme-specific districts if defined, else default to global DISTRICTS
    scheme_districts = SCHEME_CONFIG.districts if SCHEME_CONFIG.districts else DISTRICTS
    
    # Get CLASS_DESIGNATIONS mapping if available
    class_designations = CLASS_DESIGNATIONS if CLASS_DESIGNATIONS else None
    
    # Validate we have required data
    if not scheme_designations:
        raise ValueError(f"No designations configured for {SUB_SCHEME_CODE}")
    if not scheme_districts:
        raise ValueError(f"No districts configured for {SUB_SCHEME_CODE}")
    if not scheme_classes:
        raise ValueError(f"No classes configured for {SUB_SCHEME_CODE}")
    if not scheme_categories:
        raise ValueError(f"No categories configured for {SUB_SCHEME_CODE}")
    if not scheme_primary_units:
        raise ValueError(f"No primary units configured for {SUB_SCHEME_CODE}")
    
    logger.info(f"Seeding fiscal year {fiscal_year} for {SUB_SCHEME_CODE}")
    
    bpd_records: List[BudgetPostDetails] = []
    ps_records: List[PostStatus] = []
    pe_records: List[PostExpenses] = []
    ue_records: List[UnitExpenditure] = []
    
    # Build BudgetPostDetails records
    for district in scheme_districts:
        for category in scheme_categories:
            for cls in scheme_classes:
                # Use class-specific designations if available, else all designations
                if class_designations and cls in class_designations:
                    designations_for_class = class_designations[cls]
                else:
                    designations_for_class = scheme_designations
                
                for designation in designations_for_class:
                    bpd_records.append(BudgetPostDetails(
                        district=district,
                        category=category,
                        class_type=cls,
                        designation=designation,
                        fiscal_year=fiscal_year,
                        sanctioned_posts_2024_25=0,
                        sanctioned_posts_2025_26=0,
                        special_pay=0,
                        basic_pay=0,
                        grade_pay=0,
                        local_supplementary_allowance=0,
                        vehicle_allowance=0,
                        washing_allowance=0,
                        cash_allowance=0,
                        footwear_allowance_other=0,
                        hra_rate='X'
                    ))
    
    # Build PostStatus records
    for district in scheme_districts:
        for category in scheme_categories:
            for cls in scheme_classes:
                for status in scheme_statuses:
                    ps_records.append(PostStatus(
                        district=district,
                        category=category,
                        class_type=cls,
                        status=status,
                        fiscal_year=fiscal_year,
                        posts=0,
                        salary=0,
                        grade_pay=0,
                        special_pay=0,
                        dearness_allowance=0,
                        local_supplementary_allowance=0,
                        house_rent_allowance=0,
                        travel_allowance=0,
                        other=0
                    ))
    
    # Build PostExpenses records
    for district in scheme_districts:
        for category in scheme_categories:
            for cls in scheme_classes_sheet3:
                pe_records.append(PostExpenses(
                    district=district,
                    category=category,
                    class_type=cls,
                    fiscal_year=fiscal_year,
                    filled_posts=0,
                    vacant_posts=0,
                    medical_expenses=0,
                    festival_advance=0,
                    swagram_maharashtra_darshan=0,
                    seventh_pay_commission_difference_nps=None,
                    nps=None,
                    seventh_pay_commission_difference=None,
                    other=0
                ))
    
    # Build UnitExpenditure records
    for district in scheme_districts:
        for primary_unit in scheme_primary_units:
            ue_records.append(UnitExpenditure(
                district=district,
                unit_account=primary_unit,
                fiscal_year=fiscal_year,
                expenditure_2021_22=0,
                expenditure_2022_23=0,
                expenditure_2023_24=0,
                budget_2024_25=0,
                forecast_2024_25=0,
                budget_2025_26_estimating_officer=0,
                budget_2025_26_controlling_officer=0,
                budget_2025_26_admin_dept=0,
                budget_2025_26_finance_dept=0
            ))
    
    # Batch insert for performance
    BATCH_SIZE = 1000
    
    try:
        # Insert BudgetPostDetails
        for i in range(0, len(bpd_records), BATCH_SIZE):
            db.bulk_save_objects(bpd_records[i:i+BATCH_SIZE])
            db.flush()
        logger.info(f"Inserted {len(bpd_records)} BudgetPostDetails records")
        
        # Insert PostStatus
        for i in range(0, len(ps_records), BATCH_SIZE):
            db.bulk_save_objects(ps_records[i:i+BATCH_SIZE])
            db.flush()
        logger.info(f"Inserted {len(ps_records)} PostStatus records")
        
        # Insert PostExpenses
        for i in range(0, len(pe_records), BATCH_SIZE):
            db.bulk_save_objects(pe_records[i:i+BATCH_SIZE])
            db.flush()
        logger.info(f"Inserted {len(pe_records)} PostExpenses records")
        
        # Insert UnitExpenditure
        for i in range(0, len(ue_records), BATCH_SIZE):
            db.bulk_save_objects(ue_records[i:i+BATCH_SIZE])
            db.flush()
        logger.info(f"Inserted {len(ue_records)} UnitExpenditure records")
        
        db.commit()
        logger.info(f"Successfully seeded fiscal year {fiscal_year} for {SUB_SCHEME_CODE}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed fiscal year {fiscal_year} for {SUB_SCHEME_CODE}: {e}", exc_info=True)
        raise
