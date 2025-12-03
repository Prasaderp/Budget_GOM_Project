from src.database import Base
from sqlalchemy import Column, Integer, String, Float, UniqueConstraint, Boolean, BigInteger, CheckConstraint, CHAR
from sqlalchemy.types import Numeric
from sqlalchemy import Text
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from sqlalchemy import DateTime
from datetime import datetime

class BudgetPostDetails(Base):
    __tablename__ = 'budget_post_details'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default='2053', server_default='2053', index=True)
    sub_scheme_code = Column(String(15), nullable=False, default='20530028', server_default='20530028', index=True)
    district = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    class_type = Column(String(50), nullable=False)
    designation = Column(String(200), nullable=False)
    sanctioned_posts_2024_25 = Column(Integer, nullable=False, default=0, server_default='0')
    sanctioned_posts_2025_26 = Column(Integer, nullable=False, default=0, server_default='0')
    special_pay = Column(BigInteger, nullable=False, default=0, server_default='0')
    basic_pay = Column(Numeric(10, 1), nullable=False, default=0, server_default='0')
    grade_pay = Column(BigInteger, nullable=False, default=0, server_default='0')
    local_supplementary_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    vehicle_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    washing_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    cash_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    footwear_allowance_other = Column(BigInteger, nullable=False, default=0, server_default='0')
    hra_rate = Column(CHAR(1), nullable=False, default='X', server_default='X')
    
    __table_args__ = (
        UniqueConstraint('fiscal_year', 'sub_scheme_code', 'district', 'category', 'class_type', 'designation', 
                        name='uq_budget_post_natural_key_v2'),
        CheckConstraint('sanctioned_posts_2024_25 >= 0', name='chk_posts_2024_25_non_negative'),
        CheckConstraint('sanctioned_posts_2025_26 >= 0', name='chk_posts_2025_26_non_negative'),
        CheckConstraint('basic_pay >= 0', name='chk_basic_pay_non_negative'),
        CheckConstraint("hra_rate IN ('X', 'Y', 'Z')", name='chk_hra_rate_valid'),
    )

class PostStatus(Base):
    __tablename__ = 'post_status'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default='2053', server_default='2053', index=True)
    sub_scheme_code = Column(String(15), nullable=False, default='20530028', server_default='20530028', index=True)
    district = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    class_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    posts = Column(Integer, nullable=False, default=0, server_default='0')
    salary = Column(BigInteger, nullable=False, default=0, server_default='0')
    grade_pay = Column(BigInteger, nullable=False, default=0, server_default='0')
    special_pay = Column(BigInteger, nullable=False, default=0, server_default='0')
    dearness_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    local_supplementary_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    house_rent_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    travel_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    other = Column(BigInteger, nullable=False, default=0, server_default='0')
    
    __table_args__ = (
        UniqueConstraint('fiscal_year', 'sub_scheme_code', 'district', 'category', 'class_type', 'status', 
                        name='uq_post_status_natural_key_v2'),
        CheckConstraint('posts >= 0', name='chk_posts_non_negative'),
        CheckConstraint('salary >= 0', name='chk_salary_non_negative'),
    )

class PostExpenses(Base):
    __tablename__ = 'post_expenses'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default='2053', server_default='2053', index=True)
    sub_scheme_code = Column(String(15), nullable=False, default='20530028', server_default='20530028', index=True)
    class_type = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    filled_posts = Column(Integer, nullable=False, default=0, server_default='0')
    vacant_posts = Column(Integer, nullable=False, default=0, server_default='0')
    district = Column(String(100), nullable=False)
    medical_expenses = Column(BigInteger, nullable=False, default=0, server_default='0')
    festival_advance = Column(BigInteger, nullable=False, default=0, server_default='0')
    swagram_maharashtra_darshan = Column(BigInteger, nullable=False, default=0, server_default='0')
    seventh_pay_commission_difference_nps = Column(Float)
    nps = Column(Float)
    seventh_pay_commission_difference = Column(Float)
    other = Column(BigInteger, nullable=False, default=0, server_default='0')
    
    __table_args__ = (
        UniqueConstraint('fiscal_year', 'sub_scheme_code', 'district', 'category', 'class_type', 
                        name='uq_post_expenses_natural_key_v2'),
        CheckConstraint('filled_posts >= 0', name='chk_filled_posts_non_negative'),
        CheckConstraint('vacant_posts >= 0', name='chk_vacant_posts_non_negative'),
    )

class UnitExpenditure(Base):
    __tablename__ = 'unit_expenditure'
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default='2053', server_default='2053', index=True)
    sub_scheme_code = Column(String(15), nullable=False, default='20530028', server_default='20530028', index=True)
    unit_account = Column(String(200), nullable=False)
    district = Column(String(100), nullable=False)
    expenditure_2021_22 = Column(BigInteger, nullable=False, default=0, server_default='0')
    expenditure_2022_23 = Column(BigInteger, nullable=False, default=0, server_default='0')
    expenditure_2023_24 = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_2024_25 = Column(BigInteger, nullable=False, default=0, server_default='0')
    forecast_2024_25 = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_2025_26_estimating_officer = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_2025_26_controlling_officer = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_2025_26_admin_dept = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_2025_26_finance_dept = Column(BigInteger, nullable=False, default=0, server_default='0')
    
    __table_args__ = (
        UniqueConstraint('fiscal_year', 'sub_scheme_code', 'district', 'unit_account', 
                        name='uq_unit_expenditure_natural_key_v2'),
    )


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

class Migration(Base):
    __tablename__ = 'schema_migrations'
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True, nullable=False)
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PayMatrix(Base):
    __tablename__ = 'pay_matrix'
    id = Column(Integer, primary_key=True, index=True)
    stage = Column(String(5), nullable=False, index=True)
    level = Column(Integer, nullable=False)
    basic_pay = Column(Integer, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('stage', 'level', name='uq_pay_matrix_stage_level'),
        CheckConstraint('level >= 1 AND level <= 40', name='chk_pay_matrix_level_range'),
        CheckConstraint('basic_pay > 0', name='chk_pay_matrix_basic_pay_positive'),
    )