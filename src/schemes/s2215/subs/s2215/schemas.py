"""Pydantic schemas for sub-scheme 2215."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import SCHEME_CODE, SUB_SCHEME_CODE
from .config import get_account_head, get_districts_for_account_head


class DistrictExpenditureBase(BaseModel):
    """Base schema for district expenditure with fiscal year columns."""
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = Field(default=SCHEME_CODE, min_length=1, max_length=10)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE, min_length=1, max_length=15)
    account_head_code: Optional[str] = None
    district: Optional[str] = None

    # Actual expenditure (historical)
    expenditure_2022_23: Optional[int] = 0
    expenditure_2023_24: Optional[int] = 0
    expenditure_2024_25: Optional[int] = 0

    # Budget estimates and demands
    budget_estimate_2025_26: Optional[int] = 0
    revised_demand_2025_26: Optional[int] = 0
    budget_estimate_2026_27: Optional[int] = 0

    remarks: Optional[str] = None

    @field_validator(
        "expenditure_2022_23",
        "expenditure_2023_24",
        "expenditure_2024_25",
        "budget_estimate_2025_26",
        "revised_demand_2025_26",
        "budget_estimate_2026_27",
    )
    @classmethod
    def non_negative_int(cls, v: Optional[int]) -> Optional[int]:
        """Validate that financial values are non-negative and within reasonable limits."""
        if v is None:
            return v
        if v < 0:
            raise ValueError("Value must be non-negative")
        if v > 999_999_999_999:
            raise ValueError("Value too large")
        return v


class DistrictExpenditureCreate(DistrictExpenditureBase):
    """Schema for creating a new district expenditure record."""
    account_head_code: str
    district: str

    @field_validator("account_head_code")
    @classmethod
    def validate_account_head(cls, v: str) -> str:
        """Validate that account head code exists in configuration."""
        head = get_account_head(v)
        if not head:
            raise ValueError("Invalid account head code")
        return v

    @field_validator("district")
    @classmethod
    def validate_district(cls, v: str) -> str:
        """Validate that district is required."""
        if not v:
            raise ValueError("District is required")
        return v


class DistrictExpenditureUpdate(DistrictExpenditureBase):
    """Schema for updating an existing district expenditure record."""
    pass


class DistrictExpenditureResponse(DistrictExpenditureBase):
    """Schema for district expenditure response."""
    id: int
    model_config = ConfigDict(from_attributes=True)

