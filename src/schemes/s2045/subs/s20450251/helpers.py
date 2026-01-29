"""Helper utilities for sub-scheme 20450251."""
from src.schemes.s2045.common.district_expenditure import DistrictExpenditureHelper
from src.utils_district import get_request_info
from .config import SCHEME_CODE, SUB_SCHEME_CODE, KONKAN_DISTRICTS_NO_MUMBAI, TABLE_NAME
from .models import DistrictExpenditure20450251

# Create helper instance for this sub-scheme
helper = DistrictExpenditureHelper(
    sub_scheme_code=SUB_SCHEME_CODE,
    scheme_code=SCHEME_CODE,
    allowed_districts=KONKAN_DISTRICTS_NO_MUMBAI,
    model_class=DistrictExpenditure20450251,
    table_name=TABLE_NAME,
)

__all__ = ['helper', 'get_request_info']
