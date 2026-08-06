"""Database models for sub-scheme 62450017 - Loans for Natural Calamities (Other Loans)."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.core.taluka.models import TalukaScopedMixin
from src.database import Base


class DistrictExpenditure62450017(TalukaScopedMixin, Base):
    __tablename__ = "district_expenditure_62450017"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="6245", server_default="6245", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="62450017", server_default="62450017", index=True)

    district = Column(String(100), nullable=False)

    expenditure_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_grant_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "district",
            "taluka",
            name="uq_district_exp_62450017_natural_key",
        ),
        CheckConstraint("expenditure_prev3 >= 0", name="chk_exp_prev3_non_negative"),
        CheckConstraint("expenditure_prev2 >= 0", name="chk_exp_prev2_non_negative"),
        CheckConstraint("expenditure_prev1 >= 0", name="chk_exp_prev1_non_negative"),
        CheckConstraint("budget_grant_curr >= 0", name="chk_bg_curr_non_negative"),
        CheckConstraint("revised_estimate_curr >= 0", name="chk_re_curr_non_negative"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_next_non_negative"),
    )


SCHEME_CODE = "6245"
SUB_SCHEME_CODE = "62450017"


