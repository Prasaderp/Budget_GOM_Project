"""Base handler for category-wise information reports"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Type
import logging

from src.database import get_db
from src.core.templates import render
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_auth import get_auth_unit, get_auth_role, get_auth_level, get_auth_user, is_authenticated
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from ..services.category_info_service import CategoryInfoService
from ..utils.helpers import get_no_cache_headers

logger = logging.getLogger(__name__)


def create_category_info_router(
    prefix: str,
    post_expenses_model: Type,
    template_path: str
) -> APIRouter:
    """
    Factory function to create configured category info router.
    
    Args:
        prefix: Router prefix (e.g., "/ui/s20450091/category-wise-info")
        post_expenses_model: PostExpenses model class
        template_path: Path to template
    
    Returns:
        Configured APIRouter instance
    """
    router = APIRouter(
        prefix=prefix,
        tags=["UI - संवर्गनिहाय माहिती"],
        include_in_schema=False
    )
    
    category_service = CategoryInfoService(post_expenses_model=post_expenses_model)
    
    @router.get("", response_class=HTMLResponse)
    async def ui_category_wise_info(request: Request, db: Session = Depends(get_db)):
        """Display category-wise information with strict sub_scheme_code isolation"""
        auth_level = get_auth_level(request)
        auth_unit = get_auth_unit(request)
        
        if auth_level in ('district', 'taluka') or (auth_level == 'district' and auth_unit == DCO_STAFF_IDENTIFIER):
            raise HTTPException(status_code=403, detail="Access denied")
        
        _, sub_scheme = get_scheme_from_cookies(request)
        if not sub_scheme:
            raise HTTPException(status_code=400, detail="Subscheme not specified")
        
        fiscal_year = get_fiscal_year_from_request(request, db)
        
        try:
            table_rows, totals = category_service.get_category_data(
                db=db,
                sub_scheme_code=sub_scheme,
                fiscal_year=fiscal_year
            )
        except Exception as e:
            logger.error(
                f"Error fetching category data: sub_scheme={sub_scheme}, "
                f"fiscal_year={fiscal_year}, error={type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Error loading data. Please try again or contact support."
            )
        
        response = render(request, 
            template_path,
            {
                "request": request,
                "resource_name": "संवर्गनिहाय माहिती",
                "table_rows": table_rows,
                "totals": totals,
                "auth_level": auth_level
            }
        )
        response.headers.update(get_no_cache_headers())
        return response
    
    return router
