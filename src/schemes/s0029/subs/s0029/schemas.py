"""Pydantic schemas for scheme 0029."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import SCHEME_CODE, SUB_SCHEME_CODE
from .config import get_table_section, KONKAN_DISTRICTS


class DistrictRevenueBase(BaseModel):
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = Field(default=SCHEME_CODE, min_length=1, max_length=10)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE, min_length=1, max_length=15)
    table_section_code: Optional[str] = None
    district: Optional[str] = None

    actual_prev3: Optional[int] = 0
    actual_prev2: Optional[int] = 0
    actual_prev1: Optional[int] = 0

    budget_estimate_curr: Optional[int] = 0
    revised_estimate_curr: Optional[int] = 0
    budget_estimate_next: Optional[int] = 0

    @field_validator(
        "actual_prev3",
        "actual_prev2",
        "actual_prev1",
        "budget_estimate_curr",
        "revised_estimate_curr",
        "budget_estimate_next",
    )
    @classmethod
    def non_negative_int(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("Value must be non-negative")
        if v > 999_999_999_999:
            raise ValueError("Value too large")
        return v


class DistrictRevenueCreate(DistrictRevenueBase):
    table_section_code: str
    district: str

    @field_validator("table_section_code")
    @classmethod
    def validate_table_section(cls, v: str) -> str:
        section = get_table_section(v)
        if not section:
            raise ValueError("Invalid table section code")
        return v

    @field_validator("district")
    @classmethod
    def validate_district(cls, v: str) -> str:
        if not v or v not in KONKAN_DISTRICTS:
            raise ValueError("Invalid district for 0029")
        return v


class DistrictRevenueUpdate(DistrictRevenueBase):
    pass


class DistrictRevenueResponse(DistrictRevenueBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

