"""Database models for sub-scheme 2245."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


class DistrictExpenditure2245(Base):
    __tablename__ = "district_expenditure_2245"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="2245", server_default="2245", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="2245", server_default="2245", index=True)

    table_section_code = Column(String(20), nullable=False, index=True)
    district = Column(String(100), nullable=False)

    exp_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0")
    exp_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0")
    exp_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "table_section_code",
            "district",
            name="uq_district_exp_2245_natural_key",
        ),
        CheckConstraint("exp_prev3 >= 0", name="chk_exp_prev3_non_negative_2245"),
        CheckConstraint("exp_prev2 >= 0", name="chk_exp_prev2_non_negative_2245"),
        CheckConstraint("exp_prev1 >= 0", name="chk_exp_prev1_non_negative_2245"),
        CheckConstraint("budget_estimate_curr >= 0", name="chk_budget_est_curr_non_negative_2245"),
        CheckConstraint("revised_estimate_curr >= 0", name="chk_revised_est_curr_non_negative_2245"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_next_non_negative_2245"),
    )


SCHEME_CODE = "2245"
SUB_SCHEME_CODE = "2245"

