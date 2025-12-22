"""UI routes for sub-scheme 20530153 - District Administration (Charged)"""
from fastapi import APIRouter
from .config import SCHEME_CONFIG
from .ui_budget_details import router as budget_details_router
from .ui_post_status import router as post_status_router
from .ui_post_expenses import router as post_expenses_router
from .ui_unit_expenditure import router as unit_expenditure_router
from .ui_budget_summary import router as budget_summary_router, get_budget_summary_data, get_district_budget_summary_data
from .ui_abstract import router as abstract_router
from .ui_category_info import router as category_info_router

router = APIRouter(tags=[f"UI - {SCHEME_CONFIG.name_mr}"], include_in_schema=False)

__all__ = [
    'router',
    'budget_details_router',
    'post_status_router', 
    'post_expenses_router',
    'unit_expenditure_router',
    'budget_summary_router',
    'abstract_router',
    'category_info_router',
    'get_budget_summary_data',
    'get_district_budget_summary_data'
]
