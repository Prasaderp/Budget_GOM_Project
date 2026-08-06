"""Database models for sub-scheme 20290046 - District Administration (Charged)."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, Float, CheckConstraint, UniqueConstraint
from sqlalchemy.types import Numeric
from src.database import Base
from src.core.base_models import BudgetDetailsMixin, PostStatusMixin, UnitExpenditureMixin
from .config import SCHEME_CODE, SUB_SCHEME_CODE


class BudgetPostDetails20290046(BudgetDetailsMixin, Base):
    __tablename__ = "budget_post_details_20290046"

    id = Column(Integer, primary_key=True, index=True)
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
    designation = Column(String(200), nullable=False, index=True)
    sanctioned_posts_prev1 = Column(Integer, nullable=False, default=0, server_default='0')
    sanctioned_posts_curr = Column(Integer, nullable=False, default=0, server_default='0')
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
        UniqueConstraint('fiscal_year', 'district', 'category', 'class_type', 'designation', 'taluka',
                         name='uq_bpd_20290046_natural_key'),
        CheckConstraint('sanctioned_posts_prev1 >= 0', name='chk_bpd_20290046_posts_prev1'),
        CheckConstraint('sanctioned_posts_curr >= 0', name='chk_bpd_20290046_posts_curr'),
        CheckConstraint('basic_pay >= 0', name='chk_bpd_20290046_basic_pay'),
        CheckConstraint("hra_rate IN ('X', 'Y', 'Z')", name='chk_bpd_20290046_hra_rate'),
    )


class PostStatus20290046(PostStatusMixin, Base):
    __tablename__ = "post_status_20290046"

    id = Column(Integer, primary_key=True, index=True)
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
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
        UniqueConstraint('fiscal_year', 'district', 'category', 'class_type', 'status', 'taluka',
                         name='uq_ps_20290046_natural_key'),
        CheckConstraint('posts >= 0', name='chk_ps_20290046_posts'),
        CheckConstraint('salary >= 0', name='chk_ps_20290046_salary'),
    )


class PostExpenses20290046(BudgetDetailsMixin, Base):
    __tablename__ = "post_expenses_20290046"

    id = Column(Integer, primary_key=True, index=True)
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
    filled_posts = Column(Integer, nullable=False, default=0, server_default='0')
    vacant_posts = Column(Integer, nullable=False, default=0, server_default='0')
    medical_expenses = Column(BigInteger, nullable=False, default=0, server_default='0')
    festival_advance = Column(BigInteger, nullable=False, default=0, server_default='0')
    swagram_maharashtra_darshan = Column(BigInteger, nullable=False, default=0, server_default='0')
    seventh_pay_commission_difference_nps = Column(Float)
    nps = Column(Float)
    seventh_pay_commission_difference = Column(Float)
    other = Column(BigInteger, nullable=False, default=0, server_default='0')

    __table_args__ = (
        UniqueConstraint('fiscal_year', 'district', 'category', 'class_type', 'taluka',
                         name='uq_pe_20290046_natural_key'),
        CheckConstraint('filled_posts >= 0', name='chk_pe_20290046_filled_posts'),
        CheckConstraint('vacant_posts >= 0', name='chk_pe_20290046_vacant_posts'),
    )


class UnitExpenditure20290046(UnitExpenditureMixin, Base):
    __tablename__ = "unit_expenditure_20290046"

    id = Column(Integer, primary_key=True, index=True)
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default=SUB_SCHEME_CODE, server_default=SUB_SCHEME_CODE, index=True)
    expenditure_prev4 = Column(BigInteger, nullable=False, default=0, server_default='0')
    expenditure_prev3 = Column(BigInteger, nullable=False, default=0, server_default='0')
    expenditure_prev2 = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_prev1 = Column(BigInteger, nullable=False, default=0, server_default='0')
    forecast_prev1 = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_curr_estimating_officer = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_curr_controlling_officer = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_curr_admin_dept = Column(BigInteger, nullable=False, default=0, server_default='0')
    budget_curr_finance_dept = Column(BigInteger, nullable=False, default=0, server_default='0')

    __table_args__ = (
        UniqueConstraint('fiscal_year', 'district', 'unit_account', 'taluka',
                         name='uq_ue_20290046_natural_key'),
    )


BudgetPostDetails = BudgetPostDetails20290046
PostStatus = PostStatus20290046
PostExpenses = PostExpenses20290046
UnitExpenditure = UnitExpenditure20290046
