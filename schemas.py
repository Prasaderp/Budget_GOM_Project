from pydantic import BaseModel
from typing import Optional, List

# Corrected to match user's models.py
class BudgetPostDetailsBase(BaseModel):
    District: Optional[str] = None
    Category: Optional[str] = None
    Class: Optional[str] = None
    Designation: Optional[str] = None
    SanctionedPosts202425: Optional[int] = None
    SanctionedPosts202526: Optional[int] = None
    SpecialPay: Optional[int] = None
    BasicPay: Optional[int] = None
    GradePay: Optional[int] = None
    DearnessAllowance64: Optional[int] = None
    LocalSupplemetoryAllowance: Optional[int] = None
    LocalHRA: Optional[int] = None
    VehicleAllowance: Optional[int] = None
    WashingAllowance: Optional[int] = None
    CashAllowance: Optional[int] = None
    FootWareAllowanceOther: Optional[int] = None # Note spelling 'Ware'

class BudgetPostDetailsCreate(BudgetPostDetailsBase):
    District: str
    Category: str
    Class: str
    Designation: str

class BudgetPostDetailsUpdate(BudgetPostDetailsBase):
     pass

class BudgetPostDetailsResponse(BudgetPostDetailsBase):
    id: int
    class Config: from_attributes = True

# --- Other Schemas ---
class PostStatusBase(BaseModel):
    District: Optional[str] = None
    Category: Optional[str] = None
    Class: Optional[str] = None
    Status: Optional[str] = None
    Posts: Optional[int] = None
    Salary: Optional[int] = None
    GradePay: Optional[int] = None
    DearnessAllowance: Optional[int] = None
    LocalSupplemetoryAllowance: Optional[int] = None
    HouseRentAllowance: Optional[int] = None
    TravelAllowance: Optional[int] = None
    Other: Optional[int] = None

class PostStatusCreate(PostStatusBase):
    District: str
    Category: str
    Class: str
    Status: str

class PostStatusUpdate(PostStatusBase):
    pass

class PostStatusResponse(PostStatusBase):
    id: int
    class Config: from_attributes = True

class PostExpensesBase(BaseModel):
    Class: Optional[str] = None
    Category: Optional[str] = None
    FilledPosts: Optional[int] = None
    VacantPosts: Optional[int] = None
    District: Optional[str] = None
    MedicalExpenses: Optional[int] = None
    FestivalAdvance: Optional[int] = None
    SwagramMaharashtraDarshan: Optional[int] = None
    SeventhPayCommissionDifferenceNPS: Optional[float] = None
    NPS: Optional[float] = None
    SeventhPayCommissionDifference: Optional[float] = None
    Other: Optional[int] = None

class PostExpensesCreate(PostExpensesBase):
    Class: str
    Category: str
    District: str

class PostExpensesUpdate(PostExpensesBase):
    pass

class PostExpensesResponse(PostExpensesBase):
    id: int
    class Config: from_attributes = True

class UnitExpenditureBase(BaseModel):
    PrimaryAndSecondaryUnitsOfAccount: Optional[str] = None
    District: Optional[str] = None
    ActualAmountExpenditure20212022: Optional[int] = None
    ActualAmountExpenditure20222023: Optional[int] = None
    ActualAmountExpenditure20232024: Optional[int] = None
    BudgetaryEstimates20242025: Optional[int] = None
    ImprovedForecast20242025: Optional[int] = None
    BudgetaryEstimates20252026EstimatingOfficer: Optional[int] = None
    BudgetaryEstimates20252026ControllingOfficer: Optional[int] = None
    BudgetaryEstimates20252026AdministrativeDepartment: Optional[int] = None
    BudgetaryEstimates20252026FinanceDepartment: Optional[int] = None

class UnitExpenditureCreate(UnitExpenditureBase):
    PrimaryAndSecondaryUnitsOfAccount: str
    District: str

class UnitExpenditureUpdate(UnitExpenditureBase):
    pass

class UnitExpenditureResponse(UnitExpenditureBase):
    id: int
    class Config: from_attributes = True