from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import pandas as pd
import json
import logging

from src.database import get_db
from src.core.templates import render
from src.config import REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_district import get_district_from_taluka
from src.utils_auth import get_auth_level, get_auth_unit, get_fiscal_year
from src.utils_fiscal_year import get_default_fiscal_year

from src.schemes.s2053.common.services.abstract_service import SubSchemeAbstractService
from .models import UnitExpenditure
from .config import UNIT_ACCOUNT_MAP_MR
from .helpers import get_no_cache_headers

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20530387/district-wise-abstract",
    tags=["UI - जिल्हानिहाय गोषवारा"],
    include_in_schema=False
)

_abstract_service = SubSchemeAbstractService(
    model_class=UnitExpenditure,
    unit_account_map=UNIT_ACCOUNT_MAP_MR,
    fiscal_year_field='budget_curr_estimating_officer',
    expenditure_field='expenditure_prev2',
    current_budget_field='budget_prev1',
    forecast_field='forecast_prev1'
)


@router.get("", response_class=HTMLResponse)
async def ui_district_wise_abstract(request: Request, db: Session = Depends(get_db)):
    """
    Display district-wise abstract report.
    
    This endpoint uses the shared SubSchemeAbstractService for data retrieval,
    ensuring consistent logic across all sub-schemes and proper fiscal year caching.
    """
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    
    fiscal_year = get_fiscal_year(request) or get_default_fiscal_year(db)
    
    if auth_level not in ('', 'district', 'taluka', 'dco'):
        logger.warning(f"Invalid auth_level: {auth_level} from {request.client}")
        auth_level = ''
    
    if auth_level == 'district' and auth_unit == DCO_STAFF_IDENTIFIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        if auth_level == 'district' and auth_unit:
            pivot_df = _abstract_service.get_district_abstract_data(
                db=db,
                district=auth_unit,
                fiscal_year=fiscal_year
            )
            charts_data = _abstract_service.get_district_abstract_charts_data(
                db=db,
                district=auth_unit,
                fiscal_year=fiscal_year
            )
            expected_headers = ['Subheadings', auth_unit]
            
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            if district_name:
                pivot_df = _abstract_service.get_district_abstract_data(
                    db=db,
                    district=district_name,
                    fiscal_year=fiscal_year
                )
                charts_data = _abstract_service.get_district_abstract_charts_data(
                    db=db,
                    district=district_name,
                    fiscal_year=fiscal_year
                )
                expected_headers = ['Subheadings', district_name]
            else:
                logger.warning(f"Taluka not found: {auth_unit}")
                pivot_df = pd.DataFrame()
                charts_data = {}
                expected_headers = ['Subheadings']
                
        else:
            pivot_df = _abstract_service.get_abstract_data(
                db=db,
                fiscal_year=fiscal_year
            )
            charts_data = _abstract_service.get_all_districts_abstract_charts_data(
                db=db,
                fiscal_year=fiscal_year
            )
            expected_headers = ['Subheadings'] + REGULAR_DISTRICTS + ['Total']
    
    except Exception as e:
        logger.error(
            f"Error fetching abstract data: auth_level={auth_level}, "
            f"auth_unit={auth_unit}, fiscal_year={fiscal_year}, "
            f"error={type(e).__name__}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Error loading data. Please try again or contact support."
        )
    
    if pivot_df.empty:
        response = render(request, 
            "schemes/s2053/subs/s20530387/district_wise_abstract.html",
            {
                "request": request,
                "resource_name": "जिल्हानिहाय गोषवारा",
                "headers": expected_headers,
                "data_rows": [],
                "total_row": None,
                "auth_level": auth_level,
                "auth_unit": auth_unit,
                "fiscal_year": fiscal_year,
                "chart_data_json": json.dumps(charts_data)
            }
        )
        response.headers.update(get_no_cache_headers())
        return response
    
    if auth_level in ('district', 'taluka'):
        total_row_dict = None
    else:
        rows_to_exclude = ['10- Contractual Services', '16- Publications']
        rows_to_exclude_existing = [r for r in rows_to_exclude if r in pivot_df.index]
        
        df_for_column_totals = pivot_df.drop(
            index=rows_to_exclude_existing,
            errors='ignore'
        )
        column_totals = df_for_column_totals.sum(axis=0)
        column_totals.name = 'Total'
        
        total_row_dict = column_totals.astype(int).to_dict()
        total_row_dict['Subheadings'] = 'एकूण'
    
    pivot_df_display = pivot_df.reset_index()
    
    pivot_df_display['Subheadings'] = pivot_df_display['Subheadings'].map(
        UNIT_ACCOUNT_MAP_MR
    ).fillna(pivot_df_display['Subheadings'])
    
    headers = list(pivot_df_display.columns)
    int_cols = [
        col for col in headers
        if col not in ['Subheadings', 'Total'] and col in pivot_df_display.columns
    ]
    if 'Total' in pivot_df_display.columns:
        int_cols.append('Total')
    
    for col in int_cols:
        pivot_df_display[col] = pivot_df_display[col].astype(int)
    
    data_rows = pivot_df_display.to_dict(orient='records')
    
    response = render(request, 
        "schemes/s2053/subs/s20530387/district_wise_abstract.html",
        {
            "request": request,
            "resource_name": "जिल्हानिहाय गोषवारा",
            "headers": headers,
            "data_rows": data_rows,
            "total_row": total_row_dict,
            "districts_mr": DISTRICTS_MR,
            "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
            "auth_level": auth_level,
            "auth_unit": auth_unit,
            "fiscal_year": fiscal_year,
            "chart_data_json": json.dumps(charts_data)
        }
    )
    response.headers.update(get_no_cache_headers())
    return response
