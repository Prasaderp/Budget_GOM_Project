from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
# Need RedirectResponse again for edit success
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import models
import schemas # Kept as Edit route uses it
from database import get_db
from config import DISTRICTS, CATEGORIES, CLASSES_SHEET1_2, DESIGNATIONS # Add DESIGNATIONS back
import pandas as pd
import io
from urllib.parse import urlencode

# Import the helper function from the summary router (Ensure it exists!)
try:
    # Assuming routers are in the same directory or PYTHONPATH allows relative imports
    from .ui_budget_summary import get_budget_summary_data
except ImportError as e:
    print(f"ERROR: Could not import get_budget_summary_data from .ui_budget_summary: {e}")
    # Define a dummy function or raise error if import fails
    def get_budget_summary_data(db: Session) -> Dict[str, Any]:
        print("WARNING: Using dummy get_budget_summary_data function.")
        return {
            "permanent_rows": [], "temporary_rows": [],
            "permanent_totals_render": {}, "temporary_totals_render": {},
            "final_summary_rows": []
        }

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/budget-post-details",
    tags=["UI - Budget Post Details"], # Reverted Tag
    include_in_schema=False
)

# --- Route for List View (handles both Edit/Display and Summary views) ---
@router.get("", response_class=HTMLResponse)
async def ui_list_budget_details(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"), # Default view is 'edit' (display list)
    # Filter parameters from your fresh code
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    designation_search: Optional[str] = Query(None)
):
    """
    Displays either the filtered list of Budget Post Details (with Edit links)
    or the Budget Summary Report based on the 'view' query parameter.
    """
    context = {"request": request}
    print(f"LOG: Requesting view='{view}'") # Keep for debugging

    # Base context needed for filter dropdowns in 'edit' view
    base_context = {
        "districts": DISTRICTS,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "current_district": district,
        "current_category": category,
        "current_class": cls,
        "current_designation_search": designation_search,
    }
    context.update(base_context)

    if view == "summary":
        # --- Logic for Summary View ---
        print("LOG: Fetching summary data...")
        summary_data = get_budget_summary_data(db) # Call helper
        if summary_data is None:
            print("ERROR: Failed to get summary data from helper.")
            raise HTTPException(status_code=500, detail="Could not generate summary data.")
        print("LOG: Summary data fetched.")

        context["resource_name"] = "Budget Post Details Summary"
        context["view_mode"] = "summary"
        context.update(summary_data) # Add summary data keys
        # Ensure specific keys are present for clarity
        context["permanent_rows"]= summary_data.get("permanent_rows", [])
        context["temporary_rows"]= summary_data.get("temporary_rows", [])
        context["permanent_totals"]= summary_data.get("permanent_totals_render", {})
        context["temporary_totals"]= summary_data.get("temporary_totals_render", {})
        context["final_summary_rows"]= summary_data.get("final_summary_rows", [])

        print("LOG: Rendering summary view...")
        return templates.TemplateResponse("budget_post_details_list.html", context)

    elif view == "edit":
        # --- Logic for Filtered List View (with Edit links) ---
        # Use filtering and query logic from your fresh code
        print("LOG: Fetching filtered details data...")
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

        # Calculate export_query_string for the download button in this view
        query_params = {"district": district, "category": category, "class": cls, "designation_search": designation_search}
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        export_query_string = "?" + urlencode(filtered_params) if filtered_params else ""

        context["resource_name"] = "Budget Post Details"
        context["view_mode"] = "edit"
        context["details"] = details # Pass filtered items
        context["export_query_string"] = export_query_string # Pass for download button

        print("LOG: Rendering edit view...")
        return templates.TemplateResponse("budget_post_details_list.html", context)

    else:
        print(f"ERROR: Invalid view parameter received: {view}")
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


# --- Edit Form Route (GET) - From your fresh code ---
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_budget_detail_form(request: Request, id: int, db: Session = Depends(get_db)):
    detail = db.query(models.BudgetPostDetails).filter(models.BudgetPostDetails.id == id).first()
    if not detail:
        raise HTTPException(status_code=404, detail=f"Budget Post Detail with ID {id} not found")
    # Ensure the form template exists: "budget_post_details_form.html"
    return templates.TemplateResponse("budget_post_details_form.html", {
        "request": request,
        "districts": DISTRICTS,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "designations": DESIGNATIONS, # Needed if editable
        "detail": detail,
        "resource_name": f"Edit Budget Post Detail (ID: {id})", # Dynamic title
        "is_edit": True
    })

