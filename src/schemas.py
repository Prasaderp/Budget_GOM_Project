from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class BudgetPostDetailsBase(BaseModel):
    scheme_code: Optional[str] = '2053'
    sub_scheme_code: Optional[str] = '20530028'
    district: Optional[str] = None
    category: Optional[str] = None
    class_type: Optional[str] = None
    designation: Optional[str] = None
    sanctioned_posts_2024_25: Optional[int] = None
    sanctioned_posts_2025_26: Optional[int] = None
    special_pay: Optional[int] = None
    basic_pay: Optional[float] = None
    grade_pay: Optional[int] = None
    local_supplementary_allowance: Optional[int] = None
    vehicle_allowance: Optional[int] = None
    washing_allowance: Optional[int] = None
    cash_allowance: Optional[int] = None
    footwear_allowance_other: Optional[int] = None 

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
    scheme_code: Optional[str] = '2053'
    sub_scheme_code: Optional[str] = '20530028'
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
    scheme_code: Optional[str] = '2053'
    sub_scheme_code: Optional[str] = '20530028'
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
    scheme_code: Optional[str] = '2053'
    sub_scheme_code: Optional[str] = '20530028'
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

class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    level: str
    unit: Optional[str] = None
    role: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    message: str
    user: Optional[UserResponse] = None

class MessageCreate(BaseModel):
    thread_key: str
    to_username: str
    text: str

class MessageResponse(BaseModel):
    id: int
    thread_key: str
    from_username: str
    to_username: str
    role_from: str
    role_to: str
    text: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminUserResponse(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)

class UserUpdateRequest(BaseModel):
    id: int
    username: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    level: Optional[str] = None
    unit: Optional[str] = None
    role: Optional[str] = None

class DistrictTalukaSelectionBase(BaseModel):
    district: str
    selected_talukas: List[str]

class DistrictTalukaSelectionCreate(DistrictTalukaSelectionBase):
    pass

class DistrictTalukaSelectionUpdate(BaseModel):
    selected_talukas: List[str]

class DistrictTalukaSelectionResponse(DistrictTalukaSelectionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AssistantChatItem(BaseModel):
    message_role: str
    content: str
    created_at: datetime

class AssistantChatHistoryResponse(BaseModel):
    items: List[AssistantChatItem]

class UserSettingsResponse(BaseModel):
    email: str
    phone_number: str
    notification_preferences: dict

class UserSettingsUpdate(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    data_filling_period: Optional[bool] = None
    taluka_activation: Optional[bool] = None
    fiscal_year_changes: Optional[bool] = None