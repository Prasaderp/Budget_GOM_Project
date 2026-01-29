"""Pydantic schemas for sub-scheme 20450182."""
from src.schemes.s2045.common.district_expenditure import create_district_expenditure_schemas
from .config import SCHEME_CODE, SUB_SCHEME_CODE, KONKAN_DISTRICTS_FULL

# Create schemas using the shared factory
(
    DistrictExpenditureBase,
    DistrictExpenditureCreate,
    DistrictExpenditureUpdate,
    DistrictExpenditureResponse,
) = create_district_expenditure_schemas(
    scheme_code=SCHEME_CODE,
    sub_scheme_code=SUB_SCHEME_CODE,
    allowed_districts=KONKAN_DISTRICTS_FULL,
)

__all__ = [
    'DistrictExpenditureBase',
    'DistrictExpenditureCreate',
    'DistrictExpenditureUpdate',
    'DistrictExpenditureResponse',
]
