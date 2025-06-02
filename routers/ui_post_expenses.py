# routers/ui_post_expenses.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case, Integer, String, Float
from typing import List, Optional, Dict, Any
import models
import schemas
from database import get_db
from config import DISTRICTS, CATEGORIES, CLASSES_SHEET3
import pandas as pd
import io
from urllib.parse import urlencode
from collections import defaultdict
import logging
import json # For embedding chart data

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/post-expenses",
    tags=["UI - Post Expenses"],
    include_in_schema=False
)

logger = logging.getLogger(__name__)

# --- CORRECTED HELPER FUNCTION v4.1 (Fixed Indentation) ---
def get_post_expenses_summary_data(db: Session) -> Dict[str, Any]:
    logger.info("--- (Helper REVISED v4.1) Fetching post expenses summary data (Tables 1 & 3 only) ---")
    try:
        # --- Aggregation for Table 1 (Post Counts) ---
        post_counts_query = db.query(
            models.PostExpenses.Class,
            models.PostExpenses.Category,
            func.sum(models.PostExpenses.FilledPosts).label("TotalFilled"),
            func.sum(models.PostExpenses.VacantPosts).label("TotalVacant")
        ).group_by(
            models.PostExpenses.Class,
            models.PostExpenses.Category
        ).all()
        logger.info(f"(Helper REVISED v4.1) Post counts query returned {len(post_counts_query)} rows.")

        # --- Fetch and Process Data for Table 3 (Expense Summary - Unique District Sum) ---
        expense_data_query = db.query(
            models.PostExpenses.District,
            models.PostExpenses.MedicalExpenses,
            models.PostExpenses.FestivalAdvance,
            models.PostExpenses.SwagramMaharashtraDarshan,
            models.PostExpenses.SeventhPayCommissionDifferenceNPS,
            models.PostExpenses.NPS,
            models.PostExpenses.SeventhPayCommissionDifference,
            models.PostExpenses.Other
        ).all()
        logger.info(f"(Helper REVISED v4.1) Base expense data query returned {len(expense_data_query)} rows for processing.")

        # --- Process Data for Table 1 (Post Counts) ---
        table1_data = defaultdict(lambda: defaultdict(int))
        for row in post_counts_query: # Indent Level 1
            cls = row.Class          # Indent Level 2
            cat = row.Category       # Indent Level 2
            if cls not in ['1', '2', '3', '4']: continue # Indent Level 2
            # *** CORRECTED INDENTATION HERE ***
            table1_data[cls][f"{cat}_Filled"] = int(row.TotalFilled or 0) # Indent Level 2
            table1_data[cls][f"{cat}_Vacant"] = int(row.TotalVacant or 0) # Indent Level 2

        table1_rows = []
        table1_totals = defaultdict(int)
        for i, cls in enumerate(['1', '2', '3', '4'], 1): # Indent Level 1
            row_data = { # Indent Level 2
                "SrNo": i,
                "Class": cls,
                "Permanent_Filled": table1_data[cls].get("Permanent_Filled", 0),
                "Permanent_Vacant": table1_data[cls].get("Permanent_Vacant", 0),
                "Temporary_Filled": table1_data[cls].get("Temporary_Filled", 0),
                "Temporary_Vacant": table1_data[cls].get("Temporary_Vacant", 0),
            }
            row_data["Row_Total"] = sum(row_data[k] for k in ["Permanent_Filled", "Permanent_Vacant", "Temporary_Filled", "Temporary_Vacant"]) # Indent Level 2
            table1_rows.append(row_data) # Indent Level 2

            # Summing for footer totals
            for key in ["Permanent_Filled", "Permanent_Vacant", "Temporary_Filled", "Temporary_Vacant", "Row_Total"]: # Indent Level 2
                table1_totals[key] += row_data[key] # Indent Level 3

        table1_totals["SrNo"] = "--"  # Indent Level 1
        table1_totals["Class"] = "एकूण" # Indent Level 1

        # --- Process Data for Table 3 (Expense Summary - Sum unique per-district values) ---
        table3_totals_dict = defaultdict(float) # Indent Level 1
        processed_districts = set()             # Indent Level 1

        for row in expense_data_query: # Indent Level 1
            district = row.District # Indent Level 2
            if not district or district in processed_districts: continue # Indent Level 2

            processed_districts.add(district) # Indent Level 2
            # Sum unique values across all processed districts
            table3_totals_dict['Medical'] += float(row.MedicalExpenses or 0.0)              # Indent Level 2
            table3_totals_dict['Festival'] += float(row.FestivalAdvance or 0.0)          # Indent Level 2
            table3_totals_dict['Swagram'] += float(row.SwagramMaharashtraDarshan or 0.0) # Indent Level 2
            # Combine 7th pay/NPS columns into one value per district - Summing non-null values
            pay_diff_nps = float(row.SeventhPayCommissionDifferenceNPS or 0.0)          # Indent Level 2
            nps = float(row.NPS or 0.0)                                                 # Indent Level 2
            pay_diff = float(row.SeventhPayCommissionDifference or 0.0)                 # Indent Level 2
            table3_totals_dict['SeventhPayNPS'] += (pay_diff_nps + nps + pay_diff)       # Indent Level 2
            table3_totals_dict['Other'] += float(row.Other or 0.0)                      # Indent Level 2

        # Calculate final total expense
        table3_totals_dict['Expense_Total'] = sum(table3_totals_dict[k] for k in ['Medical', 'Festival', 'Swagram', 'SeventhPayNPS', 'Other']) # Indent Level 1

        # Prepare the single row for the template table
        table3_final_data_row = { # Indent Level 1
                "SrNo": 1,
                "Division": "कोकण विभाग", # Assuming single division Kokan
                "Medical": int(round(table3_totals_dict['Medical'])),
                "Festival": int(round(table3_totals_dict['Festival'])),
                "Swagram": int(round(table3_totals_dict['Swagram'])),
                "SeventhPayNPS": int(round(table3_totals_dict['SeventhPayNPS'])),
                "Other": int(round(table3_totals_dict['Other'])),
                "Expense_Total": int(round(table3_totals_dict['Expense_Total']))
        }
        logger.info(f"(Helper REVISED v4.1) Processed expense totals: {table3_final_data_row}") # Indent Level 1

        return { # Indent Level 1
            "table1_rows": table1_rows,
            "table1_totals": dict(table1_totals),
            "table3_data": [table3_final_data_row],
            "expense_totals_for_chart": dict(table3_totals_dict)
        }

    except Exception as e: # Indent Level 1
        logger.error(f"(Helper REVISED v4.1) Error fetching/processing post expenses summary data: {e}", exc_info=True) # Indent Level 2
        return None # Indent Level 2
