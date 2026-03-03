"""DTOs for unit expenditure requests and responses"""
from pydantic import BaseModel
from typing import Optional


class UnitExpenditureRecordDataDTO(BaseModel):
    """DTO for record data response"""
    found: bool
    id: Optional[int] = None
    expenditure_prev4: int = 0
    expenditure_prev3: int = 0
    expenditure_prev2: int = 0
    budget_prev1: int = 0
    forecast_prev1: int = 0
    budget_curr_estimating_officer: int = 0
    budget_curr_controlling_officer: int = 0
    budget_curr_admin_dept: int = 0
    budget_curr_finance_dept: int = 0


class UnitExpenditureInlineUpdateDTO(BaseModel):
    """DTO for inline update request"""
    id: int
    expenditure_prev4: int = 0
    expenditure_prev3: int = 0
    expenditure_prev2: int = 0
    budget_prev1: int = 0
    forecast_prev1: int = 0
    budget_curr_estimating_officer: int = 0
    budget_curr_controlling_officer: int = 0
    budget_curr_admin_dept: int = 0
    budget_curr_finance_dept: int = 0


class UnitExpenditureFormUpdateDTO(BaseModel):
    """DTO for form update request"""
    id: int
    unit_account: str
    district: str
    expenditure_prev4: Optional[int] = None
    expenditure_prev3: Optional[int] = None
    expenditure_prev2: Optional[int] = None
    budget_prev1: Optional[int] = None
    forecast_prev1: Optional[int] = None
    budget_curr_estimating_officer: Optional[int] = None
    budget_curr_controlling_officer: Optional[int] = None
    budget_curr_admin_dept: Optional[int] = None
    budget_curr_finance_dept: Optional[int] = None

