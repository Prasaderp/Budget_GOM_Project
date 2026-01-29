"""Base model factory for district expenditure tables in s2045 sub-schemes."""
from typing import Type
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


def create_district_expenditure_model(
    table_name: str,
    scheme_code: str,
    sub_scheme_code: str,
) -> Type[Base]:
    """
    Factory function to create a district expenditure model class.
    
    All s2045 district expenditure tables share the same structure:
    - fiscal_year, scheme_code, sub_scheme_code (keys)
    - district (English name)
    - expenditure_2022_23, expenditure_2023_24, expenditure_2024_25
    - budget_estimate_2025_26, quarterly_expenditure_apr_jul_2025, budget_estimate_2026_27
    - remarks
    
    Args:
        table_name: Database table name (e.g., 'district_expenditure_20450182')
        scheme_code: Parent scheme code (e.g., '2045')
        sub_scheme_code: Sub-scheme code (e.g., '20450182')
    
    Returns:
        SQLAlchemy model class
    """
    constraint_prefix = f"chk_{sub_scheme_code}"
    class_name = f"DistrictExpenditure_{sub_scheme_code}"
    
    # Use type() to create class with unique name at definition time
    # This avoids SQLAlchemy registry collision warnings
    DistrictExpenditureModel = type(
        class_name,
        (Base,),
        {
            "__tablename__": table_name,
            "__table_args__": (
                UniqueConstraint(
                    "fiscal_year",
                    "sub_scheme_code", 
                    "district",
                    name=f"uq_{table_name}_natural_key",
                ),
                CheckConstraint("expenditure_2022_23 >= 0", name=f"{constraint_prefix}_exp2223"),
                CheckConstraint("expenditure_2023_24 >= 0", name=f"{constraint_prefix}_exp2324"),
                CheckConstraint("expenditure_2024_25 >= 0", name=f"{constraint_prefix}_exp2425"),
                CheckConstraint("budget_estimate_2025_26 >= 0", name=f"{constraint_prefix}_be2526"),
                CheckConstraint("quarterly_expenditure_apr_jul_2025 >= 0", name=f"{constraint_prefix}_qe2025"),
                CheckConstraint("budget_estimate_2026_27 >= 0", name=f"{constraint_prefix}_be2627"),
            ),
            
            # Primary key
            "id": Column(Integer, primary_key=True, index=True),
            
            # Keys
            "fiscal_year": Column(CHAR(7), nullable=False, index=True),
            "scheme_code": Column(String(10), nullable=False, default=scheme_code, server_default=scheme_code, index=True),
            "sub_scheme_code": Column(String(15), nullable=False, default=sub_scheme_code, server_default=sub_scheme_code, index=True),
            
            # District
            "district": Column(String(100), nullable=False),
            
            # प्रत्यक्ष खर्च (Actual Expenditure)
            "expenditure_2022_23": Column(BigInteger, nullable=False, default=0, server_default="0"),
            "expenditure_2023_24": Column(BigInteger, nullable=False, default=0, server_default="0"),
            "expenditure_2024_25": Column(BigInteger, nullable=False, default=0, server_default="0"),
            
            # अर्थसंकल्पीय अंदाज 2025-2026 (Budget Estimate)
            "budget_estimate_2025_26": Column(BigInteger, nullable=False, default=0, server_default="0"),
            
            # माहे एप्रिल-2025 ते जुलै-2025 चारमाही प्रत्यक्ष खर्च (Quarterly April-July 2025)
            "quarterly_expenditure_apr_jul_2025": Column(BigInteger, nullable=False, default=0, server_default="0"),
            
            # सन 2026-2027 चे अर्थसंकल्पीय अंदाजपत्रक (Budget Estimate 2026-27)
            "budget_estimate_2026_27": Column(BigInteger, nullable=False, default=0, server_default="0"),
            
            # शेरा (Remarks)
            "remarks": Column(String(500), nullable=True),
            
            # Class attributes for easy access
            "SCHEME_CODE": scheme_code,
            "SUB_SCHEME_CODE": sub_scheme_code,
        }
    )
    
    return DistrictExpenditureModel
