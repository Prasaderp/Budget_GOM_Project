"""DTOs for unit expenditure requests and responses"""
from pydantic import BaseModel
from typing import Optional


class UnitExpenditureRecordDataDTO(BaseModel):
    """DTO for record data response"""
    found: bool
    id: Optional[int] = None
    expenditure_2021_22: int = 0
    expenditure_2022_23: int = 0
    expenditure_2023_24: int = 0
    budget_2024_25: int = 0
    forecast_2024_25: int = 0
    budget_2025_26_estimating_officer: int = 0
    budget_2025_26_controlling_officer: int = 0
    budget_2025_26_admin_dept: int = 0
    budget_2025_26_finance_dept: int = 0


class UnitExpenditureInlineUpdateDTO(BaseModel):
    """DTO for inline update request"""
    id: int
    expenditure_2021_22: int = 0
    expenditure_2022_23: int = 0
    expenditure_2023_24: int = 0
    budget_2024_25: int = 0
    forecast_2024_25: int = 0
    budget_2025_26_estimating_officer: int = 0
    budget_2025_26_controlling_officer: int = 0
    budget_2025_26_admin_dept: int = 0
    budget_2025_26_finance_dept: int = 0


class UnitExpenditureFormUpdateDTO(BaseModel):
    """DTO for form update request"""
    id: int
    unit_account: str
    district: str
    expenditure_2021_22: Optional[int] = None
    expenditure_2022_23: Optional[int] = None
    expenditure_2023_24: Optional[int] = None
    budget_2024_25: Optional[int] = None
    forecast_2024_25: Optional[int] = None
    budget_2025_26_estimating_officer: Optional[int] = None
    budget_2025_26_controlling_officer: Optional[int] = None
    budget_2025_26_admin_dept: Optional[int] = None
    budget_2025_26_finance_dept: Optional[int] = None