# --- END HELPER FUNCTION ---


# --- Main GET Route (Chart data prep logic remains the same) ---
@router.get("", response_class=HTMLResponse)
async def ui_list_post_expenses(
    request: Request, db: Session = Depends(get_db), view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None), category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class")
):
    context = { "request": request, "resource_name": "Post Expenses", "districts": DISTRICTS,
                "categories": CATEGORIES, "classes": CLASSES_SHEET3, "current_district": district,
                "current_category": category, "current_class": cls, "view_mode": view }

    if view == "summary":
        logger.info("Requesting Post Expenses Summary view")
        summary_data = get_post_expenses_summary_data(db) # Calls corrected helper
        if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate Post Expenses summary data.")

        # --- Prepare Chart Data (Logic unchanged from previous response) ---
        chart_data = {}
        try:
            table1_rows = summary_data.get("table1_rows", [])
            table1_totals = summary_data.get("table1_totals", {})
            expense_totals = summary_data.get("expense_totals_for_chart", {})

            # 1. Doughnut Chart: Overall Posts (Filled vs Vacant)
            total_filled = table1_totals.get("Permanent_Filled", 0) + table1_totals.get("Temporary_Filled", 0)
            total_vacant = table1_totals.get("Permanent_Vacant", 0) + table1_totals.get("Temporary_Vacant", 0)
            if total_filled > 0 or total_vacant > 0:
                 chart_data['doughnut_posts_status'] = {'भरलेली': total_filled, 'रिक्त': total_vacant}

            # 2. Grouped Bar: Posts by Class (Filled vs Vacant)
            posts_by_class = {"labels": [], "भरलेली": [], "रिक्त": []}
            has_posts_data = False
            for row in table1_rows:
                cls_label = f"वर्ग-{row['Class']}"; filled_cls = row.get("Permanent_Filled", 0) + row.get("Temporary_Filled", 0)
                vacant_cls = row.get("Permanent_Vacant", 0) + row.get("Temporary_Vacant", 0)
                posts_by_class["labels"].append(cls_label); posts_by_class["भरलेली"].append(filled_cls); posts_by_class["रिक्त"].append(vacant_cls)
                if filled_cls > 0 or vacant_cls > 0: has_posts_data = True
            if has_posts_data:
                 chart_data['grouped_bar_posts_by_class'] = posts_by_class

            # 3. Pie Chart: Expense Breakdown
            expense_breakdown = {}
            if expense_totals.get('Medical', 0) > 0: expense_breakdown['वैद्यकीय'] = expense_totals['Medical']
            if expense_totals.get('Festival', 0) > 0: expense_breakdown['उत्सव'] = expense_totals['Festival']
            if expense_totals.get('Swagram', 0) > 0: expense_breakdown['स्वग्राम'] = expense_totals['Swagram']
            if expense_totals.get('SeventhPayNPS', 0) > 0: expense_breakdown['7वे वेतन/NPS'] = expense_totals['SeventhPayNPS']
            if expense_totals.get('Other', 0) > 0: expense_breakdown['इतर'] = expense_totals['Other']
            if expense_breakdown:
                 chart_data['pie_expense_breakdown'] = expense_breakdown

            logger.info(f"Prepared chart data for Post Expenses: {chart_data}")

        except Exception as e:
             logger.error(f"Error preparing chart data for Post Expenses: {e}", exc_info=True)
             chart_data = {}

        context["resource_name"] = "Post Expenses Summary"
        context.update(summary_data)
        context["chart_data"] = chart_data

        logger.info("Rendering Post Expenses Summary view")
        return templates.TemplateResponse("post_expenses_list.html", context)

    elif view == "edit":
        # (Edit view logic remains unchanged)
        logger.info("Requesting Post Expenses List (edit) view")
        query = db.query(models.PostExpenses)
        if district: query = query.filter(models.PostExpenses.District == district)
        if category: query = query.filter(models.PostExpenses.Category == category)
        if cls: query = query.filter(models.PostExpenses.Class == cls)
        items = query.order_by(models.PostExpenses.id).all()
        filtered_params = {k: v for k, v in {"district": district, "category": category, "class": cls}.items() if v is not None}
        context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""
        context["items"] = items
        context["chart_data"] = None
        logger.info(f"Rendering Post Expenses List (edit) view with {len(items)} items.")
        return templates.TemplateResponse("post_expenses_list.html", context)

    else: # Invalid view
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


