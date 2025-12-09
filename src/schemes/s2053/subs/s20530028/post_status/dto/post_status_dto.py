"""Data Transfer Objects for Post Status"""
from typing import Optional
from pydantic import BaseModel, Field


class PostStatusUpdateDTO(BaseModel):
    """DTO for updating post status record"""
    posts: Optional[int] = Field(None, ge=0)
    salary: Optional[int] = Field(None, ge=0)
    grade_pay: Optional[int] = Field(None, ge=0)
    special_pay: Optional[int] = Field(None, ge=0)
    dearness_allowance: Optional[int] = Field(None, ge=0)
    local_supplementary_allowance: Optional[int] = Field(None, ge=0)
    house_rent_allowance: Optional[int] = Field(None, ge=0)
    travel_allowance: Optional[int] = Field(None, ge=0)
    other: Optional[int] = Field(None, ge=0)


class PostStatusRecordDTO(BaseModel):
    """DTO for post status record data"""
    found: bool
    id: Optional[int] = None
    posts: Optional[int] = 0
    salary: Optional[int] = 0
    grade_pay: Optional[int] = 0
    special_pay: Optional[int] = 0
    dearness_allowance: Optional[int] = 0
    local_supplementary_allowance: Optional[int] = 0
    house_rent_allowance: Optional[int] = 0
    travel_allowance: Optional[int] = 0
    other: Optional[int] = 0

