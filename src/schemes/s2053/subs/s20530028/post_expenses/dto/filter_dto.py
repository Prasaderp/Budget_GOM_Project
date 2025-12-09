"""Filter DTOs for post expenses queries"""
from pydantic import BaseModel
from typing import Optional


class PostExpensesFilterDTO(BaseModel):
    """Filter parameters for post expenses list"""
    district: Optional[str] = None
    category: Optional[str] = None
    class_type: Optional[str] = None
    page: int = 1
    page_size: int = 50
    
    class Config:
        from_attributes = True

