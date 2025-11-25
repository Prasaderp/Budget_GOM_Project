from src.database import Base
from sqlalchemy import Column, Integer, String, Float, UniqueConstraint, Boolean
from sqlalchemy import Text
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from sqlalchemy import DateTime
from datetime import datetime

class BudgetPostDetails(Base):
    __tablename__ = 'budget_post_details'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(String, index=True, nullable=False, default='2025-26', server_default='2025-26')
    district = Column(String, index=True)
    category = Column(String, index=True)
    class_type = Column(String, index=True)
    designation = Column(String, index=True)
    sanctioned_posts_2024_25 = Column(Integer)
    sanctioned_posts_2025_26 = Column(Integer)
    special_pay = Column(Integer)
    basic_pay = Column(Integer)
    grade_pay = Column(Integer)
    local_supplementary_allowance = Column(Integer)
    vehicle_allowance = Column(Integer)
    washing_allowance = Column(Integer)
    cash_allowance = Column(Integer)
    footwear_allowance_other = Column(Integer)

class PostStatus(Base):
    __tablename__ = 'post_status'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(String, index=True, nullable=False, default='2025-26', server_default='2025-26')
    district = Column(String, index=True)
    category = Column(String, index=True)
    class_type = Column(String, index=True)
    status = Column(String, index=True)
    posts = Column(Integer)
    salary = Column(Integer)
    grade_pay = Column(Integer)
    special_pay = Column(Integer)
    dearness_allowance = Column(Integer)
    local_supplementary_allowance = Column(Integer)
    house_rent_allowance = Column(Integer)
    travel_allowance = Column(Integer)
    other = Column(Integer)

class PostExpenses(Base):
    __tablename__ = 'post_expenses'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(String, index=True, nullable=False, default='2025-26', server_default='2025-26')
    class_type = Column(String, index=True)
    category = Column(String, index=True)
    filled_posts = Column(Integer)
    vacant_posts = Column(Integer)
    district = Column(String, index=True)
    medical_expenses = Column(Integer)
    festival_advance = Column(Integer)
    swagram_maharashtra_darshan = Column(Integer)
    seventh_pay_commission_difference_nps = Column(Float)
    nps = Column(Float)
    seventh_pay_commission_difference = Column(Float)
    other = Column(Integer)

class UnitExpenditure(Base):
    __tablename__ = 'unit_expenditure'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(String, index=True, nullable=False, default='2025-26', server_default='2025-26')
    unit_account = Column(String, index=True)
    district = Column(String, index=True)
    expenditure_2021_22 = Column(Integer)
    expenditure_2022_23 = Column(Integer)
    expenditure_2023_24 = Column(Integer)
    budget_2024_25 = Column(Integer)
    forecast_2024_25 = Column(Integer)
    budget_2025_26_estimating_officer = Column(Integer)
    budget_2025_26_controlling_officer = Column(Integer)
    budget_2025_26_admin_dept = Column(Integer)
    budget_2025_26_finance_dept = Column(Integer)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    level = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    activated_by = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    phone_number = Column(String, nullable=True)
    notification_preferences = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    @validates('level')
    def validate_level(self, key, value):
        allowed = {'dco', 'district', 'taluka'}
        if value not in allowed:
            raise ValueError('Invalid level')
        return value

    @validates('role')
    def validate_role(self, key, value):
        allowed = {'assistant', 'officer2', 'officer1', 'dco'}
        if value not in allowed:
            raise ValueError('Invalid role')
        return value

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    thread_key = Column(String, index=True)
    from_username = Column(String, index=True)
    to_username = Column(String, index=True)
    role_from = Column(String, index=True)
    role_to = Column(String, index=True)
    text = Column(String)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())


class AdminUser(Base):
    __tablename__ = 'admin_users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

class DistrictTalukaSelection(Base):
    __tablename__ = 'district_taluka_selection'
    id = Column(Integer, primary_key=True, index=True)
    district = Column(String, unique=True, index=True, nullable=False)
    selected_talukas = Column(JSON, nullable=False)


class TalukaUserManagement(Base):
    __tablename__ = 'taluka_user_management'
    id = Column(Integer, primary_key=True, index=True)
    district = Column(String, index=True, nullable=False)
    taluka_name = Column(String, index=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    activated_by_district_assistant = Column(String, nullable=True)
    officer1_user_id = Column(Integer, nullable=True)
    officer2_user_id = Column(Integer, nullable=True)
    assistant_user_id = Column(Integer, nullable=True)
    last_modified = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('district', 'taluka_name', name='uq_district_taluka_mgmt'),
    )


class AssistantChat(Base):
    __tablename__ = 'assistant_chats'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False)
    unit = Column(String, index=True, nullable=True)
    role = Column(String, index=True, nullable=False)
    message_role = Column(String, index=True, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, index=True, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('id', name='uq_assistant_chats_id'),
    )


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, index=True, nullable=False)
    record_id = Column(Integer, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)  # 'INSERT', 'UPDATE', 'DELETE'
    username = Column(String, index=True, nullable=False)
    user_level = Column(String, index=True, nullable=False)
    user_role = Column(String, index=True, nullable=False)
    user_unit = Column(String, index=True, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changed_fields = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, index=True, nullable=False, default=datetime.utcnow)
    session_id = Column(String, index=True, nullable=True)
    
    @validates('action')
    def validate_action(self, key, value):
        allowed = {'INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'VIEW', 'EXPORT'}
        if value not in allowed:
            raise ValueError('Invalid audit action')
        return value


class FiscalYear(Base):
    __tablename__ = 'fiscal_years'
    id = Column(Integer, primary_key=True, index=True)
    year_range = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    @validates('year_range')
    def validate_year_range(self, key, value):
        if not value or '-' not in value:
            raise ValueError('Year range must be in format YYYY-YY')
        return value

class DataFillingPeriod(Base):
    __tablename__ = 'data_filling_periods'
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, index=True, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    @validates('level')
    def validate_level(self, key, value):
        allowed = {'district', 'taluka', 'both'}
        if value not in allowed:
            raise ValueError('Invalid level for data filling period')
        return value