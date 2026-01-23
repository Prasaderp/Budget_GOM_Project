"""API routes for sub-scheme 20530378 - District Administration (Charged)

Secured with authentication, authorization, and audit logging.
"""
from fastapi import APIRouter

from src.core.secure_crud import create_secure_crud_routes
from .models import BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure
from .schemas import (
    BudgetPostDetailsCreate, BudgetPostDetailsUpdate, BudgetPostDetailsResponse,
    PostStatusCreate, PostStatusUpdate, PostStatusResponse,
    PostExpensesCreate, PostExpensesUpdate, PostExpensesResponse,
    UnitExpenditureCreate, UnitExpenditureUpdate, UnitExpenditureResponse
)
from .config import SCHEME_CONFIG

router = APIRouter(prefix=f"/api/schemes/{SCHEME_CONFIG.code}", tags=[f"API - {SCHEME_CONFIG.name_mr}"])

create_secure_crud_routes(
    router, BudgetPostDetails,
    BudgetPostDetailsCreate, BudgetPostDetailsUpdate, BudgetPostDetailsResponse,
    "budget-post-details", SCHEME_CONFIG.parent_scheme, SCHEME_CONFIG.code
)

create_secure_crud_routes(
    router, PostStatus,
    PostStatusCreate, PostStatusUpdate, PostStatusResponse,
    "post-status", SCHEME_CONFIG.parent_scheme, SCHEME_CONFIG.code
)

create_secure_crud_routes(
    router, PostExpenses,
    PostExpensesCreate, PostExpensesUpdate, PostExpensesResponse,
    "post-expenses", SCHEME_CONFIG.parent_scheme, SCHEME_CONFIG.code
)

create_secure_crud_routes(
    router, UnitExpenditure,
    UnitExpenditureCreate, UnitExpenditureUpdate, UnitExpenditureResponse,
    "unit-expenditure", SCHEME_CONFIG.parent_scheme, SCHEME_CONFIG.code
)
