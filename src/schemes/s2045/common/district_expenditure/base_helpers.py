"""Shared helper utilities for s2045 district expenditure sub-schemes."""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from concurrent.futures import ThreadPoolExecutor
import logging

from src.utils_district import (
    get_district_from_taluka,
    check_edit_permission,
    validate_access_control as base_validate_access_control,
    get_request_info,
)

logger = logging.getLogger(__name__)

# Shared thread pool for audit logging
_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s2045_de")

MAX_INPUT_VALUE = 999_999_999_999


class DistrictExpenditureHelper:
    """
    Helper class for district expenditure operations.
    
    Each sub-scheme creates an instance with its specific configuration.
    """
    
    def __init__(
        self,
        sub_scheme_code: str,
        scheme_code: str,
        allowed_districts: List[str],
        model_class,
        table_name: str,
    ):
        self.sub_scheme_code = sub_scheme_code
        self.scheme_code = scheme_code
        self.allowed_districts = allowed_districts
        self.model_class = model_class
        self.table_name = table_name
    
    def get_allowed_districts_for_user(self, auth_level: str, auth_unit: str) -> List[str]:
        """Get list of districts user can access based on auth level."""
        if auth_level == "district" and auth_unit:
            return [auth_unit] if auth_unit in self.allowed_districts else []
        if auth_level == "taluka" and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            return [district_name] if district_name and district_name in self.allowed_districts else []
        if auth_level == "dco":
            return self.allowed_districts
        return self.allowed_districts
    
    def ensure_fiscal_year_seeded(self, db: Session, fiscal_year: str) -> None:
        """Ensure base rows exist for all configured districts for the given fiscal year."""
        exists = (
            db.query(self.model_class.id)
            .filter(
                self.model_class.fiscal_year == fiscal_year,
                self.model_class.sub_scheme_code == self.sub_scheme_code,
            )
            .limit(1)
            .first()
        )
        if exists:
            return
        
        rows = [
            self.model_class(
                fiscal_year=fiscal_year,
                scheme_code=self.scheme_code,
                sub_scheme_code=self.sub_scheme_code,
                district=d,
            )
            for d in self.allowed_districts
        ]
        db.bulk_save_objects(rows)
        db.commit()
    
    def check_edit_permission_for_scheme(
        self, auth_role: str, auth_level: str, auth_unit: str, db: Session
    ) -> bool:
        """Unified permission check for this sub-scheme."""
        return check_edit_permission(auth_role, auth_level, auth_unit, db, self.sub_scheme_code)
    
    def validate_access_control(
        self, record_district: str, auth_level: str, auth_unit: str, db: Session
    ):
        """Validate access control for a record."""
        return base_validate_access_control(record_district, auth_level, auth_unit, db)
    
    def validate_numeric_input(self, value: Optional[str], field_name: str = "field") -> int:
        """Validate and parse numeric input from form."""
        if value in (None, ""):
            return 0
        try:
            val = int(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for {field_name}"
            )
        if val < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Negative values not allowed for {field_name}"
            )
        if val > MAX_INPUT_VALUE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Value too large for {field_name}"
            )
        return val
    
    def log_audit_async(
        self,
        record_id: int,
        username: str,
        old_vals: Dict[str, Any],
        new_vals: Dict[str, Any],
        req_info: Dict[str, str],
        action: str = "UPDATE"
    ):
        """
        Async audit logging using thread pool.
        
        Uses the existing database module's SessionLocal for connection reuse.
        """
        table = self.table_name
        
        # Pre-compute changed fields to avoid work in background thread
        changed = [
            {"field": k, "old": old_vals.get(k), "new": new_vals.get(k)}
            for k in set(old_vals) | set(new_vals)
            if old_vals.get(k) != new_vals.get(k)
        ]
        if not changed:
            return  # No changes, skip audit
        
        def _log():
            try:
                from src.database import SessionLocal
                from src.models import AuditLog
                
                session = SessionLocal()
                try:
                    entry = AuditLog(
                        table_name=table,
                        record_id=record_id,
                        action=action,
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
            except Exception as e:
                logger.warning(f"Audit log failed for {table}:{record_id}: {e}")
        
        _audit_executor.submit(_log)
    
    def get_record_values(self, item) -> Dict[str, Any]:
        """Extract field values from a record for audit logging."""
        return {
            "district": item.district,
            "expenditure_prev3": item.expenditure_prev3,
            "expenditure_prev2": item.expenditure_prev2,
            "expenditure_prev1": item.expenditure_prev1,
            "budget_estimate_curr": item.budget_estimate_curr,
            "quarterly_expenditure_prev1": item.quarterly_expenditure_prev1,
            "budget_estimate_next": item.budget_estimate_next,
            "remarks": item.remarks,
        }


# Re-export for convenience
__all__ = ['DistrictExpenditureHelper', 'get_request_info']
