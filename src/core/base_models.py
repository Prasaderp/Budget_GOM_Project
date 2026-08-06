"""Base model mixins for scheme-specific models"""
from sqlalchemy import Column, String, Integer, CHAR
from sqlalchemy.ext.declarative import declared_attr
from src.core.taluka.models import TalukaScopedMixin
from src.database import Base

class SchemeModelMixin(TalukaScopedMixin):
    """Mixin providing common columns for all scheme-related models"""

    @declared_attr
    def fiscal_year(cls):
        return Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26', index=True)
    
    @declared_attr
    def scheme_code(cls):
        return Column(String(10), nullable=False, index=True)
    
    @declared_attr
    def sub_scheme_code(cls):
        return Column(String(15), nullable=False, index=True)
    
    @declared_attr
    def district(cls):
        return Column(String(100), nullable=False, index=True)

class BudgetDetailsMixin(SchemeModelMixin):
    """Mixin for budget post details type models"""
    
    @declared_attr
    def category(cls):
        return Column(String(50), nullable=False)
    
    @declared_attr
    def class_type(cls):
        return Column(String(50), nullable=False)

class PostStatusMixin(BudgetDetailsMixin):
    """Mixin for post status type models"""
    
    @declared_attr
    def status(cls):
        return Column(String(50), nullable=False)

class UnitExpenditureMixin(SchemeModelMixin):
    """Mixin for unit expenditure type models"""
    
    @declared_attr
    def unit_account(cls):
        return Column(String(200), nullable=False)

def create_scheme_model(base_class, scheme_code: str, table_suffix: str = ""):
    """
    Factory to create scheme-specific model classes dynamically.
    For schemes with identical structure, reuse existing tables.
    For schemes with different structure, create new tables.
    """
    return type(
        f"{base_class.__name__}_{scheme_code}",
        (base_class,),
        {'__tablename__': f'{base_class.__tablename__}{table_suffix}'}
    )

