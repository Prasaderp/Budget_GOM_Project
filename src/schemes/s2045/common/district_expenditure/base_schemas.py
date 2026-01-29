"""Base Pydantic schema factory for district expenditure tables."""
from typing import Optional, List, Tuple, Type
from pydantic import BaseModel, ConfigDict, Field, field_validator


def create_district_expenditure_schemas(
    scheme_code: str,
    sub_scheme_code: str,
    allowed_districts: List[str],
) -> Tuple[Type[BaseModel], Type[BaseModel], Type[BaseModel], Type[BaseModel]]:
    """
    Factory function to create Pydantic schemas for district expenditure.
    
    Args:
        scheme_code: Parent scheme code (e.g., '2045')
        sub_scheme_code: Sub-scheme code (e.g., '20450182')
        allowed_districts: List of valid district names
    
    Returns:
        Tuple of (Base, Create, Update, Response) schema classes
    """
    # Capture parameters to avoid class body shadowing
    _scheme_code = scheme_code
    _sub_scheme_code = sub_scheme_code
    
    class DistrictExpenditureBase(BaseModel):
        fiscal_year: Optional[str] = None
        scheme_code: Optional[str] = Field(default=_scheme_code, min_length=1, max_length=10)
        sub_scheme_code: Optional[str] = Field(default=_sub_scheme_code, min_length=1, max_length=15)
        district: Optional[str] = None
        
        expenditure_2022_23: Optional[int] = 0
        expenditure_2023_24: Optional[int] = 0
        expenditure_2024_25: Optional[int] = 0
        
        budget_estimate_2025_26: Optional[int] = 0
        quarterly_expenditure_apr_jul_2025: Optional[int] = 0
        budget_estimate_2026_27: Optional[int] = 0
        
        remarks: Optional[str] = None
        
        @field_validator(
            "expenditure_2022_23",
            "expenditure_2023_24",
            "expenditure_2024_25",
            "budget_estimate_2025_26",
            "quarterly_expenditure_apr_jul_2025",
            "budget_estimate_2026_27",
        )
        @classmethod
        def non_negative_int(cls, v: Optional[int]) -> Optional[int]:
            if v is None:
                return v
            if v < 0:
                raise ValueError("Value must be non-negative")
            if v > 999_999_999_999:
                raise ValueError("Value too large")
            return v
    
    # Store allowed districts for validator access
    _allowed_districts = allowed_districts
    
    class DistrictExpenditureCreate(DistrictExpenditureBase):
        district: str
        
        @field_validator("district")
        @classmethod
        def validate_district(cls, v: str) -> str:
            if v not in _allowed_districts:
                raise ValueError(f"Invalid district for {_sub_scheme_code}")
            return v
    
    class DistrictExpenditureUpdate(DistrictExpenditureBase):
        pass
    
    class DistrictExpenditureResponse(DistrictExpenditureBase):
        id: int
        model_config = ConfigDict(from_attributes=True)
    
    return (
        DistrictExpenditureBase,
        DistrictExpenditureCreate,
        DistrictExpenditureUpdate,
        DistrictExpenditureResponse,
    )
