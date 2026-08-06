"""Database models for scheme 0029."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.core.taluka.models import TalukaScopedMixin
from src.database import Base


class DistrictRevenue0029(TalukaScopedMixin, Base):
    __tablename__ = "district_revenue_0029"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="0029", server_default="0029", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="0029", server_default="0029", index=True)

    table_section_code = Column(String(20), nullable=False, index=True)
    district = Column(String(100), nullable=False)

    actual_prev3 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_prev2 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_prev1 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_curr = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_next = Column(BigInteger, nullable=False, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "table_section_code",
            "district",
            "taluka",
            name="uq_district_rev_0029_natural_key",
        ),
        CheckConstraint("actual_prev3 >= 0", name="chk_actual_prev3_non_negative_0029"),
        CheckConstraint("actual_prev2 >= 0", name="chk_actual_prev2_non_negative_0029"),
        CheckConstraint("actual_prev1 >= 0", name="chk_actual_prev1_non_negative_0029"),
        CheckConstraint("budget_estimate_curr >= 0", name="chk_budget_est_curr_non_negative_0029"),
        CheckConstraint("revised_estimate_curr >= 0", name="chk_revised_est_curr_non_negative_0029"),
        CheckConstraint("budget_estimate_next >= 0", name="chk_be_next_non_negative_0029"),
    )


SCHEME_CODE = "0029"
SUB_SCHEME_CODE = "0029"

