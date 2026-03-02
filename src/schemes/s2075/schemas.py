"""Pydantic schemas for scheme 2075 - Miscellaneous General Services.

Provides validation for all API request/response models.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_VALUE = 999_999_999_999
SCHEME_CODE = "2075"


# ============================================================================
# BASE VALIDATORS
# ============================================================================

def _validate_expenditure_field(v: Optional[int]) -> Optional[int]:
    """Shared validator for expenditure fields."""
    if v is None:
        return v
    if v < 0:
        raise ValueError("Value must be non-negative")
    if v > MAX_VALUE:
        raise ValueError("Value too large")
    return v


# ============================================================================
# SUB-HEAD EXPENDITURE SCHEMAS
# ============================================================================

class SubHeadExpenditureBase(BaseModel):
    """Base schema for sub-head expenditure."""
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = Field(default=SCHEME_CODE, min_length=1, max_length=10)
    sub_scheme_code: Optional[str] = Field(default="20750249", min_length=1, max_length=15)
    sub_head: Optional[str] = None
    
    expenditure_prev3: Optional[int] = 0
    expenditure_prev2: Optional[int] = 0
    expenditure_prev1: Optional[int] = 0
    budget_estimate_curr: Optional[int] = 0
    revised_estimate_curr: Optional[int] = 0
    budget_estimate_next: Optional[int] = 0
    
    remarks: Optional[str] = None

    @field_validator("expenditure_prev3", "expenditure_prev2", "expenditure_prev1",
                     "budget_estimate_curr", "revised_estimate_curr", "budget_estimate_next")
    @classmethod
    def non_negative_int(cls, v: Optional[int]) -> Optional[int]:
        return _validate_expenditure_field(v)


class SubHeadExpenditureCreate(SubHeadExpenditureBase):
    """Schema for creating sub-head expenditure."""
    pass


class SubHeadExpenditureUpdate(SubHeadExpenditureBase):
    """Schema for updating sub-head expenditure."""
    pass


class SubHeadExpenditureResponse(SubHeadExpenditureBase):
    """Schema for sub-head expenditure response."""
    id: int
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DISTRICT EXPENDITURE SCHEMAS
# ============================================================================

class DistrictExpenditureBase(BaseModel):
    """Base schema for district expenditure."""
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = Field(default=SCHEME_CODE, min_length=1, max_length=10)
    sub_scheme_code: Optional[str] = Field(default="20750294", min_length=1, max_length=15)
    district: Optional[str] = None
    
    expenditure_prev3: Optional[int] = 0
    expenditure_prev2: Optional[int] = 0
    expenditure_prev1: Optional[int] = 0
    budget_estimate_curr: Optional[int] = 0
    revised_estimate_curr: Optional[int] = 0
    budget_estimate_next: Optional[int] = 0
    
    remarks: Optional[str] = None

    @field_validator("expenditure_prev3", "expenditure_prev2", "expenditure_prev1",
                     "budget_estimate_curr", "revised_estimate_curr", "budget_estimate_next")
    @classmethod
    def non_negative_int(cls, v: Optional[int]) -> Optional[int]:
        return _validate_expenditure_field(v)


class DistrictExpenditureCreate(DistrictExpenditureBase):
    """Schema for creating district expenditure."""
    pass


class DistrictExpenditureUpdate(DistrictExpenditureBase):
    """Schema for updating district expenditure."""
    pass


class DistrictExpenditureResponse(DistrictExpenditureBase):
    """Schema for district expenditure response."""
    id: int
    model_config = ConfigDict(from_attributes=True)
