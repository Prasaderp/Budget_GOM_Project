"""Database models for sub-scheme 22350311 - Social Security and Welfare (District Expenditure)."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


class DistrictExpenditure22350311(Base):
    __tablename__ = "district_expenditure_22350311"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="2235", server_default="2235", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="22350311", server_default="22350311", index=True)

    district = Column(String(100), nullable=False)

    expenditure_2022_23 = Column(BigInteger, nullable=False, default=0, server_default="0")
    expenditure_2023_24 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_grant_2024_25 = Column(BigInteger, nullable=False, default=0, server_default="0")

    revised_grant_2025_26 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2026_27 = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "district",
            name="uq_district_exp_22350311_natural_key",
        ),
        CheckConstraint("expenditure_2022_23 >= 0", name="chk_22350311_exp_2223_non_negative"),
        CheckConstraint("expenditure_2023_24 >= 0", name="chk_22350311_exp_2324_non_negative"),
        CheckConstraint("budget_grant_2024_25 >= 0", name="chk_22350311_bg_2425_non_negative"),
        CheckConstraint("revised_grant_2025_26 >= 0", name="chk_22350311_rg_2526_non_negative"),
        CheckConstraint("budget_estimate_2026_27 >= 0", name="chk_22350311_be_2627_non_negative"),
    )


SCHEME_CODE = "2235"
SUB_SCHEME_CODE = "22350311"