# --- Edit Form GET Route - Unchanged ---
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_expense_form(request: Request, id: int, db: Session = Depends(get_db)):
    # (Keep original code)
    item = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not item: raise HTTPException(status_code=404, detail=f"Post Expense with ID {id} not found")
    return templates.TemplateResponse("post_expenses_form.html", {
        "request": request, "districts": DISTRICTS, "categories": CATEGORIES,
        "classes": CLASSES_SHEET3, "item": item, "resource_name": "Post Expenses"
    })


# --- Edit Form POST Route (Handling Optional Floats - Corrected) ---
@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_post_expense(
    request: Request, id: int, db: Session = Depends(get_db),
    # Required fields
    Class: str = Form(...), Category: str = Form(...), District: str = Form(...),
    # Optional Integer fields
    FilledPosts: Optional[int] = Form(None), VacantPosts: Optional[int] = Form(None),
    MedicalExpenses: Optional[int] = Form(None), FestivalAdvance: Optional[int] = Form(None),
    SwagramMaharashtraDarshan: Optional[int] = Form(None), Other: Optional[int] = Form(None),
    # Receive potentially empty float fields as strings
    SeventhPayCommissionDifferenceNPS: Optional[str] = Form(None),
    NPS: Optional[str] = Form(None),
    SeventhPayCommissionDifference: Optional[str] = Form(None),
):
    db_item = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not db_item: raise HTTPException(status_code=404, detail=f"Post Expense with ID {id} not found")

    # Helper function to safely convert string to float or None
    def safe_float(value: Optional[str]) -> Optional[float]:
        if value is None or value.strip() == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid number format: '{value}'")

    form_data = { # Collect non-float fields first
        "Class": Class, "Category": Category, "District": District, "FilledPosts": FilledPosts,
        "VacantPosts": VacantPosts, "MedicalExpenses": MedicalExpenses, "FestivalAdvance": FestivalAdvance,
        "SwagramMaharashtraDarshan": SwagramMaharashtraDarshan, "Other": Other
    }

    try:
        # Convert float strings safely
        form_data["SeventhPayCommissionDifferenceNPS"] = safe_float(SeventhPayCommissionDifferenceNPS)
        form_data["NPS"] = safe_float(NPS)
        form_data["SeventhPayCommissionDifference"] = safe_float(SeventhPayCommissionDifference)

        # Update the database item
        for key, value in form_data.items():
             if hasattr(db_item, key):
                setattr(db_item, key, value) # Allow setting None

        db.commit(); db.refresh(db_item)
        logger.info(f"Successfully updated Post Expense ID {id}")
        # Redirect back to EDIT view
        return RedirectResponse(url=router.url_path_for("ui_list_post_expenses") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)

    except ValueError as ve: # Catch specific conversion errors
        db.rollback()
        logger.error(f"Invalid float input during update for Post Expense ID {id}: {ve}")
        db_item_reloaded = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
        return templates.TemplateResponse("post_expenses_form.html", {
            "request": request, "error": f"Failed to update: {ve}",
            "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET3,
            "item": db_item_reloaded, "resource_name": "Post Expenses"
        }, status_code=400)

    except Exception as e: # Catch other potential errors
        db.rollback(); logger.error(f"Failed to update Post Expense ID {id}: {e}", exc_info=True)
        db_item_reloaded = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
        return templates.TemplateResponse("post_expenses_form.html", {
            "request": request, "error": f"Failed to update record: {e}",
            "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET3,
            "item": db_item_reloaded, "resource_name": "Post Expenses"
        }, status_code=500)


