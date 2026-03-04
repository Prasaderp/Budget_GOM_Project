"""Pydantic schemas for sub-scheme 76101871 district-wise expenditure."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import SCHEME_CODE, SUB_SCHEME_CODE
from .config import KONKAN_DISTRICTS


class DistrictExpenditureBase(BaseModel):
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = Field(default=SCHEME_CODE, min_length=1, max_length=10)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE, min_length=1, max_length=15)
    district: Optional[str] = None

    expenditure_prev3: Optional[int] = 0
    expenditure_prev2: Optional[int] = 0
    expenditure_prev1: Optional[int] = 0

    budget_estimate: Optional[int] = 0
    revised_estimate: Optional[int] = 0
    budget_estimate_next: Optional[int] = 0

    remarks: Optional[str] = None

    @field_validator(
        "expenditure_prev3",
        "expenditure_prev2",
        "expenditure_prev1",
        "budget_estimate",
        "revised_estimate",
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


class DistrictExpenditureCreate(DistrictExpenditureBase):
    district: str

    @field_validator("district")
    @classmethod
    def validate_district(cls, v: str) -> str:
        if v not in KONKAN_DISTRICTS:
            raise ValueError("Invalid district for 76101871")
        return v


class DistrictExpenditureUpdate(DistrictExpenditureBase):
    pass


class DistrictExpenditureResponse(DistrictExpenditureBase):
    id: int
    model_config = ConfigDict(from_attributes=True)



