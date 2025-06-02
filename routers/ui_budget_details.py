# routers/ui_budget_details.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import models
import schemas
from database import get_db
from config import DISTRICTS, CATEGORIES, CLASSES_SHEET1_2, DESIGNATIONS
import pandas as pd
import io
from urllib.parse import urlencode
import json # For embedding chart data

# Import the helper function from the summary router (Ensure it exists!)
try:
    from .ui_budget_summary import get_budget_summary_data
except ImportError as e:
    print(f"ERROR: Could not import get_budget_summary_data from .ui_budget_summary: {e}")
    # Define a dummy function or raise error if import fails
    def get_budget_summary_data(db: Session) -> Dict[str, Any]:
        print("WARNING: Using dummy get_budget_summary_data function.")
        return {
            "permanent_rows": [], "temporary_rows": [],
            "permanent_totals_render": {}, "temporary_totals_render": {},
            "final_summary_rows": [],
            "internal_col_keys_for_template": []
        }

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/budget-post-details",
    tags=["UI - Budget Post Details"],
    include_in_schema=False
)

# --- Route for List View (handles both Edit/Display and Summary views) ---
@router.get("", response_class=HTMLResponse)
async def ui_list_budget_details(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"), # Default view is 'edit'
    # Filter parameters
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    designation_search: Optional[str] = Query(None)
):
    """
    Displays either the filtered list of Budget Post Details (with Edit links)
    or the Budget Summary Report (with JS Charts) based on the 'view' query parameter.
    """
    context = {"request": request}
    print(f"LOG: Requesting view='{view}'")

    base_context = {
        "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2,
        "current_district": district, "current_category": category, "current_class": cls,
        "current_designation_search": designation_search,
    }
    context.update(base_context)

    if view == "summary":
        # --- Logic for Summary View (with JS Chart Data) ---
        print("LOG: Fetching summary data for tables and charts...")
        summary_data = get_budget_summary_data(db) # Call helper
        if summary_data is None:
            print("ERROR: Failed to get summary data from helper.")
            raise HTTPException(status_code=500, detail="Could not generate summary data.")
        print("LOG: Summary data fetched.")

        # --- Prepare Data for Chart.js ---
        chart_data = {} # Initialize as empty dict
        try:
            perm_total_dict = summary_data.get("permanent_totals_render", {})
            temp_total_dict = summary_data.get("temporary_totals_render", {})
            final_rows = summary_data.get("final_summary_rows", [])

            # 1. Pie Chart Data: Total Amount (Perm vs Temp)
            # Keys are already Marathi: स्थायी, अस्थायी
            pie_chart_amount_input = {
                "स्थायी": perm_total_dict.get('Total', 0),
                "अस्थायी": temp_total_dict.get('Total', 0)
            }
            if pie_chart_amount_input["स्थायी"] > 0 or pie_chart_amount_input["अस्थायी"] > 0:
                 chart_data["pie_amount"] = pie_chart_amount_input

            # Data extraction intermediate storage
            class_map_summary = {'वर्ग-1 व 2': 'Class-1 & 2', 'वर्ग-3': 'Class-3', 'वर्ग-4': 'Class-4'}
            temp_class_totals_amount_perm = {}
            temp_class_totals_amount_temp = {}
            temp_class_totals_posts_perm = {}
            temp_class_totals_posts_temp = {}

            if final_rows: # Check if final_rows has data
                for row in final_rows:
                    category_label = row.get("CategoryLabel", "") # स्थायी / अस्थायी
                    class_label = row.get("ClassLabel", "") # वर्ग-1 व 2 etc.
                    if class_label in class_map_summary: # Process only class rows
                        total_amount = row.get('Total', 0)
                        total_posts = row.get('Approved Posts 2025-26', 0)
                        if category_label == 'स्थायी':
                            temp_class_totals_amount_perm[class_label] = total_amount
                            temp_class_totals_posts_perm[class_label] = total_posts
                        elif category_label == 'अस्थायी':
                            temp_class_totals_amount_temp[class_label] = total_amount
                            temp_class_totals_posts_temp[class_label] = total_posts

            # 2. Bar Chart Data: Total Amount by Class (Perm vs Temp)
            bar_chart_amount_input = {"labels": [], "स्थायी": [], "अस्थायी": []} # Marathi keys
            has_amount_data = False
            for label in ['वर्ग-1 व 2', 'वर्ग-3', 'वर्ग-4']: # Marathi/Devanagari labels
                perm_amount = temp_class_totals_amount_perm.get(label, 0)
                temp_amount = temp_class_totals_amount_temp.get(label, 0)
                bar_chart_amount_input["labels"].append(label)
                bar_chart_amount_input["स्थायी"].append(perm_amount)
                bar_chart_amount_input["अस्थायी"].append(temp_amount)
                if perm_amount > 0 or temp_amount > 0: has_amount_data = True
            if has_amount_data:
                chart_data["bar_amount_by_class"] = bar_chart_amount_input

            # 3. Stacked Bar Data: Approved Posts 2025-26 by Class (Perm vs Temp)
            stacked_bar_posts_input = {"labels": [], "स्थायी": [], "अस्थायी": []} # Marathi keys
            has_posts_data = False
            for label in ['वर्ग-1 व 2', 'वर्ग-3', 'वर्ग-4']: # Marathi/Devanagari labels
                perm_posts = temp_class_totals_posts_perm.get(label, 0)
                temp_posts = temp_class_totals_posts_temp.get(label, 0)
                stacked_bar_posts_input["labels"].append(label)
                stacked_bar_posts_input["स्थायी"].append(perm_posts)
                stacked_bar_posts_input["अस्थायी"].append(temp_posts)
                if perm_posts > 0 or temp_posts > 0: has_posts_data = True
            if has_posts_data:
                chart_data["stacked_bar_posts"] = stacked_bar_posts_input


            # 4. Bar Chart Data: Overall Pay Components
            pay_components_input = {"labels": [], "values": []}
            other_allowances_total = 0
            allowance_keys = [
                'Local Supplementary Allowance', 'Vehicle Allowance', 'Washing Allowance',
                'Cash Allowance', 'Footwear Allowance / Others'
            ]
            total_pay_overall = perm_total_dict.get('Total Pay', 0) + temp_total_dict.get('Total Pay', 0)
            da_overall = perm_total_dict.get('Dearness Allowance 64%', 0) + temp_total_dict.get('Dearness Allowance 64%', 0)
            hra_overall = perm_total_dict.get('House Rent Allowance', 0) + temp_total_dict.get('House Rent Allowance', 0)
            for key in allowance_keys:
                 other_allowances_total += perm_total_dict.get(key, 0) + temp_total_dict.get(key, 0)

            # --- Use Marathi labels for components ---
            temp_labels_marathi = []
            temp_values = []
            if total_pay_overall > 0:
                temp_labels_marathi.append('एकूण वेतन') # Marathi
                temp_values.append(total_pay_overall)
            if da_overall > 0:
                temp_labels_marathi.append('महा. भत्ता 64%') # Marathi
                temp_values.append(da_overall)
            if hra_overall > 0:
                temp_labels_marathi.append('घर भाडे भत्ता') # Marathi (same as Hindi)
                temp_values.append(hra_overall)
            if other_allowances_total > 0:
                temp_labels_marathi.append('इतर भत्ते') # Marathi
                temp_values.append(other_allowances_total)

            if temp_labels_marathi: # Only add if there's data
                 pay_components_input["labels"] = temp_labels_marathi
                 pay_components_input["values"] = temp_values
                 chart_data["bar_pay_components"] = pay_components_input


            print(f"LOG: Prepared chart data (including new charts, Marathi labels): {chart_data}")

        except Exception as e:
            print(f"ERROR: Could not prepare chart data from summary: {e}")
            chart_data = {} # Ensure it's an empty dict on error

        context["resource_name"] = "Budget Post Details Summary"
        context["view_mode"] = "summary"
        context.update(summary_data)
        context["chart_data"] = chart_data # Pass Python dict directly

        print("LOG: Rendering summary view with chart data object...")
        return templates.TemplateResponse("budget_post_details_list.html", context)

    elif view == "edit":
        # (Edit view logic remains unchanged)
        # ... (rest of edit view code) ...
        print("LOG: Fetching filtered details data for edit view...")
        query = db.query(models.BudgetPostDetails)
        if district: query = query.filter(models.BudgetPostDetails.District == district)
        if category: query = query.filter(models.BudgetPostDetails.Category == category)
        if cls: query = query.filter(models.BudgetPostDetails.Class == cls)
        if designation_search: query = query.filter(models.BudgetPostDetails.Designation.ilike(f"%{designation_search}%"))
        try:
            details = query.order_by(models.BudgetPostDetails.id).all()
            print(f"LOG: Found {len(details)} details for edit view.")
        except Exception as e:
             print(f"ERROR: Database error fetching details: {e}")
             raise HTTPException(status_code=500, detail=f"Database error fetching details: {e}")
        query_params = {"district": district, "category": category, "class": cls, "designation_search": designation_search}
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        export_query_string = "?" + urlencode(filtered_params) if filtered_params else ""
        context["resource_name"] = "Budget Post Details"
        context["view_mode"] = "edit"
        context["details"] = details
        context["export_query_string"] = export_query_string
        context["chart_data"] = None
        print("LOG: Rendering edit view (no plots)...")
        return templates.TemplateResponse("budget_post_details_list.html", context)

    else:
        print(f"ERROR: Invalid view parameter received: {view}")
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")

