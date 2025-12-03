"""Database models for sub-scheme 20530028 - District Administration (Voted)."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, Float, CheckConstraint, UniqueConstraint
from sqlalchemy.types import Numeric
from src.database import Base

SCHEME_CODE = "2053"
SUB_SCHEME_CODE = "20530028"


class BudgetPostDetails20530028(Base):
    __tablename__ = "budget_post_details"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
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
        {'extend_existing': True}
    )


class PostStatus20530028(Base):
    __tablename__ = "post_status"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
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
        {'extend_existing': True}
    )


class PostExpenses20530028(Base):
    __tablename__ = "post_expenses"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
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
        {'extend_existing': True}
    )


class UnitExpenditure20530028(Base):
    __tablename__ = "unit_expenditure"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26')
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
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
        {'extend_existing': True}
    )


# Aliases for backward compatibility - these map to the scheme-specific classes
BudgetPostDetails = BudgetPostDetails20530028
PostStatus = PostStatus20530028
PostExpenses = PostExpenses20530028
UnitExpenditure = UnitExpenditure20530028
