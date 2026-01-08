"""Base schema classes for scheme-specific schemas"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

class SchemeBaseSchema(BaseModel):
    """Base schema with common scheme fields"""
    fiscal_year: Optional[str] = None
    scheme_code: Optional[str] = None
    sub_scheme_code: Optional[str] = None
    district: Optional[str] = None

class BudgetDetailsBaseSchema(SchemeBaseSchema):
    """Base schema for budget details type data"""
    category: Optional[str] = None
    class_type: Optional[str] = None

class PostStatusBaseSchema(BudgetDetailsBaseSchema):
    """Base schema for post status type data"""
    status: Optional[str] = None

class UnitExpenditureBaseSchema(SchemeBaseSchema):
    """Base schema for unit expenditure type data"""
    unit_account: Optional[str] = None

class SchemeResponseMixin:
    """Mixin for response schemas"""
    id: int
    model_config = ConfigDict(from_attributes=True)

