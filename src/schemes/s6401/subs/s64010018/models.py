"""Database models for sub-scheme 64010018 - Loans for Crop Husbandry."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.core.taluka.models import TalukaScopedMixin
from src.database import Base


class DistrictExpenditure64010018(TalukaScopedMixin, Base):
    __tablename__ = "district_expenditure_64010018"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="6401", server_default="6401", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="64010018", server_default="64010018", index=True)

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
            name="uq_district_exp_64010018_natural_key",
        ),
        CheckConstraint("expenditure_prev3 >= 0", name="chk_exp_prev3_non_negative"),
        CheckConstraint("expenditure_prev2 >= 0", name="chk_exp_prev2_non_negative"),
        CheckConstraint("expenditure_prev1 >= 0", name="chk_exp_prev1_non_negative"),
        CheckConstraint("budget_grant_curr >= 0", name="chk_bg_curr_non_negative"),
        CheckConstraint("revised_estimate_curr >= 0", name="chk_re_curr_non_negative"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_next_non_negative"),
    )


SCHEME_CODE = "6401"
SUB_SCHEME_CODE = "64010018"


