"""Pydantic schemas for sub-scheme 20290182"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from src.core.base_schemas import BudgetDetailsBaseSchema, PostStatusBaseSchema, UnitExpenditureBaseSchema
from .config import SCHEME_CODE, SUB_SCHEME_CODE


class BudgetPostDetailsBase(BudgetDetailsBaseSchema):
    scheme_code: Optional[str] = Field(default=SCHEME_CODE)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE)
    designation: Optional[str] = None
    sanctioned_posts_prev1: Optional[int] = Field(None, ge=0)
    sanctioned_posts_curr: Optional[int] = Field(None, ge=0)
    special_pay: Optional[int] = Field(None, ge=0)
    basic_pay: Optional[float] = Field(None, ge=0)
    grade_pay: Optional[int] = Field(None, ge=0)
    local_supplementary_allowance: Optional[int] = Field(None, ge=0)
    vehicle_allowance: Optional[int] = Field(None, ge=0)
    washing_allowance: Optional[int] = Field(None, ge=0)
    cash_allowance: Optional[int] = Field(None, ge=0)
    footwear_allowance_other: Optional[int] = Field(None, ge=0)
    hra_rate: Optional[str] = Field('X', pattern='^[XYZ]$')


class BudgetPostDetailsCreate(BudgetPostDetailsBase):
    district: str
    category: str
    class_type: str
    designation: str


class BudgetPostDetailsUpdate(BudgetPostDetailsBase):
    pass


class BudgetPostDetailsResponse(BudgetPostDetailsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PostStatusBase(PostStatusBaseSchema):
    scheme_code: Optional[str] = Field(default=SCHEME_CODE)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE)
    posts: Optional[int] = Field(None, ge=0)
    salary: Optional[int] = Field(None, ge=0)
    grade_pay: Optional[int] = Field(None, ge=0)
    special_pay: Optional[int] = Field(None, ge=0)
    dearness_allowance: Optional[int] = Field(None, ge=0)
    local_supplementary_allowance: Optional[int] = Field(None, ge=0)
    house_rent_allowance: Optional[int] = Field(None, ge=0)
    travel_allowance: Optional[int] = Field(None, ge=0)
    other: Optional[int] = Field(None, ge=0)


class PostStatusCreate(PostStatusBase):
    district: str
    category: str
    class_type: str
    status: str


class PostStatusUpdate(PostStatusBase):
    pass


class PostStatusResponse(PostStatusBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PostExpensesBase(BudgetDetailsBaseSchema):
    scheme_code: Optional[str] = Field(default=SCHEME_CODE)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE)
    filled_posts: Optional[int] = Field(None, ge=0)
    vacant_posts: Optional[int] = Field(None, ge=0)
    medical_expenses: Optional[int] = Field(None, ge=0)
    festival_advance: Optional[int] = Field(None, ge=0)
    swagram_maharashtra_darshan: Optional[int] = Field(None, ge=0)
    seventh_pay_commission_difference_nps: Optional[float] = None
    nps: Optional[float] = None
    seventh_pay_commission_difference: Optional[float] = None
    other: Optional[int] = Field(None, ge=0)


class PostExpensesCreate(PostExpensesBase):
    class_type: str
    category: str
    district: str


class PostExpensesUpdate(PostExpensesBase):
    pass


class PostExpensesResponse(PostExpensesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class UnitExpenditureBase(UnitExpenditureBaseSchema):
    scheme_code: Optional[str] = Field(default=SCHEME_CODE)
    sub_scheme_code: Optional[str] = Field(default=SUB_SCHEME_CODE)
    expenditure_prev4: Optional[int] = Field(None, ge=0)
    expenditure_prev3: Optional[int] = Field(None, ge=0)
    expenditure_prev2: Optional[int] = Field(None, ge=0)
    budget_prev1: Optional[int] = Field(None, ge=0)
    forecast_prev1: Optional[int] = Field(None, ge=0)
    budget_curr_estimating_officer: Optional[int] = Field(None, ge=0)
    budget_curr_controlling_officer: Optional[int] = Field(None, ge=0)
    budget_curr_admin_dept: Optional[int] = Field(None, ge=0)
    budget_curr_finance_dept: Optional[int] = Field(None, ge=0)


class UnitExpenditureCreate(UnitExpenditureBase):
    unit_account: str
    district: str


class UnitExpenditureUpdate(UnitExpenditureBase):
    pass


class UnitExpenditureResponse(UnitExpenditureBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

