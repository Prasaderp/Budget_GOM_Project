"""Database models for scheme 0029."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


class DistrictRevenue0029(Base):
    __tablename__ = "district_revenue_0029"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="0029", server_default="0029", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="0029", server_default="0029", index=True)

    table_section_code = Column(String(20), nullable=False, index=True)
    district = Column(String(100), nullable=False)

    actual_2017_18 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2018_19 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2019_20 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate_2020_21 = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_2020_21 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2021_22 = Column(BigInteger, nullable=False, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "table_section_code",
            "district",
            name="uq_district_rev_0029_natural_key",
        ),
        CheckConstraint("actual_2017_18 >= 0", name="chk_actual_1718_non_negative_0029"),
        CheckConstraint("actual_2018_19 >= 0", name="chk_actual_1819_non_negative_0029"),
        CheckConstraint("actual_2019_20 >= 0", name="chk_actual_1920_non_negative_0029"),
        CheckConstraint("budget_estimate_2020_21 >= 0", name="chk_budget_est_2021_non_negative_0029"),
        CheckConstraint("revised_estimate_2020_21 >= 0", name="chk_revised_est_2021_non_negative_0029"),
        CheckConstraint("budget_estimate_2021_22 >= 0", name="chk_be_2122_non_negative_0029"),
    )


SCHEME_CODE = "0029"
SUB_SCHEME_CODE = "0029"

