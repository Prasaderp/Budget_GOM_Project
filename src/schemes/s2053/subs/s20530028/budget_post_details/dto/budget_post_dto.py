"""DTOs for budget post details"""
from pydantic import BaseModel
from typing import Optional


class BudgetPostRecordDataDTO(BaseModel):
    """DTO for record data API response"""
    found: bool
    id: Optional[int] = None
    sanctioned_posts_2024_25: int = 0
    sanctioned_posts_2025_26: int = 0
    special_pay: int = 0
    basic_pay: float = 0
    grade_pay: int = 0
    local_supplementary_allowance: int = 0
    vehicle_allowance: int = 0
    washing_allowance: int = 0
    cash_allowance: int = 0
    footwear_allowance_other: int = 0
    hra_rate: str = 'X'


class BudgetPostUpdateDTO(BaseModel):
    """DTO for inline update request"""
    id: int
    sanctioned_posts_2024_25: int = 0
    sanctioned_posts_2025_26: int = 0
    special_pay: int = 0
    basic_pay: float = 0
    grade_pay: int = 0
    local_supplementary_allowance: int = 0
    vehicle_allowance: int = 0
    washing_allowance: int = 0
    cash_allowance: int = 0
    footwear_allowance_other: int = 0
    hra_rate: str = 'X'


class BudgetPostFormUpdateDTO(BaseModel):
    """DTO for form-based update"""
    district: str
    category: str
    class_type: str
    designation: str
    sanctioned_posts_2024_25: Optional[int] = None
    sanctioned_posts_2025_26: Optional[int] = None
    special_pay: Optional[int] = None
    basic_pay: Optional[float] = None
    grade_pay: Optional[int] = None
    local_supplementary_allowance: Optional[int] = None
    vehicle_allowance: Optional[int] = None
    washing_allowance: Optional[int] = None
    cash_allowance: Optional[int] = None
    footwear_allowance_other: Optional[int] = None
    hra_rate: Optional[str] = 'X'

