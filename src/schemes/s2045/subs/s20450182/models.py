"""Database models for sub-scheme 20450182."""
from src.schemes.s2045.common.district_expenditure import create_district_expenditure_model
from .config import SCHEME_CODE, SUB_SCHEME_CODE, TABLE_NAME

# Create the model using the shared factory
DistrictExpenditure20450182 = create_district_expenditure_model(
    table_name=TABLE_NAME,
    scheme_code=SCHEME_CODE,
    sub_scheme_code=SUB_SCHEME_CODE,
)

__all__ = ['DistrictExpenditure20450182', 'SCHEME_CODE', 'SUB_SCHEME_CODE', 'TABLE_NAME']
