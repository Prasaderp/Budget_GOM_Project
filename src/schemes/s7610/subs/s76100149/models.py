"""Database models for sub-scheme 76100149."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


class DistrictExpenditure76100149(Base):
    __tablename__ = "district_expenditure_76100149"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="7610", server_default="7610", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="76100149", server_default="76100149", index=True)

    district = Column(String(100), nullable=False)

    expenditure_2022_23 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_2023_24 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_2024_25 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2026_27 = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "district",
            name="uq_district_exp_76100149_natural_key",
        ),
        CheckConstraint("expenditure_2022_23 >= 0", name="chk_exp_2223_non_negative"),
        CheckConstraint("expenditure_2023_24 >= 0", name="chk_exp_2324_non_negative"),
        CheckConstraint("expenditure_2024_25 >= 0", name="chk_exp_2425_non_negative"),
        CheckConstraint("budget_estimate >= 0", name="chk_budget_est_non_negative"),
        CheckConstraint("revised_estimate >= 0", name="chk_revised_est_non_negative"),
        CheckConstraint("budget_estimate_2026_27 >= 0", name="chk_be_2627_non_negative"),
    )


SCHEME_CODE = "7610"
SUB_SCHEME_CODE = "76100149"

