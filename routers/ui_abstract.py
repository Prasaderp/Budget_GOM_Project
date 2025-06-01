from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import pandas as pd
import models
from database import get_db
from config import DISTRICTS
import io

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/district-wise-abstract",
    tags=["UI - District Wise Abstract"],
    include_in_schema=False
)

def get_abstract_data(db: Session) -> pd.DataFrame:
     data_query = db.query(
        models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount,
        models.UnitExpenditure.District,
        models.UnitExpenditure.BudgetaryEstimates20252026EstimatingOfficer
    ).all()

     if not data_query:
         return pd.DataFrame(columns=['Subheadings'] + DISTRICTS + ['Total']).set_index('Subheadings')

     df = pd.DataFrame(data_query, columns=['Subheadings', 'District', 'Value'])
     pivot_df = df.pivot_table(
        index='Subheadings',
        columns='District',
        values='Value',
        fill_value=0
     )
     pivot_df = pivot_df.reindex(columns=DISTRICTS, fill_value=0)
     numeric_cols = pivot_df.columns
     for col in numeric_cols:
        pivot_df[col] = pd.to_numeric(pivot_df[col], errors='coerce').fillna(0).astype(int)

     pivot_df['Total'] = pivot_df.sum(axis=1)
     return pivot_df


@router.get("", response_class=HTMLResponse)
async def ui_district_wise_abstract(request: Request, db: Session = Depends(get_db)):
    pivot_df = get_abstract_data(db)

    if pivot_df.empty:
         return templates.TemplateResponse("district_wise_abstract.html", {
            "request": request,
            "resource_name": "District Wise Abstract",
            "headers": ['Subheadings'] + DISTRICTS + ['Total'],
            "data_rows": [],
            "total_row": None
        })

    rows_to_exclude = ['10- Contractual Services', '16- Publications']
    df_for_column_totals = pivot_df.drop(index=rows_to_exclude, errors='ignore')
    column_totals = df_for_column_totals.sum(axis=0)

    total_row_dict = column_totals.astype(int).to_dict()
    total_row_dict['Subheadings'] = 'Total'

    pivot_df_display = pivot_df.reset_index()
    headers = list(pivot_df_display.columns)
    data_rows = pivot_df_display.astype({col: int for col in headers if col != 'Subheadings'}).to_dict(orient='records')


    return templates.TemplateResponse("district_wise_abstract.html", {
        "request": request,
        "resource_name": "District Wise Abstract",
        "headers": headers,
        "data_rows": data_rows,
        "total_row": total_row_dict
    })

@router.get("/export-excel")
async def export_district_abstract_excel(db: Session = Depends(get_db)):
    pivot_df = get_abstract_data(db)

    rows_to_exclude = ['10- Contractual Services', '16- Publications']
    df_for_column_totals = pivot_df.drop(index=rows_to_exclude, errors='ignore')
    column_totals = df_for_column_totals.sum(axis=0).astype(int)
    column_totals.name = 'Total'

    pivot_df_int = pivot_df.astype(int)
    total_row_df = column_totals.to_frame().T

    pivot_df_with_total = pd.concat([pivot_df_int, total_row_df])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pivot_df_with_total.to_excel(writer, sheet_name='District Wise Abstract', index=True)
    output.seek(0)

    headers = {
        'Content-Disposition': 'attachment; filename="district_wise_abstract.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')