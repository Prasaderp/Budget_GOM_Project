"""Routers for sub-scheme 20450262."""
from src.schemes.s2045.common.district_expenditure import (
    create_district_expenditure_routers,
    export_unified_workbook_async,
)
from .config import SUB_SCHEME_CODE
from .models import DistrictExpenditure20450262
from .helpers import helper


# Create routers using the shared factory
# Excel export uses the UNIFIED export that includes ALL 3 sub-schemes
ui_router, api_router = create_district_expenditure_routers(
    sub_scheme_code=SUB_SCHEME_CODE,
    model_class=DistrictExpenditure20450262,
    helper=helper,
    template_base_path="schemes/s2045/subs/s20450262",
    resource_name_mr="20450262 जिल्हानिहाय खर्च",
    excel_export_fn=export_unified_workbook_async,
)

__all__ = ['ui_router', 'api_router']
