from database import Base
from sqlalchemy import Column, Integer, String, Float, UniqueConstraint # Added UniqueConstraint

class BudgetPostDetails(Base):
    __tablename__ = 'budget_post_details'
    id = Column(Integer, primary_key=True, index=True)
    District = Column(String)
    Category = Column(String)
    Class = Column(String)
    Designation = Column(String)
    SanctionedPosts202425 = Column(Integer)
    SanctionedPosts202526 = Column(Integer)
    SpecialPay = Column(Integer)
    BasicPay = Column(Integer)
    GradePay = Column(Integer)
    DearnessAllowance64 = Column(Integer)
    LocalSupplemetoryAllowance = Column(Integer)
    LocalHRA = Column(Integer)
    VehicleAllowance = Column(Integer)
    WashingAllowance = Column(Integer)
    CashAllowance = Column(Integer)
    FootWareAllowanceOther = Column(Integer)

class PostStatus(Base):
    __tablename__ = 'post_status'
    id = Column(Integer, primary_key=True, index=True)
    District = Column(String)
    Category = Column(String)
    Class = Column(String)
    Status = Column(String)
    Posts = Column(Integer)
    Salary = Column(Integer)
    GradePay = Column(Integer)
    DearnessAllowance = Column(Integer)
    LocalSupplemetoryAllowance = Column(Integer)
    HouseRentAllowance = Column(Integer)
    TravelAllowance = Column(Integer)
    Other = Column(Integer)

class PostExpenses(Base):
    __tablename__ = 'post_expenses'
    id = Column(Integer, primary_key=True, index=True)
    Class = Column(String)
    Category = Column(String)
    FilledPosts = Column(Integer)
    VacantPosts = Column(Integer)
    District = Column(String)
    MedicalExpenses = Column(Integer)
    FestivalAdvance = Column(Integer)
    SwagramMaharashtraDarshan = Column(Integer)
    SeventhPayCommissionDifferenceNPS = Column(Float)
    NPS = Column(Float)
    SeventhPayCommissionDifference = Column(Float)
    Other = Column(Integer)

class UnitExpenditure(Base):
    __tablename__ = 'unit_expenditure'
    id = Column(Integer, primary_key=True, index=True)
    PrimaryAndSecondaryUnitsOfAccount = Column(String)
    District = Column(String)
    ActualAmountExpenditure20212022 = Column(Integer)
    ActualAmountExpenditure20222023 = Column(Integer)
    ActualAmountExpenditure20232024 = Column(Integer)
    BudgetaryEstimates20242025 = Column(Integer)
    ImprovedForecast20242025 = Column(Integer)
    BudgetaryEstimates20252026EstimatingOfficer = Column(Integer)
    BudgetaryEstimates20252026ControllingOfficer = Column(Integer)
    BudgetaryEstimates20252026AdministrativeDepartment = Column(Integer)
    BudgetaryEstimates20252026FinanceDepartment = Column(Integer)

# --- NEW MODEL for Editable Approved Post Targets ---
class ApprovedPostTarget(Base):
    __tablename__ = 'approved_post_targets'

    id = Column(Integer, primary_key=True, index=True)
    class_key = Column(String, index=True) # e.g., '1', '2', '3', '4'
    category = Column(String, index=True) # 'Permanent' or 'Temporary'
    approved_count = Column(Integer, default=0)

    # Ensure only one entry per class/category combination
    __table_args__ = (UniqueConstraint('class_key', 'category', name='_class_category_uc'),)