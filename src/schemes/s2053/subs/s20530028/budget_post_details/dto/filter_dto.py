"""Filter DTOs for budget post details queries"""
from pydantic import BaseModel
from typing import Optional


class BudgetPostFilterDTO(BaseModel):
    """Filter parameters for budget post details list"""
    district: Optional[str] = None
    category: Optional[str] = None
    class_type: Optional[str] = None
    designation_search: Optional[str] = None
    page: int = 1
    page_size: int = 50
    
    class Config:
        from_attributes = True

