"""UI routes for sub-scheme 20530028 - District Administration (Voted)"""
from fastapi import APIRouter
from .config import SCHEME_CONFIG
from .budget_post_details.controllers.api_controller import router as budget_details_api_router
from .budget_post_details.controllers.ui_controller import router as budget_details_ui_router
from .post_status.controllers.api_controller import router as post_status_api_router
from .post_status.controllers.ui_controller import router as post_status_ui_router
from .post_expenses.controllers.api_controller import router as post_expenses_api_router
from .post_expenses.controllers.ui_controller import router as post_expenses_ui_router
from .unit_expenditure.controllers.api_controller import router as unit_expenditure_api_router
from .unit_expenditure.controllers.ui_controller import router as unit_expenditure_ui_router
from .ui_budget_summary import router as budget_summary_router, get_budget_summary_data, get_district_budget_summary_data
from .ui_abstract import router as abstract_router
from .ui_category_info import router as category_info_router
from .post_expenses import (
    get_post_expenses_summary_data,
    get_district_post_expenses_summary_data,
    get_post_expenses_charts_data,
    get_district_post_expenses_charts_data
)

budget_details_router = APIRouter()
budget_details_router.include_router(budget_details_api_router)
budget_details_router.include_router(budget_details_ui_router)

post_status_router = APIRouter()
post_status_router.include_router(post_status_api_router)
post_status_router.include_router(post_status_ui_router)

post_expenses_router = APIRouter()
post_expenses_router.include_router(post_expenses_api_router)
post_expenses_router.include_router(post_expenses_ui_router)

unit_expenditure_router = APIRouter()
unit_expenditure_router.include_router(unit_expenditure_api_router)
unit_expenditure_router.include_router(unit_expenditure_ui_router)

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
    'get_district_budget_summary_data',
    'get_post_expenses_summary_data',
    'get_district_post_expenses_summary_data',
    'get_post_expenses_charts_data',
    'get_district_post_expenses_charts_data'
]
