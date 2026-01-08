"""Pydantic schemas for post level details"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class PostLevelBase(BaseModel):
    """Base schema for post level"""
    level_name: str = Field(..., min_length=1, max_length=100)
    level_order: int = Field(default=1, ge=1)
    pay_stage: Optional[str] = None
    pay_level: Optional[int] = None
    special_pay: int = Field(default=0, ge=0)
    basic_pay: float = Field(default=0, ge=0)
    grade_pay: int = Field(default=0, ge=0)
    local_supplementary_allowance: int = Field(default=0, ge=0)
    vehicle_allowance: int = Field(default=0, ge=0)
    washing_allowance: int = Field(default=0, ge=0)
    cash_allowance: int = Field(default=0, ge=0)
    footwear_allowance_other: int = Field(default=0, ge=0)
    hra_rate: str = Field(default='X', pattern='^[XYZ]$')


class PostLevelCreate(PostLevelBase):
    """Schema for creating a new level"""
    budget_post_id: int
    sub_scheme_code: str
    table_name: str
    fiscal_year: str = '2025-26'


class PostLevelUpdate(BaseModel):
    """Schema for updating an existing level"""
    level_name: Optional[str] = Field(None, min_length=1, max_length=100)
    level_order: Optional[int] = Field(None, ge=1)
    pay_stage: Optional[str] = None
    pay_level: Optional[int] = None
    special_pay: Optional[int] = Field(None, ge=0)
    basic_pay: Optional[float] = Field(None, ge=0)
    grade_pay: Optional[int] = Field(None, ge=0)
    local_supplementary_allowance: Optional[int] = Field(None, ge=0)
    vehicle_allowance: Optional[int] = Field(None, ge=0)
    washing_allowance: Optional[int] = Field(None, ge=0)
    cash_allowance: Optional[int] = Field(None, ge=0)
    footwear_allowance_other: Optional[int] = Field(None, ge=0)
    hra_rate: Optional[str] = Field(None, pattern='^[XYZ]$')


class PostLevelResponse(PostLevelBase):
    """Schema for API response"""
    id: int
    budget_post_id: int
    sub_scheme_code: str
    table_name: str
    fiscal_year: str
    created_at: datetime
    updated_at: datetime
    
    # Calculated fields (not stored, computed on read)
    dearness_allowance: Optional[int] = None
    hra_amount: Optional[int] = None
    total: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class PostLevelCalculateRequest(BaseModel):
    """Request schema for salary calculation endpoint"""
    basic_pay: float
    grade_pay: int
    hra_rate: str = Field(..., pattern='^[XYZ]$')


class PostLevelCalculateResponse(BaseModel):
    """Response schema for salary calculation"""
    dearness_allowance: int
    hra_amount: int
    base_for_allowances: int


class AggregatedTotals(BaseModel):
    """Schema for aggregated totals from all levels"""
    count: int
    special_pay: int
    basic_pay: float
    grade_pay: int
    local_supplementary_allowance: int
    vehicle_allowance: int
    washing_allowance: int
    cash_allowance: int
    footwear_allowance_other: int
    dearness_allowance: int
    hra_total: int
    grand_total: int

