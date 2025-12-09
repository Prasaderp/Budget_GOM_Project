"""Service for Post Status business logic"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from fastapi import Request

from ...helpers import check_edit_permission_for_scheme, validate_access_control
from ...shared.services.audit_service import AuditService
from ...shared.utils.request_utils import get_request_info
from src.utils_timing import check_data_filling_allowed
from ...config import SCHEME_CONFIG
from ..repositories.post_status_repository import PostStatusRepository
from ..dto.post_status_dto import PostStatusUpdateDTO, PostStatusRecordDTO
from ..utils.validators import validate_post_status_inputs
from ...models import PostStatus


class PostStatusService:
    """Service for Post Status business logic"""
    
    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.repository = PostStatusRepository(db)
        self.db = db
    
    def get_statuses(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None
    ) -> list[str]:
        """Get distinct statuses matching filters"""
        return self.repository.get_statuses(
            fiscal_year, sub_scheme_code, district, category, class_type
        )
    
    def get_record_data(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        category: str,
        class_type: str,
        status: str
    ) -> PostStatusRecordDTO:
        """Get record data by natural key"""
        record = self.repository.get_by_natural_key(
            fiscal_year, sub_scheme_code, district, category, class_type, status
        )
        
        if not record:
            return PostStatusRecordDTO(found=False)
        
        return PostStatusRecordDTO(
            found=True,
            id=record.id,
            posts=record.posts or 0,
            salary=record.salary or 0,
            grade_pay=record.grade_pay or 0,
            special_pay=record.special_pay or 0,
            dearness_allowance=record.dearness_allowance or 0,
            local_supplementary_allowance=record.local_supplementary_allowance or 0,
            house_rent_allowance=record.house_rent_allowance or 0,
            travel_allowance=record.travel_allowance or 0,
            other=record.other or 0
        )
    
    def update_inline(
        self,
        record_id: int,
        sub_scheme_code: str,
        update_data: PostStatusUpdateDTO,
        auth_role: str,
        auth_level: str,
        auth_unit: str,
        auth_user: str,
        request: Request
    ) -> Dict[str, Any]:
        """
        Update post status record inline
        
        Returns:
            dict with 'success' and 'message' keys
        """
        # Permission check
        if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, self.db):
            return {"success": False, "message": "Forbidden"}
        
        # Timing check
        is_allowed, timing_msg = check_data_filling_allowed(
            self.db, auth_level, auth_role, SCHEME_CONFIG.code
        )
        if not is_allowed:
            return {
                "success": False,
                "message": timing_msg or "Data filling period expired"
            }
        
        # Get record
        record = self.repository.get_by_id(record_id, sub_scheme_code)
        if not record:
            return {"success": False, "message": "Record not found"}
        
        # Access control validation
        allowed, error_msg = validate_access_control(
            record.district, auth_level, auth_unit, self.db
        )
        if not allowed:
            return {"success": False, "message": error_msg}
        
        # Validate inputs
        is_valid, error_msg = validate_post_status_inputs(
            posts=update_data.posts,
            salary=update_data.salary,
            grade_pay=update_data.grade_pay,
            special_pay=update_data.special_pay,
            dearness_allowance=update_data.dearness_allowance,
            local_supplementary_allowance=update_data.local_supplementary_allowance,
            house_rent_allowance=update_data.house_rent_allowance,
            travel_allowance=update_data.travel_allowance,
            other=update_data.other
        )
        if not is_valid:
            return {"success": False, "message": error_msg}
        
        # Store old values for audit
        old_values = {
            "posts": record.posts,
            "salary": record.salary,
            "grade_pay": record.grade_pay,
            "special_pay": record.special_pay,
            "dearness_allowance": record.dearness_allowance,
            "local_supplementary_allowance": record.local_supplementary_allowance,
            "house_rent_allowance": record.house_rent_allowance,
            "travel_allowance": record.travel_allowance,
            "other": record.other
        }
        
        # Update record
        if update_data.posts is not None:
            record.posts = update_data.posts
        if update_data.salary is not None:
            record.salary = update_data.salary
        if update_data.grade_pay is not None:
            record.grade_pay = update_data.grade_pay
        if update_data.special_pay is not None:
            record.special_pay = update_data.special_pay
        if update_data.dearness_allowance is not None:
            record.dearness_allowance = update_data.dearness_allowance
        if update_data.local_supplementary_allowance is not None:
            record.local_supplementary_allowance = update_data.local_supplementary_allowance
        if update_data.house_rent_allowance is not None:
            record.house_rent_allowance = update_data.house_rent_allowance
        if update_data.travel_allowance is not None:
            record.travel_allowance = update_data.travel_allowance
        if update_data.other is not None:
            record.other = update_data.other
        
        new_values = {
            "posts": record.posts,
            "salary": record.salary,
            "grade_pay": record.grade_pay,
            "special_pay": record.special_pay,
            "dearness_allowance": record.dearness_allowance,
            "local_supplementary_allowance": record.local_supplementary_allowance,
            "house_rent_allowance": record.house_rent_allowance,
            "travel_allowance": record.travel_allowance,
            "other": record.other
        }
        
        # Audit log
        try:
            req_info = get_request_info(request)
            AuditService.log_edit(
                self.db, request, "post_status", record_id, auth_user, old_values, new_values
            )
        except Exception:
            pass  # Don't fail if audit logging fails
        
        # Commit
        self.repository.update(record)
        
        return {"success": True, "message": "अपडेट यशस्वी"}
    
    def get_by_id(self, record_id: int, sub_scheme_code: str) -> Optional[PostStatus]:
        """Get post status record by ID"""
        return self.repository.get_by_id(record_id, sub_scheme_code)
    
    def update_record(
        self,
        record: PostStatus,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
        status: Optional[str] = None,
        posts: Optional[int] = None,
        salary: Optional[int] = None,
        grade_pay: Optional[int] = None,
        special_pay: Optional[int] = None,
        dearness_allowance: Optional[int] = None,
        local_supplementary_allowance: Optional[int] = None,
        house_rent_allowance: Optional[int] = None,
        travel_allowance: Optional[int] = None,
        other: Optional[int] = None
    ) -> PostStatus:
        """Update post status record with provided fields"""
        if district is not None:
            record.district = district
        if category is not None:
            record.category = category
        if class_type is not None:
            record.class_type = class_type
        if status is not None:
            record.status = status
        if posts is not None:
            record.posts = posts
        if salary is not None:
            record.salary = salary
        if grade_pay is not None:
            record.grade_pay = grade_pay
        if special_pay is not None:
            record.special_pay = special_pay
        if dearness_allowance is not None:
            record.dearness_allowance = dearness_allowance
        if local_supplementary_allowance is not None:
            record.local_supplementary_allowance = local_supplementary_allowance
        if house_rent_allowance is not None:
            record.house_rent_allowance = house_rent_allowance
        if travel_allowance is not None:
            record.travel_allowance = travel_allowance
        if other is not None:
            record.other = other
        
        return self.repository.update(record)

