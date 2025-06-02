# routers/ui_abstract.py
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import models
from database import get_db
# Import constants and map from config
from config import DISTRICTS, UNIT_ACCOUNT_MAP_MR
import io
import json # For chart data
import logging

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/district-wise-abstract",
    tags=["UI - District Wise Abstract"],
    include_in_schema=False
)

# Helper function to get pivoted data (remains the same)
def get_abstract_data(db: Session) -> pd.DataFrame:
     data_query = db.query(
        models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount,
        models.UnitExpenditure.District,
        models.UnitExpenditure.BudgetaryEstimates20252026EstimatingOfficer # Using Estimating Officer
    ).all()

     if not data_query:
         return pd.DataFrame(columns=['Subheadings'] + DISTRICTS + ['Total']).set_index('Subheadings')

     df = pd.DataFrame(data_query, columns=['Subheadings', 'District', 'Value'])
     pivot_df = df.pivot_table( index='Subheadings', columns='District', values='Value', fill_value=0, aggfunc=sum )
     pivot_df = pivot_df.reindex(columns=DISTRICTS, fill_value=0)
     numeric_cols = pivot_df.columns
     for col in numeric_cols:
        pivot_df[col] = pd.to_numeric(pivot_df[col], errors='coerce').fillna(0).astype(int)
     pivot_df['Total'] = pivot_df.sum(axis=1)
     return pivot_df

# Main route, modified for 2 charts
@router.get("", response_class=HTMLResponse)
async def ui_district_wise_abstract(request: Request, db: Session = Depends(get_db)):
    pivot_df = get_abstract_data(db)

    if pivot_df.empty:
         return templates.TemplateResponse("district_wise_abstract.html", {
            "request": request, "resource_name": "District Wise Abstract",
            "headers": ['Subheadings'] + DISTRICTS + ['Total'], "data_rows": [],
            "total_row": None, "chart_data": None
        })

    # Calculate column totals
    rows_to_exclude = ['10- Contractual Services', '16- Publications']
    rows_to_exclude_existing = [r for r in rows_to_exclude if r in pivot_df.index]
    df_for_column_totals = pivot_df.drop(index=rows_to_exclude_existing, errors='ignore')
    column_totals = df_for_column_totals.sum(axis=0)
    column_totals.name = 'Total'

    # Prepare total row dictionary
    total_row_dict = column_totals.astype(int).to_dict()
    total_row_dict['Subheadings'] = 'एकूण'

    # Prepare data rows
    pivot_df_display = pivot_df.reset_index()
    pivot_df_display['Subheadings'] = pivot_df_display['Subheadings'].map(UNIT_ACCOUNT_MAP_MR).fillna(pivot_df_display['Subheadings'])
    headers = list(pivot_df_display.columns)
    int_cols = [col for col in headers if col not in ['Subheadings', 'Total'] and col in pivot_df_display.columns]
    if 'Total' in pivot_df_display.columns: int_cols.append('Total')
    for col in int_cols: pivot_df_display[col] = pivot_df_display[col].astype(int)
    data_rows = pivot_df_display.to_dict(orient='records')


    # --- Prepare Chart Data for 2 Charts ---
    chart_data = {}
    try:
        # 1. Horizontal Bar Chart: Total Estimate per District
        district_totals_for_chart = column_totals.drop('Total', errors='ignore')
        district_totals_for_chart = district_totals_for_chart.sort_values(ascending=True)
        if not district_totals_for_chart.empty and district_totals_for_chart.sum() > 0:
            chart_data["hbar_total_per_district"] = {
                "labels": district_totals_for_chart.index.tolist(),
                "values": [int(v) for v in district_totals_for_chart.values] # Python native int
            }

        # 2. Doughnut Chart: Top Unit Account Contribution to Grand Total
        grand_total = column_totals.get('Total', 0)
        unit_totals = df_for_column_totals['Total']
        if grand_total > 0 and not unit_totals.empty:
            top_n = 7
            unit_totals_sorted = unit_totals.sort_values(ascending=False)
            other_sum = 0
            if len(unit_totals_sorted) > top_n:
                top_items = unit_totals_sorted.head(top_n); other_sum = unit_totals_sorted.iloc[top_n:].sum()
            else: top_items = unit_totals_sorted
            doughnut_data_units_marathi = {
                UNIT_ACCOUNT_MAP_MR.get(k, k): int(v) # Python native int
                for k, v in top_items.items() if v > 0
            }
            if other_sum > 0: doughnut_data_units_marathi["इतर"] = int(other_sum)
            if doughnut_data_units_marathi: chart_data["doughnut_top_units_contribution"] = doughnut_data_units_marathi

        # --- Removed Radar/Grouped Bar data preparation ---

    except Exception as e:
        logger.error(f"Error preparing chart data for District Abstract: {e}", exc_info=True)
        chart_data = {}

    return templates.TemplateResponse("district_wise_abstract.html", {
        "request": request,
        "resource_name": "District Wise Abstract",
        "headers": headers,
        "data_rows": data_rows,
        "total_row": total_row_dict,
        "chart_data": chart_data # Pass chart data object for 2 charts
    })

# --- Export Excel Route (Unchanged) ---
@router.get("/export-excel")
async def export_district_abstract_excel(db: Session = Depends(get_db)):
    # (Keep code from previous response)
    pivot_df = get_abstract_data(db); rows_to_exclude = ['10- Contractual Services', '16- Publications']
    rows_to_exclude_existing = [r for r in rows_to_exclude if r in pivot_df.index]
    df_for_column_totals = pivot_df.drop(index=rows_to_exclude_existing, errors='ignore')
    column_totals = df_for_column_totals.sum(axis=0).astype(int); column_totals.name = 'एकूण'
    pivot_df_int = pivot_df.astype(int); total_row_df = pd.DataFrame(column_totals).T; total_row_df.index = ['एकूण']
    pivot_df_int.index = pivot_df_int.index.map(UNIT_ACCOUNT_MAP_MR).fillna(pivot_df_int.index)
    pivot_df_with_total = pd.concat([pivot_df_int, total_row_df]); output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: pivot_df_with_total.to_excel(writer, sheet_name='District Wise Abstract', index=True)
    output.seek(0); headers = {'Content-Disposition': 'attachment; filename="district_wise_abstract.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')