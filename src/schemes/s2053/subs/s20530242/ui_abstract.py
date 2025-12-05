from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import io
import json
import logging

from src.database import get_db
from src.core.templates import templates
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_cache import ttl_cache
from src.utils_district import get_district_from_taluka
from .models import UnitExpenditure
from .config import UNIT_ACCOUNT_MAP_MR
from .helpers import get_no_cache_headers

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20530242/district-wise-abstract",
    tags=["UI - जिल्हानिहाय गोषवारा"],
    include_in_schema=False
)

@ttl_cache(ttl_seconds=180, use_global=True)
def get_district_abstract_data(db: Session, district: str) -> pd.DataFrame:
    data_query = db.query(
        UnitExpenditure.unit_account,
        UnitExpenditure.district,
        UnitExpenditure.budget_2025_26_estimating_officer
    ).filter(UnitExpenditure.district == district).all()

    if not data_query:
        return pd.DataFrame(columns=['Subheadings', district]).set_index('Subheadings')

    df = pd.DataFrame(data_query, columns=['Subheadings', 'District', 'Value'])
    pivot_df = df.pivot_table( index='Subheadings', columns='District', values='Value', fill_value=0, aggfunc=sum )
    pivot_df = pivot_df.reindex(columns=[district], fill_value=0)
    numeric_cols = pivot_df.columns
    for col in numeric_cols:
        pivot_df[col] = pd.to_numeric(pivot_df[col], errors='coerce').fillna(0).astype(int)
    return pivot_df

@ttl_cache(ttl_seconds=180, use_global=True)
def get_district_abstract_charts_data(db: Session, district: str) -> Dict[str, Any]:
    data_query = db.query(
        UnitExpenditure.unit_account,
        func.sum(UnitExpenditure.budget_2025_26_estimating_officer).label('budget'),
        func.sum(UnitExpenditure.expenditure_2023_24).label('expenditure'),
        func.sum(UnitExpenditure.budget_2024_25).label('current_budget'),
        func.sum(UnitExpenditure.forecast_2024_25).label('forecast')
    ).filter(UnitExpenditure.district == district).group_by(UnitExpenditure.unit_account).all()
    
    unit_accounts = []
    budgets, expenditures, current_budgets, forecasts = [], [], [], []
    
    for row in data_query:
        unit_accounts.append(UNIT_ACCOUNT_MAP_MR.get(row.unit_account, row.unit_account))
        budgets.append(int(row.budget or 0))
        expenditures.append(int(row.expenditure or 0))
        current_budgets.append(int(row.current_budget or 0))
        forecasts.append(int(row.forecast or 0))
    
    return {
        'labels': unit_accounts,
        'budgets': budgets,
        'expenditures': expenditures,
        'current_budgets': current_budgets,
        'forecasts': forecasts
    }

@ttl_cache(ttl_seconds=180, use_global=True)
def get_all_districts_abstract_charts_data(db: Session) -> Dict[str, Any]:
    data_query = db.query(
        UnitExpenditure.district,
        func.sum(UnitExpenditure.budget_2025_26_estimating_officer).label('budget'),
        func.sum(UnitExpenditure.expenditure_2023_24).label('expenditure'),
        func.sum(UnitExpenditure.budget_2024_25).label('current_budget'),
        func.sum(UnitExpenditure.forecast_2024_25).label('forecast')
    ).filter(
        UnitExpenditure.district != DCO_STAFF_IDENTIFIER
    ).group_by(UnitExpenditure.district).order_by(UnitExpenditure.district).all()
    
    districts = []
    budgets, expenditures, current_budgets, forecasts = [], [], [], []
    
    for row in data_query:
        districts.append(DISTRICTS_MR.get(row.district, row.district))
        budgets.append(int(row.budget or 0))
        expenditures.append(int(row.expenditure or 0))
        current_budgets.append(int(row.current_budget or 0))
        forecasts.append(int(row.forecast or 0))
    
    return {
        'labels': districts,
        'budgets': budgets,
        'expenditures': expenditures,
        'current_budgets': current_budgets,
        'forecasts': forecasts
    }

