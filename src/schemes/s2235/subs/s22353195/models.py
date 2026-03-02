"""Database models for sub-scheme 22353195 - Social Security and Welfare (District Expenditure)."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


class DistrictExpenditure22353195(Base):
    __tablename__ = "district_expenditure_22353195"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="2235", server_default="2235", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="22353195", server_default="22353195", index=True)

    district = Column(String(100), nullable=False)

    expenditure_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_grant_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_grant_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "district",
            name="uq_district_exp_22353195_natural_key",
        ),
        CheckConstraint("expenditure_prev3 >= 0", name="chk_22353195_exp_2223_non_negative"),
        CheckConstraint("expenditure_prev2 >= 0", name="chk_22353195_exp_2324_non_negative"),
        CheckConstraint("expenditure_prev1 >= 0", name="chk_22353195_exp_2425_non_negative"),
        CheckConstraint("budget_grant_curr >= 0", name="chk_22353195_bg_2526_non_negative"),
        CheckConstraint("revised_grant_curr >= 0", name="chk_22353195_rg_2526_non_negative"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_22353195_be_2627_non_negative"),
    )


SCHEME_CODE = "2235"
SUB_SCHEME_CODE = "22353195"
