"""Filter DTOs for unit expenditure"""
from pydantic import BaseModel
from typing import Optional


class UnitExpenditureFilterDTO(BaseModel):
    """Filter parameters for unit expenditure queries"""
    fiscal_year: str
    sub_scheme_code: str
    district: Optional[str] = None
    primary_unit: Optional[str] = None
    page: int = 1
    page_size: int = 50