# --- Edit Form Route (GET) - Unchanged ---
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_budget_detail_form(request: Request, id: int, db: Session = Depends(get_db)):
    # (Keep original code)
    detail = db.query(models.BudgetPostDetails).filter(models.BudgetPostDetails.id == id).first()
    if not detail: raise HTTPException(status_code=404, detail=f"Budget Post Detail with ID {id} not found")
    return templates.TemplateResponse("budget_post_details_form.html", { "request": request, "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2, "designations": DESIGNATIONS, "detail": detail, "resource_name": f"Edit Budget Post Detail (ID: {id})", "is_edit": True })

# --- Edit Form Submission Route (POST) - Redirect to Edit View ---
@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_budget_detail( request: Request, id: int, db: Session = Depends(get_db), District: str = Form(...), Category: str = Form(...), Class: str = Form(...), Designation: str = Form(...), SanctionedPosts202425: Optional[int] = Form(None), SanctionedPosts202526: Optional[int] = Form(None), SpecialPay: Optional[int] = Form(None), BasicPay: Optional[int] = Form(None), GradePay: Optional[int] = Form(None), DearnessAllowance64: Optional[int] = Form(None), LocalSupplemetoryAllowance: Optional[int] = Form(None), LocalHRA: Optional[int] = Form(None), VehicleAllowance: Optional[int] = Form(None), WashingAllowance: Optional[int] = Form(None), CashAllowance: Optional[int] = Form(None), FootWareAllowanceOther: Optional[int] = Form(None), Other: Optional[int] = Form(None) ):
    # (Keep original code with redirect to edit)
    db_detail = db.query(models.BudgetPostDetails).filter(models.BudgetPostDetails.id == id).first()
    if not db_detail: raise HTTPException(status_code=404, detail=f"Budget Post Detail with ID {id} not found")
    form_data = locals()
    try:
        update_dict = { "District": District, "Category": Category, "Class": Class, "Designation": Designation, "SanctionedPosts202425": SanctionedPosts202425, "SanctionedPosts202526": SanctionedPosts202526, "SpecialPay": SpecialPay, "BasicPay": BasicPay, "GradePay": GradePay, "DearnessAllowance64": DearnessAllowance64, "LocalSupplemetoryAllowance": LocalSupplemetoryAllowance, "LocalHRA": LocalHRA, "VehicleAllowance": VehicleAllowance, "WashingAllowance": WashingAllowance, "CashAllowance": CashAllowance, "FootWareAllowanceOther": FootWareAllowanceOther, }
        for key, value in update_dict.items():
             if hasattr(db_detail, key):
                  if value is not None: setattr(db_detail, key, value)
             elif key not in ['request', 'id', 'db', 'form_data', 'update_dict', 'db_detail', 'key', 'value']: print(f"Warning: Attribute '{key}' not found in BudgetPostDetails model during update.")
        db.commit()
        print(f"LOG: Updated BudgetPostDetail ID {id}")
        return RedirectResponse(url=router.url_path_for("ui_list_budget_details") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback(); print(f"ERROR: Error updating record {id}: {e}")
        detail_for_form = db.query(models.BudgetPostDetails).filter(models.BudgetPostDetails.id == id).first()
        return templates.TemplateResponse("budget_post_details_form.html", { "request": request, "error": f"Failed to update record: {e}", "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2, "designations": DESIGNATIONS, "detail": detail_for_form, "resource_name": f"Edit Budget Post Detail (ID: {id})", "is_edit": True }, status_code=400)


# --- Export Excel Route - Unchanged ---
@router.get("/export-excel", response_class=StreamingResponse)
async def export_budget_details_excel( db: Session = Depends(get_db), district: Optional[str] = Query(None), category: Optional[str] = Query(None), cls: Optional[str] = Query(None, alias="class"), designation_search: Optional[str] = Query(None) ):
    # (Keep original code)
    print("LOG: Exporting filtered details to Excel...")
    query = db.query(models.BudgetPostDetails)
    if district: query = query.filter(models.BudgetPostDetails.District == district)
    if category: query = query.filter(models.BudgetPostDetails.Category == category)
    if cls: query = query.filter(models.BudgetPostDetails.Class == cls)
    if designation_search: query = query.filter(models.BudgetPostDetails.Designation.ilike(f"%{designation_search}%"))
    try:
        details = query.order_by(models.BudgetPostDetails.id).all()
        data_dict_list = []
        if details: columns = [c.name for c in models.BudgetPostDetails.__table__.columns];
        for item in details: data_dict_list.append({col: getattr(item, col, None) for col in columns})
        df = pd.DataFrame(data_dict_list); output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, sheet_name='Budget Post Details', index=False)
        output.seek(0); headers = {'Content-Disposition': 'attachment; filename="budget_post_details.xlsx"'}
        print("LOG: Sending Excel file for filtered details.")
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        print(f"ERROR: Error during filtered Excel export: {e}")
        raise HTTPException(status_code=500, detail=f"Could not generate Excel export: {e}")