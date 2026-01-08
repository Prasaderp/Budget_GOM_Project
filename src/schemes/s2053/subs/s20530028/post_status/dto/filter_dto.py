"""Filter DTOs for Post Status"""
from typing import Optional
from pydantic import BaseModel, Field


class PostStatusFilterDTO(BaseModel):
    """DTO for post status filter parameters"""
    district: Optional[str] = None
    category: Optional[str] = None
    class_type: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)

