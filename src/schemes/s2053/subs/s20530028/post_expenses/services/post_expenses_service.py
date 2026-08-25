"""Main service for post expenses business logic"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Tuple
from ..repositories.post_expenses_repository import PostExpensesRepository
from ..dto.post_expenses_dto import PostExpensesRecordDataDTO, PostExpensesUpdateDTO, PostExpensesFormUpdateDTO
from ..dto.filter_dto import PostExpensesFilterDTO
from ..utils.validators import (
    validate_filled_against_sanctioned,
    validate_numeric_inputs,
    validate_nps_value,
)
from .nps_component_service import NPSComponentService
from ...models import PostExpenses


class PostExpensesService:
    """Service for post expenses business logic"""
    
    EXPENSE_COLUMNS = [
        'filled_posts', 'vacant_posts', 'medical_expenses', 'festival_advance',
        'swagram_maharashtra_darshan', 'nps', 'seventh_pay_commission_difference',
        'seventh_pay_commission_difference_nps', 'other'
    ]
    
    def __init__(self, repository: PostExpensesRepository):
        """Initialize service with repository"""
        self.repository = repository
    
    def get_classes(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[str]:
        """Get distinct classes matching filters"""
        try:
            return self.repository.get_classes_by_filters(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district,
                category=category
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get classes: {str(e)}")
    
    def get_record_data(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        category: str,
        class_type: str
    ) -> PostExpensesRecordDataDTO:
        """Get record data for API response"""
        try:
            record = self.repository.get_record_data(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district,
                category=category,
                class_type=class_type
            )
            
            if not record:
                return PostExpensesRecordDataDTO(found=False)
            
            # Get unified NPS value using NPS component service
            nps_unified = NPSComponentService.get_nps_value(record)
            
            return PostExpensesRecordDataDTO(
                found=True,
                id=record.id,
                filled_posts=record.filled_posts or 0,
                vacant_posts=record.vacant_posts or 0,
                medical_expenses=record.medical_expenses or 0,
                festival_advance=record.festival_advance or 0,
                swagram_maharashtra_darshan=record.swagram_maharashtra_darshan or 0,
                nps_unified=nps_unified or 0.0,
                other=record.other or 0
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get record data: {str(e)}")
    
    def get_list(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        auth_level: str,
        auth_unit: Optional[str],
        filters: PostExpensesFilterDTO
    ) -> Tuple[List[PostExpenses], int]:
        """Get paginated list of post expenses"""
        try:
            return self.repository.get_by_filters(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                auth_level=auth_level,
                auth_unit=auth_unit,
                district=filters.district,
                category=filters.category,
                class_type=filters.class_type,
                page=filters.page,
                page_size=filters.page_size
            )
        except Exception as e:
            raise ConnectionError(f"Failed to get list: {str(e)}")
    
    def get_by_id(self, record_id: int, sub_scheme_code: str) -> Optional[PostExpenses]:
        """Get record by ID"""
        try:
            return self.repository.get_by_id(record_id, sub_scheme_code)
        except Exception as e:
            raise ConnectionError(f"Failed to get record: {str(e)}")
    
    def update_inline(
        self,
        update_dto: PostExpensesUpdateDTO,
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
            vals_to_check = [
                update_dto.filled_posts,
                update_dto.medical_expenses,
                update_dto.festival_advance,
                update_dto.swagram_maharashtra_darshan,
                update_dto.nps_unified,
                update_dto.other,
            ]
            is_valid, error_msg = validate_numeric_inputs(*vals_to_check)
            if not is_valid:
                raise ValueError(error_msg)
            is_valid, error_msg = validate_filled_against_sanctioned(
                self.repository.session, record, update_dto.filled_posts
            )
            if not is_valid:
                raise ValueError(error_msg)
            
            # Get old values for audit
            old_values = {
                "filled_posts": record.filled_posts,
                "vacant_posts": record.vacant_posts,
                "medical_expenses": record.medical_expenses,
                "festival_advance": record.festival_advance,
                "swagram_maharashtra_darshan": record.swagram_maharashtra_darshan,
                "seventh_pay_commission_difference_nps": record.seventh_pay_commission_difference_nps,
                "nps": record.nps,
                "seventh_pay_commission_difference": record.seventh_pay_commission_difference,
                "other": record.other,
            }
            
            # Update record
            record.filled_posts = update_dto.filled_posts
            record.medical_expenses = update_dto.medical_expenses
            record.festival_advance = update_dto.festival_advance
            record.swagram_maharashtra_darshan = update_dto.swagram_maharashtra_darshan
            record.other = update_dto.other
            
            # Set NPS value using NPS component service
            NPSComponentService.set_nps_value(record, update_dto.nps_unified)
            
            self.repository.update(record)
            
            # Get new values for audit
            new_values = {
                "filled_posts": record.filled_posts,
                "vacant_posts": record.vacant_posts,
                "medical_expenses": record.medical_expenses,
                "festival_advance": record.festival_advance,
                "swagram_maharashtra_darshan": record.swagram_maharashtra_darshan,
                "seventh_pay_commission_difference_nps": record.seventh_pay_commission_difference_nps,
                "nps": record.nps,
                "seventh_pay_commission_difference": record.seventh_pay_commission_difference,
                "other": record.other,
            }
            
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
        update_dto: PostExpensesFormUpdateDTO
    ) -> Tuple[PostExpenses, Dict[str, Any]]:
        """Update record via form submission with district sync"""
        try:
            record = self.repository.get_by_id(record_id, sub_scheme_code)
            if not record:
                raise ValueError("Record not found")

            values = (
                update_dto.filled_posts,
                update_dto.medical_expenses,
                update_dto.festival_advance,
                update_dto.swagram_maharashtra_darshan,
                update_dto.nps_unified,
                update_dto.other,
            )
            is_valid, error_msg = validate_numeric_inputs(
                *(value for value in values if value is not None)
            )
            if not is_valid:
                raise ValueError(error_msg)
            if update_dto.filled_posts is not None:
                is_valid, error_msg = validate_filled_against_sanctioned(
                    self.repository.session, record, update_dto.filled_posts
                )
                if not is_valid:
                    raise ValueError(error_msg)
            
            # Update basic fields
            if update_dto.filled_posts is not None:
                record.filled_posts = update_dto.filled_posts
            if update_dto.medical_expenses is not None:
                record.medical_expenses = update_dto.medical_expenses
            if update_dto.festival_advance is not None:
                record.festival_advance = update_dto.festival_advance
            if update_dto.swagram_maharashtra_darshan is not None:
                record.swagram_maharashtra_darshan = update_dto.swagram_maharashtra_darshan
            if update_dto.other is not None:
                record.other = update_dto.other
            
            # Update district, category, class_type if provided
            if update_dto.district:
                record.district = update_dto.district
            if update_dto.category:
                record.category = update_dto.category
            if update_dto.class_type:
                record.class_type = update_dto.class_type
            
            # Handle NPS value
            if update_dto.nps_unified is not None:
                NPSComponentService.set_nps_value(record, update_dto.nps_unified, update_dto.district)
            
            # Sync expense fields across district (if medical_expenses, festival_advance, etc. changed)
            sync_candidates = {}
            if update_dto.medical_expenses is not None:
                sync_candidates["medical_expenses"] = update_dto.medical_expenses
            if update_dto.festival_advance is not None:
                sync_candidates["festival_advance"] = update_dto.festival_advance
            if update_dto.swagram_maharashtra_darshan is not None:
                sync_candidates["swagram_maharashtra_darshan"] = update_dto.swagram_maharashtra_darshan
            if update_dto.other is not None:
                sync_candidates["other"] = update_dto.other
            
            # Add NPS field to sync if updated
            if update_dto.nps_unified is not None:
                nps_field = NPSComponentService.get_nps_field_name(update_dto.district)
                sync_candidates[nps_field] = update_dto.nps_unified
                # Clear other NPS fields
                if nps_field != "nps":
                    sync_candidates["nps"] = None
                if nps_field != "seventh_pay_commission_difference":
                    sync_candidates["seventh_pay_commission_difference"] = None
                if nps_field != "seventh_pay_commission_difference_nps":
                    sync_candidates["seventh_pay_commission_difference_nps"] = None
            
            sync_update = {k: v for k, v in sync_candidates.items() if v is not None}
            return self.repository.update(record), sync_update
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ConnectionError(f"Update failed: {str(e)}")

