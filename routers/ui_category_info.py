# routers/ui_category_info.py
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import models
from database import get_db
import io
import json # For chart data
import logging
from collections import defaultdict # **** ADDED import ****

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/category-wise-info",
    tags=["UI - Category Wise Info"],
    include_in_schema=False
)

# Helper function (remains the same logic, but now defaultdict is defined)
def get_category_data(db: Session) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # Maps the numerical class from DB ('1', '2', '3', '4') to display labels
    class_mapping = {
        '1': 'वर्ग-1', '2': 'वर्ग-2', '3': 'वर्ग-3', '4': 'वर्ग-4'
    }
    # Defines the desired display order
    class_order = ['वर्ग-1', 'वर्ग-2', 'वर्ग-3', 'वर्ग-4']

    aggregation_query = db.query(
        models.PostExpenses.Class, models.PostExpenses.Category,
        func.sum(models.PostExpenses.FilledPosts).label("TotalFilled"),
        func.sum(models.PostExpenses.VacantPosts).label("TotalVacant")
    ).group_by(
        models.PostExpenses.Class, models.PostExpenses.Category
    ).all()

    # Structure to hold aggregated data per display class label
    summary_data: Dict[str, Dict[str, int]] = {cls_name: {} for cls_name in class_order}
    # Structure to hold overall totals - uses defaultdict now correctly
    totals: Dict[str, Any] = defaultdict(int) # Use defaultdict for easier summation

    for result in aggregation_query:
        # Map DB class ('1') to display class ('वर्ग-1')
        class_key = class_mapping.get(result.Class)
        if not class_key: continue # Skip if class is not in mapping

        filled = int(result.TotalFilled or 0)
        vacant = int(result.TotalVacant or 0)
        approved = filled + vacant # Calculate approved posts for this segment

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

    # Prepare rows for the HTML table
    table_rows = []
    for i, class_name in enumerate(class_order, 1):
        row_data = summary_data.get(class_name, {}) # Get data for this class, default to empty dict
        table_rows.append({
            "Sr No.": i,
            "Cadre": class_name, # Use Marathi class name
            "Approved - Permanent": row_data.get("Approved_Perm", 0),
            "Approved - Temporary": row_data.get("Approved_Temp", 0),
            "Filled - Permanent": row_data.get("Filled_Perm", 0),
            "Filled - Temporary": row_data.get("Filled_Temp", 0),
            "Vacant - Permanent": row_data.get("Vacant_Perm", 0),
            "Vacant - Temporary": row_data.get("Vacant_Temp", 0)
        })

    # Finalize totals row for the table footer
    totals['Sr No.'] = "--"
    totals['Cadre'] = "एकूण" # Marathi Total label
    # Rename keys in the totals dict for direct use in the template footer
    totals_renamed = {
        "Sr No.": totals['Sr No.'], "Cadre": totals['Cadre'],
        "Approved - Permanent": totals['Approved_Perm'], "Approved - Temporary": totals['Approved_Temp'],
        "Filled - Permanent": totals['Filled_Perm'], "Filled - Temporary": totals['Filled_Temp'],
        "Vacant - Permanent": totals['Vacant_Perm'], "Vacant - Temporary": totals['Vacant_Temp']
    }

    # Return both table rows and the renamed totals dict
    return table_rows, totals_renamed


# Main route updated for charts
@router.get("", response_class=HTMLResponse)
async def ui_category_wise_info(request: Request, db: Session = Depends(get_db)):
    table_rows, totals = get_category_data(db)

    # --- Prepare Chart Data ---
    chart_data = {}
    try:
        # 1. Stacked Bar Chart: Posts per Class
        if table_rows: # Check if data exists for table rows
            stacked_bar_posts = {
                "labels": [row.get("Cadre", "") for row in table_rows], # Class names ('वर्ग-1', etc.)
                "datasets": [
                    # Use Marathi labels for datasets
                    {"label": "भरलेली - स्थायी", "data": [row.get("Filled - Permanent", 0) for row in table_rows]},
                    {"label": "भरलेली - अस्थायी", "data": [row.get("Filled - Temporary", 0) for row in table_rows]},
                    {"label": "रिक्त - स्थायी", "data": [row.get("Vacant - Permanent", 0) for row in table_rows]},
                    {"label": "रिक्त - अस्थायी", "data": [row.get("Vacant - Temporary", 0) for row in table_rows]},
                ]
            }
             # Check if there is actually data to plot
            if any(sum(ds['data']) > 0 for ds in stacked_bar_posts['datasets']):
                chart_data['stacked_bar_posts_class'] = stacked_bar_posts

        # 2. Pie Chart: Overall Approved (Perm vs Temp)
        if totals: # Check if totals data exists
            pie_approved_cat = {
                # Use Marathi Labels as keys
                "स्थायी": totals.get("Approved - Permanent", 0),
                "अस्थायी": totals.get("Approved - Temporary", 0)
            }
            # Only add if there are posts
            if pie_approved_cat["स्थायी"] > 0 or pie_approved_cat["अस्थायी"] > 0:
                chart_data['pie_approved_category'] = pie_approved_cat

        logger.info(f"Prepared chart data for Category Wise Info: {chart_data}")

    except Exception as e:
        logger.error(f"Error preparing chart data for Category Wise Info: {e}", exc_info=True)
        chart_data = {}


    return templates.TemplateResponse("category_wise_info.html", {
        "request": request,
        "resource_name": "Category-Wise Information", # Or use Marathi: वर्गानुसार माहिती
        "table_rows": table_rows,
        "totals": totals,
        "chart_data": chart_data # Pass chart data
    })

# Export Excel Route (remains the same)
@router.get("/export-excel")
async def export_category_info_excel(db: Session = Depends(get_db)):
    table_rows, totals_dict = get_category_data(db)

    if not table_rows:
         df = pd.DataFrame(columns=["Sr No.", "Cadre", "Approved - Permanent", "Approved - Temporary", "Filled - Permanent", "Filled - Temporary", "Vacant - Permanent", "Vacant - Temporary"])
    else:
        df = pd.DataFrame(table_rows)
        # Append the totals row correctly
        df = pd.concat([df, pd.DataFrame([totals_dict])], ignore_index=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Category Wise Info', index=False)
    output.seek(0)

    headers = {
        'Content-Disposition': 'attachment; filename="category_wise_info.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')