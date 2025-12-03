"""Pydantic schemas for sub-scheme 20530028"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

SCHEME_CODE = "2053"
SUB_SCHEME_CODE = "20530028"

class BudgetPostDetailsBase(BaseModel):
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = SCHEME_CODE
    sub_scheme_code: Optional[str] = SUB_SCHEME_CODE
    district: Optional[str] = None
    category: Optional[str] = None
    class_type: Optional[str] = None
    designation: Optional[str] = None
    sanctioned_posts_2024_25: Optional[int] = None
    sanctioned_posts_2025_26: Optional[int] = None
    special_pay: Optional[int] = None
    basic_pay: Optional[float] = None
    grade_pay: Optional[int] = None
    dearness_allowance_64: Optional[int] = None
    local_supplementary_allowance: Optional[int] = None
    house_rent_allowance: Optional[int] = None
    vehicle_allowance: Optional[int] = None
    washing_allowance: Optional[int] = None
    cash_allowance: Optional[int] = None
    footwear_allowance_other: Optional[int] = None
    hra_rate: Optional[str] = 'X'

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

class PostStatusBase(BaseModel):
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = SCHEME_CODE
    sub_scheme_code: Optional[str] = SUB_SCHEME_CODE
    district: Optional[str] = None
    category: Optional[str] = None
    class_type: Optional[str] = None
    status: Optional[str] = None
    posts: Optional[int] = None
    salary: Optional[int] = None
    grade_pay: Optional[int] = None
    special_pay: Optional[int] = None
    dearness_allowance: Optional[int] = None
    local_supplementary_allowance: Optional[int] = None
    house_rent_allowance: Optional[int] = None
    travel_allowance: Optional[int] = None
    other: Optional[int] = None

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

class PostExpensesBase(BaseModel):
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = SCHEME_CODE
    sub_scheme_code: Optional[str] = SUB_SCHEME_CODE
    class_type: Optional[str] = None
    category: Optional[str] = None
    filled_posts: Optional[int] = None
    vacant_posts: Optional[int] = None
    district: Optional[str] = None
    medical_expenses: Optional[int] = None
    festival_advance: Optional[int] = None
    swagram_maharashtra_darshan: Optional[int] = None
    seventh_pay_commission_difference_nps: Optional[float] = None
    nps: Optional[float] = None
    seventh_pay_commission_difference: Optional[float] = None
    other: Optional[int] = None

class PostExpensesCreate(PostExpensesBase):
    class_type: str
    category: str
    district: str

class PostExpensesUpdate(PostExpensesBase):
    pass

class PostExpensesResponse(PostExpensesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UnitExpenditureBase(BaseModel):
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = SCHEME_CODE
    sub_scheme_code: Optional[str] = SUB_SCHEME_CODE
    unit_account: Optional[str] = None
    district: Optional[str] = None
    expenditure_2021_22: Optional[int] = None
    expenditure_2022_23: Optional[int] = None
    expenditure_2023_24: Optional[int] = None
    budget_2024_25: Optional[int] = None
    forecast_2024_25: Optional[int] = None
    budget_2025_26_estimating_officer: Optional[int] = None
    budget_2025_26_controlling_officer: Optional[int] = None
    budget_2025_26_admin_dept: Optional[int] = None
    budget_2025_26_finance_dept: Optional[int] = None

class UnitExpenditureCreate(UnitExpenditureBase):
    unit_account: str
    district: str

class UnitExpenditureUpdate(UnitExpenditureBase):
    pass

class UnitExpenditureResponse(UnitExpenditureBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

