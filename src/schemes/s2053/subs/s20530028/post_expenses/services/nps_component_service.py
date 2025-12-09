"""Service for NPS component mapping logic"""
from typing import Optional
from ...config import POST_EXPENSES_DISTRICT_COMPONENT


class NPSComponentService:
    """Service for determining which NPS field to use based on district"""
    
    @staticmethod
    def get_active_component(district: Optional[str]) -> Optional[str]:
        """
        Get the active NPS component for a district
        
        Returns:
            Component name: "SeventhPayCommissionDifferenceNPS", "SeventhPayCommissionDifference", "NPS", or None
        """
        if not district:
            return None
        return POST_EXPENSES_DISTRICT_COMPONENT.get(district, "NPS")
    
    @staticmethod
    def get_nps_value(record, district: Optional[str] = None) -> Optional[float]:
        """
        Get the unified NPS value from a record based on district component
        
        Args:
            record: PostExpenses model instance
            district: District name (if not provided, uses record.district)
            
        Returns:
            Unified NPS value (float) or None
        """
        if not record:
            return None
        
        district_name = district or record.district
        active_component = NPSComponentService.get_active_component(district_name)
        
        if active_component == "SeventhPayCommissionDifferenceNPS":
            return record.seventh_pay_commission_difference_nps or 0.0
        elif active_component == "SeventhPayCommissionDifference":
            return record.seventh_pay_commission_difference or 0.0
        else:
            return record.nps or 0.0
    
    @staticmethod
    def set_nps_value(
        record,
        nps_unified: Optional[float],
        district: Optional[str] = None
    ) -> None:
        """
        Set the unified NPS value to the appropriate field based on district component
        
        Args:
            record: PostExpenses model instance to update
            nps_unified: Unified NPS value to set
            district: District name (if not provided, uses record.district)
        """
        if not record:
            return
        
        district_name = district or record.district
        active_component = NPSComponentService.get_active_component(district_name)
        
        # Clear all NPS fields first
        record.nps = None
        record.seventh_pay_commission_difference = None
        record.seventh_pay_commission_difference_nps = None
        
        # Set the appropriate field based on component
        if active_component == "SeventhPayCommissionDifferenceNPS":
            record.seventh_pay_commission_difference_nps = nps_unified
        elif active_component == "SeventhPayCommissionDifference":
            record.seventh_pay_commission_difference = nps_unified
        else:
            record.nps = nps_unified
    
    @staticmethod
    def get_nps_field_name(district: Optional[str]) -> str:
        """
        Get the database field name for NPS based on district component
        
        Returns:
            Field name: "nps", "seventh_pay_commission_difference", or "seventh_pay_commission_difference_nps"
        """
        active_component = NPSComponentService.get_active_component(district)
        
        if active_component == "SeventhPayCommissionDifferenceNPS":
            return "seventh_pay_commission_difference_nps"
        elif active_component == "SeventhPayCommissionDifference":
            return "seventh_pay_commission_difference"
        else:
            return "nps"

