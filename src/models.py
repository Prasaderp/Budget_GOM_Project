"""Shared database models for Budget Management System

This file contains ONLY shared models used across all schemes.
Scheme-specific models are in: src/schemes/s{code}/subs/s{subcode}/models.py
"""
from src.database import Base
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from datetime import datetime


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
    
    from sqlalchemy import UniqueConstraint
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
    message_role = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, index=True, nullable=False, default=datetime.utcnow)
    
    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        UniqueConstraint('id', name='uq_assistant_chats_id'),
    )


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, index=True, nullable=False)
    record_id = Column(Integer, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
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
    salary_mode = Column(String(10), nullable=False, default='monthly', server_default='monthly')
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    @validates('year_range')
    def validate_year_range(self, key, value):
        if not value or '-' not in value:
            raise ValueError('Year range must be in format YYYY-YY')
        return value
    
    @validates('salary_mode')
    def validate_salary_mode(self, key, value):
        if value not in ('monthly', 'annual'):
            raise ValueError('Salary mode must be monthly or annual')
        return value


class DataFillingPeriod(Base):
    __tablename__ = 'data_filling_periods'
    id = Column(Integer, primary_key=True, index=True)
    sub_scheme_code = Column(String(15), nullable=False, index=True, default='20530028', server_default='20530028')
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
    
    from sqlalchemy import UniqueConstraint, CheckConstraint
    __table_args__ = (
        UniqueConstraint('stage', 'level', name='uq_pay_matrix_stage_level'),
        CheckConstraint('level >= 1 AND level <= 40', name='chk_pay_matrix_level_range'),
        CheckConstraint('basic_pay > 0', name='chk_pay_matrix_basic_pay_positive'),
    )


# Models are now scheme-specific. Use src.utils_scheme.get_scheme_models() to get models dynamically.
