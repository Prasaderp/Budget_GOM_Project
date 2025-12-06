"""Pydantic schemas for sub-scheme 20750249 sub-head expenditure."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import SCHEME_CODE, SUB_SCHEME_CODE


class SubHeadExpenditureBase(BaseModel):
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = Field(default=SCHEME_CODE, min_length=1, max_length=10)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE, min_length=1, max_length=15)
    sub_head: Optional[str] = None

    expenditure_2022_23: Optional[int] = 0
    expenditure_2023_24: Optional[int] = 0
    expenditure_2024_25: Optional[int] = 0

    budget_estimate: Optional[int] = 0
    revised_estimate: Optional[int] = 0
    budget_estimate_2026_27: Optional[int] = 0

    remarks: Optional[str] = None

    @field_validator(
        "expenditure_2022_23",
        "expenditure_2023_24",
        "expenditure_2024_25",
        "budget_estimate",
        "revised_estimate",
        "budget_estimate_2026_27",
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


class SubHeadExpenditureUpdate(SubHeadExpenditureBase):
    pass


class SubHeadExpenditureResponse(SubHeadExpenditureBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

