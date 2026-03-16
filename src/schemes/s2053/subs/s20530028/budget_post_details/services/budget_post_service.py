"""Main service for budget post details business logic"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Tuple
from ..repositories.budget_post_repository import BudgetPostRepository
from ..dto.budget_post_dto import BudgetPostRecordDataDTO, BudgetPostUpdateDTO, BudgetPostFormUpdateDTO
from ..dto.filter_dto import BudgetPostFilterDTO
from ..utils.formatters import format_basic_pay
from ..utils.validators import validate_numeric_inputs, validate_hra_rate
from ...models import BudgetPostDetails


class BudgetPostService:
    """Service for budget post details business logic"""
    
    BUDGET_COLUMNS = [
        'sanctioned_posts_prev1', 'sanctioned_posts_curr', 'special_pay', 'basic_pay',
        'grade_pay', 'local_supplementary_allowance', 'vehicle_allowance',
        'washing_allowance', 'cash_allowance', 'footwear_allowance_other', 'hra_rate'
    ]
    
    def __init__(self, repository: BudgetPostRepository):
        """Initialize service with repository"""
        self.repository = repository
    
    def get_designations(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None
    ) -> List[str]:
        """Get distinct designations matching filters"""
        try:
            return self.repository.get_designations(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district,
                category=category,
                class_type=class_type
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get designations: {str(e)}")
    
    def get_record_data(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        category: str,
        class_type: str,
        designation: str
    ) -> BudgetPostRecordDataDTO:
        """Get record data for API response"""
        try:
            record = self.repository.get_record_data(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district,
                category=category,
                class_type=class_type,
                designation=designation
            )
            
            if not record:
                return BudgetPostRecordDataDTO(found=False)
            
            return BudgetPostRecordDataDTO(
                found=True,
                id=record.id,
                sanctioned_posts_prev1=record.sanctioned_posts_prev1 or 0,
                sanctioned_posts_curr=record.sanctioned_posts_curr or 0,
                special_pay=record.special_pay or 0,
                basic_pay=format_basic_pay(record.basic_pay),
                grade_pay=record.grade_pay or 0,
                local_supplementary_allowance=record.local_supplementary_allowance or 0,
                vehicle_allowance=record.vehicle_allowance or 0,
                washing_allowance=record.washing_allowance or 0,
                cash_allowance=record.cash_allowance or 0,
                footwear_allowance_other=record.footwear_allowance_other or 0,
                hra_rate=record.hra_rate or 'X'
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get record data: {str(e)}")
    
    def get_list(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        auth_level: str,
        auth_unit: Optional[str],
        filters: BudgetPostFilterDTO
    ) -> Tuple[List[BudgetPostDetails], int]:
        """Get paginated list of budget post details"""
        try:
            return self.repository.get_by_filters(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                auth_level=auth_level,
                auth_unit=auth_unit,
                district=filters.district,
                category=filters.category,
                class_type=filters.class_type,
                designation_search=filters.designation_search,
                page=filters.page,
                page_size=filters.page_size
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get list: {str(e)}")
    
    def get_by_id(self, record_id: int, sub_scheme_code: str) -> Optional[BudgetPostDetails]:
        """Get record by ID"""
        try:
            return self.repository.get_by_id(record_id, sub_scheme_code)
        except Exception as e:
            raise ConnectionError(f"Failed to get record: {str(e)}")
    
    def update_inline(
        self,
        update_dto: BudgetPostUpdateDTO,
        sub_scheme_code: str
    ) -> Dict[str, Any]:
        """
        Update record via inline API
        
        Returns:
            Dict with old and new values for audit
        """
        try:
            record = self.repository.get_by_id(update_dto.id, sub_scheme_code)
            if not record:
                raise ValueError("Record not found")
            
            # Validate inputs
            vals_int = [
                update_dto.sanctioned_posts_prev1,
                update_dto.sanctioned_posts_curr,
                update_dto.special_pay,
                update_dto.grade_pay,
                update_dto.local_supplementary_allowance,
                update_dto.vehicle_allowance,
                update_dto.washing_allowance,
                update_dto.cash_allowance,
                update_dto.footwear_allowance_other
            ]
            is_valid, error_msg = validate_numeric_inputs(*vals_int, update_dto.basic_pay)
            if not is_valid:
                raise ValueError(error_msg)
            
            if update_dto.sanctioned_posts_curr is not None:
                from src.schemes.common.post_levels.repository import PostLevelRepository
                post_level_repo = PostLevelRepository(self.repository.session)
                level_count = post_level_repo.get_count(
                    record.id, sub_scheme_code,
                    record.__tablename__, record.fiscal_year
                )
                if update_dto.sanctioned_posts_curr < level_count:
                    raise ValueError(
                        f"मंजूर पदे {update_dto.sanctioned_posts_curr} ठेवता येत नाही कारण {level_count} स्तर आधीच आहेत. प्रथम स्तर हटवा."
                    )
            
            # Get old values for audit
            old_values = {k: getattr(record, k) for k in self.BUDGET_COLUMNS}
            
            # Update record
            record.sanctioned_posts_prev1 = update_dto.sanctioned_posts_prev1
            record.sanctioned_posts_curr = update_dto.sanctioned_posts_curr
            record.special_pay = update_dto.special_pay
            record.basic_pay = update_dto.basic_pay
            record.grade_pay = update_dto.grade_pay
            record.local_supplementary_allowance = update_dto.local_supplementary_allowance
            record.vehicle_allowance = update_dto.vehicle_allowance
            record.washing_allowance = update_dto.washing_allowance
            record.cash_allowance = update_dto.cash_allowance
            record.footwear_allowance_other = update_dto.footwear_allowance_other
            record.hra_rate = validate_hra_rate(update_dto.hra_rate)
            
            self.repository.update(record)
            
            # Get new values for audit
            new_values = {k: getattr(record, k) for k in self.BUDGET_COLUMNS}
            
            return {
                "old_values": old_values,
                "new_values": new_values,
                "record": record
            }
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ConnectionError(f"Update failed: {str(e)}")
    
    def update_form(
        self,
        record_id: int,
        sub_scheme_code: str,
        update_dto: BudgetPostFormUpdateDTO
    ) -> BudgetPostDetails:
        """Update record via form submission"""
        try:
            record = self.repository.get_by_id(record_id, sub_scheme_code)
            if not record:
                raise ValueError("Record not found")
            
            if update_dto.sanctioned_posts_curr is not None:
                from src.schemes.common.post_levels.repository import PostLevelRepository
                post_level_repo = PostLevelRepository(self.repository.session)
                level_count = post_level_repo.get_count(
                    record.id, sub_scheme_code,
                    record.__tablename__, record.fiscal_year
                )
                if update_dto.sanctioned_posts_curr < level_count:
                    raise ValueError(
                        f"मंजूर पदे {update_dto.sanctioned_posts_curr} ठेवता येत नाही कारण {level_count} स्तर आधीच आहेत. प्रथम स्तर हटवा."
                    )
            
            # Update fields (only non-None values)
            update_dict = update_dto.model_dump(exclude_unset=True, exclude_none=True)
            for key, value in update_dict.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            
            # Validate HRA rate
            if 'hra_rate' in update_dict:
                record.hra_rate = validate_hra_rate(update_dict['hra_rate'])
            
            return self.repository.update(record)
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ConnectionError(f"Update failed: {str(e)}")

