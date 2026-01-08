"""DTOs for post expenses"""
from pydantic import BaseModel
from typing import Optional


class PostExpensesRecordDataDTO(BaseModel):
    """DTO for record data API response"""
    found: bool
    id: Optional[int] = None
    filled_posts: int = 0
    vacant_posts: int = 0
    medical_expenses: int = 0
    festival_advance: int = 0
    swagram_maharashtra_darshan: int = 0
    nps_unified: float = 0.0
    other: int = 0


class PostExpensesUpdateDTO(BaseModel):
    """DTO for inline update request"""
    id: int
    filled_posts: int = 0
    vacant_posts: int = 0
    medical_expenses: int = 0
    festival_advance: int = 0
    swagram_maharashtra_darshan: int = 0
    nps_unified: float = 0.0
    other: int = 0


class PostExpensesFormUpdateDTO(BaseModel):
    """DTO for form-based update"""
    district: str
    category: str
    class_type: str
    filled_posts: Optional[int] = None
    vacant_posts: Optional[int] = None
    medical_expenses: Optional[int] = None
    festival_advance: Optional[int] = None
    swagram_maharashtra_darshan: Optional[int] = None
    other: Optional[int] = None
    nps_unified: Optional[float] = None