# --- Edit Form Submission Route (POST) - From your fresh code ---
# Using fields from your original POST route in Prompt #28
@router.post("/{id}/edit", response_class=RedirectResponse) # Redirect on success
async def ui_update_budget_detail(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    District: str = Form(...),
    Category: str = Form(...),
    Class: str = Form(...),
    Designation: str = Form(...),
    SanctionedPosts202425: Optional[int] = Form(None),
    SanctionedPosts202526: Optional[int] = Form(None),
    # ExistingPay: Optional[int] = Form(None), # Field from your POST code
    # Match these fields to your actual BudgetPostDetails model AND form template
    SpecialPay: Optional[int] = Form(None), # In model
    BasicPay: Optional[int] = Form(None),
    GradePay: Optional[int] = Form(None),
    DearnessAllowance64: Optional[int] = Form(None),
    LocalSupplemetoryAllowance: Optional[int] = Form(None), # In model
    LocalHRA: Optional[int] = Form(None),
    VehicleAllowance: Optional[int] = Form(None),
    WashingAllowance: Optional[int] = Form(None),
    CashAllowance: Optional[int] = Form(None),
    # UniformAllowance: Optional[int] = Form(None), # Field from your POST code
    FootWareAllowanceOther: Optional[int] = Form(None), # In model
    Other: Optional[int] = Form(None) # Field from your POST code
):
    db_detail = db.query(models.BudgetPostDetails).filter(models.BudgetPostDetails.id == id).first()
    if not db_detail:
        raise HTTPException(status_code=404, detail=f"Budget Post Detail with ID {id} not found")

    form_data = locals() # Capture submitted form data

    try:
        # Use Pydantic schema for validation (ensure BudgetPostDetailsUpdate exists and matches)
        # Or update manually like below:
        update_dict = {
            "District": District, "Category": Category, "Class": Class, "Designation": Designation,
            "SanctionedPosts202425": SanctionedPosts202425, "SanctionedPosts202526": SanctionedPosts202526,
            # "ExistingPay": ExistingPay, # Uncomment if in your model
            "SpecialPay": SpecialPay, # Ensure in model
            "BasicPay": BasicPay,
            "GradePay": GradePay,
            "DearnessAllowance64": DearnessAllowance64,
            "LocalSupplemetoryAllowance": LocalSupplemetoryAllowance, # Ensure in model
            "LocalHRA": LocalHRA,
            "VehicleAllowance": VehicleAllowance,
            "WashingAllowance": WashingAllowance,
            "CashAllowance": CashAllowance,
            # "UniformAllowance": UniformAllowance, # Uncomment if in your model
            "FootWareAllowanceOther": FootWareAllowanceOther, # Ensure in model
            "Other": Other # Ensure 'Other' is in your model if you submit it
        }

        for key, value in update_dict.items():
             if hasattr(db_detail, key):
                  if value is not None: # Only update if form sent a value
                      setattr(db_detail, key, value)
             elif key not in ['request', 'id', 'db', 'form_data', 'update_dict', 'db_detail', 'update_data', 'key', 'value']:
                  # Avoid warning for internal variables
                  print(f"Warning: Attribute '{key}' not found in BudgetPostDetails model during update.")

        db.commit()
        print(f"LOG: Updated BudgetPostDetail ID {id}")
        # Redirect back to the main list (edit view by default)
        return RedirectResponse(url=router.url_path_for("ui_list_budget_details") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        db.rollback()
        print(f"ERROR: Error updating record {id}: {e}")
        # Re-render the edit form with an error message
        detail_for_form = db.query(models.BudgetPostDetails).filter(models.BudgetPostDetails.id == id).first()
        return templates.TemplateResponse("budget_post_details_form.html", {
            "request": request, "error": f"Failed to update record: {e}",
            "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2,
            "designations": DESIGNATIONS,
            "detail": detail_for_form, # Pass original detail back
            "resource_name": f"Edit Budget Post Detail (ID: {id})", "is_edit": True
        }, status_code=400)


# --- Route to export the FILTERED details list to Excel - From your fresh code ---
@router.get("/export-excel", response_class=StreamingResponse)
async def export_budget_details_excel(
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    designation_search: Optional[str] = Query(None)
):
    print("LOG: Exporting filtered details to Excel...")
    query = db.query(models.BudgetPostDetails)
    if district: query = query.filter(models.BudgetPostDetails.District == district)
    if category: query = query.filter(models.BudgetPostDetails.Category == category)
    if cls: query = query.filter(models.BudgetPostDetails.Class == cls)
    if designation_search: query = query.filter(models.BudgetPostDetails.Designation.ilike(f"%{designation_search}%"))

    try:
        details = query.order_by(models.BudgetPostDetails.id).all()
        print(f"LOG: Found {len(details)} details for Excel export.")

        data_dict_list = []
        if details:
             columns = [c.name for c in models.BudgetPostDetails.__table__.columns]
             for item in details:
                  data_dict_list.append({col: getattr(item, col, None) for col in columns})

        df = pd.DataFrame(data_dict_list)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Budget Post Details', index=False)
        output.seek(0)

        headers = {'Content-Disposition': 'attachment; filename="budget_post_details.xlsx"'} # Original filename
        print("LOG: Sending Excel file for filtered details.")
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        print(f"ERROR: Error during filtered Excel export: {e}")
        raise HTTPException(status_code=500, detail=f"Could not generate Excel export: {e}")

# --- NO Create or Delete routes ---