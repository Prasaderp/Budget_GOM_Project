"""Database models for sub-scheme 2215 - Water Scarcity."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


class DistrictExpenditure2215(Base):
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
    expenditure_2022_23 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Actual expenditure 2022-2023")
    expenditure_2023_24 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Actual expenditure 2023-2024")
    expenditure_2024_25 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Actual expenditure 2024-2025")

    # Budget estimate for current fiscal year
    budget_estimate_2025_26 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Budget estimate 2025-2026")
    
    # Revised budget demand for current fiscal year
    revised_demand_2025_26 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Revised budget demand 2025-2026")
    
    # Budget estimate for next fiscal year
    budget_estimate_2026_27 = Column(BigInteger, nullable=False, default=0, server_default="0", comment="Budget estimate 2026-2027")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "account_head_code",
            "district",
            name="uq_district_exp_2215_natural_key",
        ),
        CheckConstraint("expenditure_2022_23 >= 0", name="chk_exp_2223_non_negative_2215"),
        CheckConstraint("expenditure_2023_24 >= 0", name="chk_exp_2324_non_negative_2215"),
        CheckConstraint("expenditure_2024_25 >= 0", name="chk_exp_2425_non_negative_2215"),
        CheckConstraint("budget_estimate_2025_26 >= 0", name="chk_be_2526_non_negative_2215"),
        CheckConstraint("revised_demand_2025_26 >= 0", name="chk_revised_demand_2526_non_negative_2215"),
        CheckConstraint("budget_estimate_2026_27 >= 0", name="chk_be_2627_non_negative_2215"),
    )


SCHEME_CODE = "2215"
SUB_SCHEME_CODE = "2215"