@ttl_cache(ttl_seconds=180, use_global=True)
def get_abstract_data(db: Session) -> pd.DataFrame:
    data_query = db.query(
        UnitExpenditure.unit_account,
        UnitExpenditure.district,
        UnitExpenditure.budget_2025_26_estimating_officer
    ).filter(
        UnitExpenditure.district != DCO_STAFF_IDENTIFIER
    ).all()

    if not data_query:
        return pd.DataFrame(columns=['Subheadings'] + REGULAR_DISTRICTS + ['Total']).set_index('Subheadings')

    df = pd.DataFrame(data_query, columns=['Subheadings', 'District', 'Value'])
    pivot_df = df.pivot_table( index='Subheadings', columns='District', values='Value', fill_value=0, aggfunc=sum )
    pivot_df = pivot_df.reindex(columns=REGULAR_DISTRICTS, fill_value=0)
    numeric_cols = pivot_df.columns
    for col in numeric_cols:
        pivot_df[col] = pd.to_numeric(pivot_df[col], errors='coerce').fillna(0).astype(int)
    pivot_df['Total'] = pivot_df.sum(axis=1)
    return pivot_df

@router.get("", response_class=HTMLResponse)
async def ui_district_wise_abstract(request: Request, db: Session = Depends(get_db)):
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    
    if auth_level == 'district' and auth_unit == DCO_STAFF_IDENTIFIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if auth_level == 'district' and auth_unit:
        pivot_df = get_district_abstract_data(db, auth_unit)
        charts_data = get_district_abstract_charts_data(db, auth_unit)
        expected_headers = ['Subheadings', auth_unit]
    elif auth_level == 'taluka' and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        if district_name:
            pivot_df = get_district_abstract_data(db, district_name)
            charts_data = get_district_abstract_charts_data(db, district_name)
            expected_headers = ['Subheadings', district_name]
        else:
            pivot_df = pd.DataFrame()
            charts_data = {}
            expected_headers = ['Subheadings']
    else:
        pivot_df = get_abstract_data(db)
        charts_data = get_all_districts_abstract_charts_data(db)
        expected_headers = ['Subheadings'] + REGULAR_DISTRICTS + ['Total']

    if pivot_df.empty:
        response = templates.TemplateResponse("schemes/s2053/subs/s20530242/district_wise_abstract.html", {
            "request": request, "resource_name": "जिल्हानिहाय गोषवारा",
            "headers": expected_headers, "data_rows": [],
            "total_row": None,
            "auth_level": auth_level, "auth_unit": auth_unit,
            "chart_data_json": json.dumps(charts_data)
        })
        response.headers.update(get_no_cache_headers())
        return response

    if auth_level in ('district', 'taluka'):
        total_row_dict = None
    else:
        rows_to_exclude = ['10- Contractual Services', '16- Publications']
        rows_to_exclude_existing = [r for r in rows_to_exclude if r in pivot_df.index]
        df_for_column_totals = pivot_df.drop(index=rows_to_exclude_existing, errors='ignore')
        column_totals = df_for_column_totals.sum(axis=0)
        column_totals.name = 'Total'

        total_row_dict = column_totals.astype(int).to_dict()
        total_row_dict['Subheadings'] = 'एकूण'

    pivot_df_display = pivot_df.reset_index()
    pivot_df_display['Subheadings'] = pivot_df_display['Subheadings'].map(UNIT_ACCOUNT_MAP_MR).fillna(pivot_df_display['Subheadings'])
    headers = list(pivot_df_display.columns)
    int_cols = [col for col in headers if col not in ['Subheadings', 'Total'] and col in pivot_df_display.columns]
    if 'Total' in pivot_df_display.columns: int_cols.append('Total')
    for col in int_cols: pivot_df_display[col] = pivot_df_display[col].astype(int)
    data_rows = pivot_df_display.to_dict(orient='records')

    response = templates.TemplateResponse("schemes/s2053/subs/s20530242/district_wise_abstract.html", {
        "request": request,
        "resource_name": "जिल्हानिहाय गोषवारा",
        "headers": headers,
        "data_rows": data_rows,
        "total_row": total_row_dict,
        "districts_mr": DISTRICTS_MR,
        "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level, "auth_unit": auth_unit,
        "chart_data_json": json.dumps(charts_data)
    })
    response.headers.update(get_no_cache_headers())
    return response
