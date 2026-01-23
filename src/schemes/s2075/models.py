"""Database models for scheme 2075 - Miscellaneous General Services.

Defines tables for:
- SubHeadExpenditure2075: Single entry for sub-scheme 20750249 (DCO level)
- DistrictExpenditure2075: District-wise entries for sub-scheme 20750294
"""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint
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
    expenditure_2022_23 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_2023_24 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_2024_25 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2026_27 = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("fiscal_year", "sub_scheme_code", "sub_head", name="uq_sub_head_exp_2075_natural_key"),
        CheckConstraint("expenditure_2022_23 >= 0", name="chk_exp_2223_non_negative_2075_sub"),
        CheckConstraint("expenditure_2023_24 >= 0", name="chk_exp_2324_non_negative_2075_sub"),
        CheckConstraint("expenditure_2024_25 >= 0", name="chk_exp_2425_non_negative_2075_sub"),
        CheckConstraint("budget_estimate >= 0", name="chk_budget_est_non_negative_2075_sub"),
        CheckConstraint("revised_estimate >= 0", name="chk_revised_est_non_negative_2075_sub"),
        CheckConstraint("budget_estimate_2026_27 >= 0", name="chk_be_2627_non_negative_2075_sub"),
    )


class DistrictExpenditure2075(Base):
    """District expenditure model for sub-scheme 20750294."""
    __tablename__ = "district_expenditure_2075"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default=SCHEME_CODE, server_default=SCHEME_CODE, index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="20750294", server_default="20750294", index=True)
    district = Column(String(100), nullable=False, index=True)
    
    # Expenditure fields (all BigInteger for large values, non-negative)
    expenditure_2022_23 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_2023_24 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_2024_25 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2026_27 = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("fiscal_year", "sub_scheme_code", "district", name="uq_district_exp_2075_natural_key"),
        CheckConstraint("expenditure_2022_23 >= 0", name="chk_exp_2223_non_neg_2075_dist"),
        CheckConstraint("expenditure_2023_24 >= 0", name="chk_exp_2324_non_neg_2075_dist"),
        CheckConstraint("expenditure_2024_25 >= 0", name="chk_exp_2425_non_neg_2075_dist"),
        CheckConstraint("budget_estimate >= 0", name="chk_budget_est_non_neg_2075_dist"),
        CheckConstraint("revised_estimate >= 0", name="chk_revised_est_non_neg_2075_dist"),
        CheckConstraint("budget_estimate_2026_27 >= 0", name="chk_be_2627_non_neg_2075_dist"),
    )
