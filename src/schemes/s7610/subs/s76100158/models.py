"""Database models for sub-scheme 76100158."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.core.taluka.models import TalukaScopedMixin
from src.database import Base


class DistrictExpenditure76100158(TalukaScopedMixin, Base):
    __tablename__ = "district_expenditure_76100158"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="7610", server_default="7610", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="76100158", server_default="76100158", index=True)

    district = Column(String(100), nullable=False)

    expenditure_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "district",
            "taluka",
            name="uq_district_exp_76100158_natural_key",
        ),
        CheckConstraint("expenditure_prev3 >= 0", name="chk_exp_2223_non_negative"),
        CheckConstraint("expenditure_prev2 >= 0", name="chk_exp_2324_non_negative"),
        CheckConstraint("expenditure_prev1 >= 0", name="chk_exp_2425_non_negative"),
        CheckConstraint("budget_estimate >= 0", name="chk_budget_est_non_negative"),
        CheckConstraint("revised_estimate >= 0", name="chk_revised_est_non_negative"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_2627_non_negative"),
    )


SCHEME_CODE = "7610"
SUB_SCHEME_CODE = "76100158"



