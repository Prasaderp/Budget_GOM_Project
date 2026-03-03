"""Main service for unit expenditure business logic"""
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple, Dict, Any
from ..repositories.unit_expenditure_repository import UnitExpenditureRepository
from ..dto.unit_expenditure_dto import (
    UnitExpenditureRecordDataDTO,
    UnitExpenditureInlineUpdateDTO,
    UnitExpenditureFormUpdateDTO
)
from ..dto.filter_dto import UnitExpenditureFilterDTO
from ..utils.validators import validate_unit_expenditure_inputs
from ..utils.formatters import get_internal_data_keys
from ...models import UnitExpenditure
from ...helpers import (
    check_edit_permission_for_scheme,
    validate_access_control,
    invalidate_scheme_cache,
    log_audit_async,
    get_request_info
)
from ...config import SCHEME_CONFIG
from src.utils_timing import check_data_filling_allowed
from fastapi import Request


class UnitExpenditureService:
    """Service for unit expenditure business logic"""
    
    def __init__(self, repository: UnitExpenditureRepository):
        """Initialize service with repository"""
        self.repository = repository
    
    def get_primary_units(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None
    ) -> List[str]:
        """Get distinct primary units matching filters"""
        try:
            return self.repository.get_primary_units(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get primary units: {str(e)}")
    
    def get_record_data(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        primary_unit: str
    ) -> UnitExpenditureRecordDataDTO:
        """Get record data for API response"""
        try:
            record = self.repository.get_record_data(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district,
                primary_unit=primary_unit
            )
            
            if not record:
                return UnitExpenditureRecordDataDTO(found=False)
            
            return UnitExpenditureRecordDataDTO(
                found=True,
                id=record.id,
                expenditure_prev4=record.expenditure_prev4 or 0,
                expenditure_prev3=record.expenditure_prev3 or 0,
                expenditure_prev2=record.expenditure_prev2 or 0,
                budget_prev1=record.budget_prev1 or 0,
                forecast_prev1=record.forecast_prev1 or 0,
                budget_curr_estimating_officer=record.budget_curr_estimating_officer or 0,
                budget_curr_controlling_officer=record.budget_curr_controlling_officer or 0,
                budget_curr_admin_dept=record.budget_curr_admin_dept or 0,
                budget_curr_finance_dept=record.budget_curr_finance_dept or 0
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get record data: {str(e)}")
    
    def get_list(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        auth_level: str,
        auth_unit: Optional[str],
        filters: UnitExpenditureFilterDTO
    ) -> Tuple[List[UnitExpenditure], int]:
        """Get paginated list of unit expenditure records"""
        try:
            return self.repository.get_by_filters(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                auth_level=auth_level,
                auth_unit=auth_unit,
                district=filters.district,
                primary_unit=filters.primary_unit,
                page=filters.page,
                page_size=filters.page_size
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get list: {str(e)}")
    
    def get_by_id(
        self,
        record_id: int,
        sub_scheme_code: str
    ) -> Optional[UnitExpenditure]:
        """Get unit expenditure record by ID"""
        try:
            return self.repository.get_by_id(record_id, sub_scheme_code)
        except Exception as e:
            raise ConnectionError(f"Failed to get record: {str(e)}")
    
    def update_inline(
        self,
        request: Request,
        update_dto: UnitExpenditureInlineUpdateDTO,
        sub_scheme_code: str,
        auth_role: str,
        auth_level: str,
        auth_unit: str,
        auth_user: str
    ) -> Dict[str, Any]:
        """
        Update unit expenditure record inline (from API)
        
        Returns:
            Dict with success status and message
        """
        # Permission checks
        if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, self.repository.session):
            return {"success": False, "message": "Forbidden"}
        
        is_allowed, timing_msg = check_data_filling_allowed(
            self.repository.session, auth_level, auth_role, SCHEME_CONFIG.code
        )
        if not is_allowed:
            return {"success": False, "message": timing_msg or "Data filling period expired"}
        
        # Get record
        record = self.repository.get_by_id(update_dto.id, sub_scheme_code)
        if not record:
            return {"success": False, "message": "Record not found"}
        
        # Access control
        allowed, error_msg = validate_access_control(
            record.district, auth_level, auth_unit, self.repository.session
        )
        if not allowed:
            return {"success": False, "message": error_msg}
        
        # Validate inputs
        is_valid, error_msg = validate_unit_expenditure_inputs(
            expenditure_prev4=update_dto.expenditure_prev4,
            expenditure_prev3=update_dto.expenditure_prev3,
            expenditure_prev2=update_dto.expenditure_prev2,
            budget_prev1=update_dto.budget_prev1,
            forecast_prev1=update_dto.forecast_prev1,
            budget_curr_estimating_officer=update_dto.budget_curr_estimating_officer,
            budget_curr_controlling_officer=update_dto.budget_curr_controlling_officer,
            budget_curr_admin_dept=update_dto.budget_curr_admin_dept,
            budget_curr_finance_dept=update_dto.budget_curr_finance_dept
        )
        if not is_valid:
            return {"success": False, "message": error_msg}
        
        # Store old values for audit
        internal_keys = get_internal_data_keys()
        old_vals = {k: getattr(record, k) for k in internal_keys}
        
        # Update record
        record.expenditure_prev4 = update_dto.expenditure_prev4
        record.expenditure_prev3 = update_dto.expenditure_prev3
        record.expenditure_prev2 = update_dto.expenditure_prev2
        record.budget_prev1 = update_dto.budget_prev1
        record.forecast_prev1 = update_dto.forecast_prev1
        record.budget_curr_estimating_officer = update_dto.budget_curr_estimating_officer
        record.budget_curr_controlling_officer = update_dto.budget_curr_controlling_officer
        record.budget_curr_admin_dept = update_dto.budget_curr_admin_dept
        record.budget_curr_finance_dept = update_dto.budget_curr_finance_dept
        
        self.repository.update(record)
        
        # Invalidate cache
        invalidate_scheme_cache(record.district, patterns=["unit_exp_summary", "unit_exp_charts"])
        
        # Audit log
        new_vals = {k: getattr(record, k) for k in internal_keys}
        req_info = get_request_info(request)
        log_audit_async(
            "unit_expenditure",
            update_dto.id,
            auth_user,
            old_vals,
            new_vals,
            req_info
        )
        
        return {"success": True, "message": "अपडेट यशस्वी"}
    
    def update_form(
        self,
        request: Request,
        update_dto: UnitExpenditureFormUpdateDTO,
        sub_scheme_code: str,
        auth_role: str,
        auth_level: str,
        auth_unit: str
    ) -> UnitExpenditure:
        """
        Update unit expenditure record from form
        
        Returns:
            Updated record
        """
        # Get record
        record = self.repository.get_by_id(update_dto.id, sub_scheme_code)
        if not record:
            raise ValueError(f"प्रपत्र अ ID {update_dto.id} सापडला नाही")
        
        # Update fields
        record.unit_account = update_dto.unit_account
        record.district = update_dto.district
        
        if update_dto.expenditure_prev4 is not None:
            record.expenditure_prev4 = update_dto.expenditure_prev4
        if update_dto.expenditure_prev3 is not None:
            record.expenditure_prev3 = update_dto.expenditure_prev3
        if update_dto.expenditure_prev2 is not None:
            record.expenditure_prev2 = update_dto.expenditure_prev2
        if update_dto.budget_prev1 is not None:
            record.budget_prev1 = update_dto.budget_prev1
        if update_dto.forecast_prev1 is not None:
            record.forecast_prev1 = update_dto.forecast_prev1
        if update_dto.budget_curr_estimating_officer is not None:
            record.budget_curr_estimating_officer = update_dto.budget_curr_estimating_officer
        
        # Only update these if not district level user
        if auth_level != 'district':
            if update_dto.budget_curr_controlling_officer is not None:
                record.budget_curr_controlling_officer = update_dto.budget_curr_controlling_officer
            if update_dto.budget_curr_admin_dept is not None:
                record.budget_curr_admin_dept = update_dto.budget_curr_admin_dept
            if update_dto.budget_curr_finance_dept is not None:
                record.budget_curr_finance_dept = update_dto.budget_curr_finance_dept
        
        self.repository.update(record)
        
        # Invalidate cache
        invalidate_scheme_cache(update_dto.district, patterns=["unit_exp_summary", "unit_exp_charts"])
        
        return record

