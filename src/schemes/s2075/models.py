"""Database models for scheme 2075 - Miscellaneous General Services.

Defines tables for:
- SubHeadExpenditure2075: Single entry for sub-scheme 20750249 (DCO level)
- DistrictExpenditure2075: District-wise entries for sub-scheme 20750294
"""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint
from src.core.taluka.models import TalukaScopedMixin
from src.database import Base

SCHEME_CODE = "2075"


class SubHeadExpenditure2075(Base):
    """Sub-head expenditure model for sub-scheme 20750249."""
    __tablename__ = "sub_head_expenditure_2075"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="20750249", server_default="20750249", index=True)
    sub_head = Column(String(500), nullable=False)
    
    # Expenditure fields (all BigInteger for large values, non-negative)
    expenditure_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("fiscal_year", "sub_scheme_code", "sub_head", name="uq_sub_head_exp_2075_natural_key"),
        CheckConstraint("expenditure_prev3 >= 0", name="chk_exp_prev3_non_negative_2075_sub"),
        CheckConstraint("expenditure_prev2 >= 0", name="chk_exp_prev2_non_negative_2075_sub"),
        CheckConstraint("expenditure_prev1 >= 0", name="chk_exp_prev1_non_negative_2075_sub"),
        CheckConstraint("budget_estimate_curr >= 0", name="chk_budget_est_curr_non_negative_2075_sub"),
        CheckConstraint("revised_estimate_curr >= 0", name="chk_revised_est_curr_non_negative_2075_sub"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_next_non_negative_2075_sub"),
    )


class DistrictExpenditure2075(TalukaScopedMixin, Base):
    """District expenditure model for sub-scheme 20750294."""
    __tablename__ = "district_expenditure_2075"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="20750294", server_default="20750294", index=True)
    district = Column(String(100), nullable=False, index=True)
    
    # Expenditure fields (all BigInteger for large values, non-negative)
    expenditure_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("fiscal_year", "sub_scheme_code", "district", "taluka", name="uq_district_exp_2075_natural_key"),
        CheckConstraint("expenditure_prev3 >= 0", name="chk_exp_prev3_non_neg_2075_dist"),
        CheckConstraint("expenditure_prev2 >= 0", name="chk_exp_prev2_non_neg_2075_dist"),
        CheckConstraint("expenditure_prev1 >= 0", name="chk_exp_prev1_non_neg_2075_dist"),
        CheckConstraint("budget_estimate_curr >= 0", name="chk_budget_est_curr_non_neg_2075_dist"),
        CheckConstraint("revised_estimate_curr >= 0", name="chk_revised_est_curr_non_neg_2075_dist"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_next_non_neg_2075_dist"),
    )
