"""Database models for sub-scheme 2215 - Water Scarcity."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.core.taluka.models import TalukaScopedMixin
from src.database import Base


class DistrictExpenditure2215(TalukaScopedMixin, Base):
    """District-wise expenditure for scheme 2215 with account heads.
    
    Supports multiple account heads (e.g., 2215A195, 2215A201) with flexible
    fiscal year columns. Each account head can have multiple district offices.
    """
    __tablename__ = "district_expenditure_2215"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="2215", server_default="2215", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="2215", server_default="2215", index=True)

    account_head_code = Column(String(20), nullable=False, index=True, comment="Account head code (e.g., 2215A195, 2215A201)")
    district = Column(String(100), nullable=False, index=True, comment="District office name")

    # Actual expenditure columns (historical data)
    expenditure_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Actual expenditure 3 years before")
    expenditure_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Actual expenditure 2 years before")
    expenditure_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Actual expenditure 1 year before")

    # Budget estimate for current fiscal year
    budget_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Budget estimate current FY")
    
    # Revised budget demand for current fiscal year
    revised_demand_curr = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Revised budget demand current FY")
    
    # Budget estimate for next fiscal year
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Budget estimate next FY")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "account_head_code",
            "district",
            "taluka",
            name="uq_district_exp_2215_natural_key",
        ),
        CheckConstraint("expenditure_prev3 >= 0", name="chk_exp_prev3_non_negative_2215"),
        CheckConstraint("expenditure_prev2 >= 0", name="chk_exp_prev2_non_negative_2215"),
        CheckConstraint("expenditure_prev1 >= 0", name="chk_exp_prev1_non_negative_2215"),
        CheckConstraint("budget_estimate_curr >= 0", name="chk_be_curr_non_negative_2215"),
        CheckConstraint("revised_demand_curr >= 0", name="chk_revised_demand_curr_non_negative_2215"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_next_non_negative_2215"),
    )


SCHEME_CODE = "2215"
SUB_SCHEME_CODE = "2215"

