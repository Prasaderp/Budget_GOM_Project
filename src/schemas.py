"""Shared Pydantic schemas for Budget Management System

This file contains ONLY shared schemas used across all schemes.
Scheme-specific schemas are in: src/schemes/s{code}/subs/s{subcode}/schemas.py
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


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


# Backward compatibility - import from scheme-specific schemas
from src.schemes.s2053.subs.s20530028.schemas import (
    BudgetPostDetailsBase, BudgetPostDetailsCreate, BudgetPostDetailsUpdate, BudgetPostDetailsResponse,
    PostStatusBase, PostStatusCreate, PostStatusUpdate, PostStatusResponse,
    PostExpensesBase, PostExpensesCreate, PostExpensesUpdate, PostExpensesResponse,
    UnitExpenditureBase, UnitExpenditureCreate, UnitExpenditureUpdate, UnitExpenditureResponse
)