# --- Excel Download Route for Summary (Unchanged from previous fix) ---
@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_expenses_summary_excel(db: Session = Depends(get_db)):
    # (Keep the code from the previous correct response)
    logger.info("--- Entered export_post_expenses_summary_excel (Revised) ---")
    summary_data = get_post_expenses_summary_data(db)
    if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    try:
        logger.info("Preparing data for Post Expenses Summary Excel (Tables 1 & 3)...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df1_rows = pd.DataFrame(summary_data['table1_rows']); df1_totals = pd.DataFrame([summary_data['table1_totals']]); df1 = pd.concat([df1_rows, df1_totals], ignore_index=True)
            df1.columns = ["अ.क्र.", "वर्ग", "स्थायी-भरलेली", "स्थायी-रिक्त", "अस्थायी-भरलेली", "अस्थायी-रिक्त", "एकूण पदे"]
            df1.to_excel(writer, sheet_name='Post Counts by Class', index=False)
            df3 = pd.DataFrame(summary_data['table3_data'])
            df3 = df3[['SrNo', 'Division', 'Medical', 'Festival', 'Swagram', 'SeventhPayNPS', 'Other', 'Expense_Total']]
            df3.columns = ["अ.क्र.", "जिल्हा / विभाग", "वैद्यकिय खर्च", "उत्सव/सण अग्रिम", "स्वग्राम/महाराष्ट्र दर्शन", "7 व्या वेतन आयोग फरक+ NPS", "इतर", "एकूण खर्च"]
            df3.to_excel(writer, sheet_name='Expense Summary', index=False)
        output.seek(0)
        logger.info("Post Expenses Summary Excel file created, preparing response...")
        headers = {'Content-Disposition': 'attachment; filename="post_expenses_summary_report.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.error(f"Failed to generate Post Expenses Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")

# --- Excel Download Route for List View - Unchanged ---
# (Keep original code)
@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_expenses_list_excel(
    db: Session = Depends(get_db), district: Optional[str] = Query(None), category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class")
):
    logger.info("--- Entered export_post_expenses_LIST_excel ---")
    query = db.query(models.PostExpenses)
    if district: query = query.filter(models.PostExpenses.District == district)
    if category: query = query.filter(models.PostExpenses.Category == category)
    if cls: query = query.filter(models.PostExpenses.Class == cls)
    items = query.order_by(models.PostExpenses.id).all()
    data_dict_list = []
    if items:
        columns = [c.name for c in models.PostExpenses.__table__.columns]
        for item in items: data_dict_list.append({col: getattr(item, col, None) for col in columns})
    df = pd.DataFrame(data_dict_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Post Expenses List', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="post_expenses_list.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')