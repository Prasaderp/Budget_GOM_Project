from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional, Dict, Any, Tuple # Import Tuple
import pandas as pd
import models
from database import get_db
import io

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/category-wise-info",
    tags=["UI - Category Wise Info"],
    include_in_schema=False
)

# Corrected return type hint here -> Tuple[...]
def get_category_data(db: Session) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    class_mapping = {
        '1': 'Class-1', '2': 'Class-2', '3': 'Class-3', '4': 'Class-4'
    }
    class_order = ['Class-1', 'Class-2', 'Class-3', 'Class-4']

    aggregation_query = db.query(
        models.PostExpenses.Class, models.PostExpenses.Category,
        func.sum(models.PostExpenses.FilledPosts).label("TotalFilled"),
        func.sum(models.PostExpenses.VacantPosts).label("TotalVacant")
    ).group_by(
        models.PostExpenses.Class, models.PostExpenses.Category
    ).all()

    summary_data: Dict[str, Dict[str, int]] = {cls_name: {} for cls_name in class_order}
    totals: Dict[str, Any] = {
        "Approved_Perm": 0, "Approved_Temp": 0,
        "Filled_Perm": 0, "Filled_Temp": 0,
        "Vacant_Perm": 0, "Vacant_Temp": 0
    }

    for result in aggregation_query:
        class_key = class_mapping.get(result.Class)
        if not class_key: continue
        filled = int(result.TotalFilled or 0)
        vacant = int(result.TotalVacant or 0)
        approved = filled + vacant
        if result.Category == 'Permanent':
            summary_data[class_key]['Filled_Perm'] = filled
            summary_data[class_key]['Vacant_Perm'] = vacant
            summary_data[class_key]['Approved_Perm'] = approved
            totals['Filled_Perm'] += filled
            totals['Vacant_Perm'] += vacant
            totals['Approved_Perm'] += approved
        elif result.Category == 'Temporary':
            summary_data[class_key]['Filled_Temp'] = filled
            summary_data[class_key]['Vacant_Temp'] = vacant
            summary_data[class_key]['Approved_Temp'] = approved
            totals['Filled_Temp'] += filled
            totals['Vacant_Temp'] += vacant
            totals['Approved_Temp'] += approved

    table_rows = []
    for i, class_name in enumerate(class_order, 1):
        row_data = summary_data.get(class_name, {})
        table_rows.append({
            "Sr No.": i,
            "Cadre": class_name,
            "Approved - Permanent": row_data.get("Approved_Perm", 0),
            "Approved - Temporary": row_data.get("Approved_Temp", 0),
            "Filled - Permanent": row_data.get("Filled_Perm", 0),
            "Filled - Temporary": row_data.get("Filled_Temp", 0),
            "Vacant - Permanent": row_data.get("Vacant_Perm", 0),
            "Vacant - Temporary": row_data.get("Vacant_Temp", 0)
        })

    totals['Sr No.'] = "--"
    totals['Cadre'] = "Total"
    totals_renamed = {
        "Sr No.": totals['Sr No.'], "Cadre": totals['Cadre'],
        "Approved - Permanent": totals['Approved_Perm'], "Approved - Temporary": totals['Approved_Temp'],
        "Filled - Permanent": totals['Filled_Perm'], "Filled - Temporary": totals['Filled_Temp'],
        "Vacant - Permanent": totals['Vacant_Perm'], "Vacant - Temporary": totals['Vacant_Temp']
    }

    return table_rows, totals_renamed


@router.get("", response_class=HTMLResponse)
async def ui_category_wise_info(request: Request, db: Session = Depends(get_db)):
    table_rows, totals = get_category_data(db)
    return templates.TemplateResponse("category_wise_info.html", {
        "request": request,
        "resource_name": "Category-Wise Information",
        "table_rows": table_rows,
        "totals": totals
    })

@router.get("/export-excel")
async def export_category_info_excel(db: Session = Depends(get_db)):
    table_rows, totals_dict = get_category_data(db)

    if not table_rows:
         df = pd.DataFrame(columns=["Sr No.", "Cadre", "Approved - Permanent", "Approved - Temporary", "Filled - Permanent", "Filled - Temporary", "Vacant - Permanent", "Vacant - Temporary"])
    else:
        df = pd.DataFrame(table_rows)
        df = pd.concat([df, pd.DataFrame([totals_dict])], ignore_index=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Category Wise Info', index=False)
    output.seek(0)

    headers = {
        'Content-Disposition': 'attachment; filename="category_wise_info.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')