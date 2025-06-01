from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func # Import func
from typing import List, Optional, Dict, Any # Import Dict, Any
import models
import schemas
from database import get_db
from config import DISTRICTS, PRIMARY_UNITS
import pandas as pd
import io
from urllib.parse import urlencode
from collections import defaultdict
import logging

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/unit-expenditure",
    tags=["UI - Unit Expenditure"],
    include_in_schema=False
)

logger = logging.getLogger(__name__)

# --- Marathi Mapping for Unit Accounts ---
# (Add more mappings if needed based on your actual data)
UNIT_ACCOUNT_MAP_MR = {
    "01- Salary": "01- वेतन",
    "03- Extra allowance": "03- अतिरिक्त भत्ता",
    "06- Telephone, Electricity, Water And Charges": "06- दूरध्वनी, वीज, पाणी शुल्क",
    "10- Contractual Services": "10- कंत्राटी सेवा",
    "11- Domestic Travel Expenses": "11- देशांतर्गत प्रवास खर्च",
    "13- Office Expenses": "13- कार्यालयीन खर्च",
    "14- Lease And Tax": "14- भाडेपट्टी व कर",
    "16- Publications": "16- प्रकाशने",
    "17- Computer Expenses": "17- संगणक खर्च",
    "20- Other Administrative Expenses": "20- इतर प्रशासकीय खर्च",
    "24- Fuel Costs": "24- इंधन खर्च",
    "26- Advertising And Publicity Expenses": "26- जाहिरात व प्रसिद्धी खर्च",
    "36- Small Construction": "36- लहान बांधकाम",
    "50- Other Expenses": "50- इतर खर्च",
    "51- Motor Vehicles": "51- मोटार वाहने"
}

# --- REVISED HELPER FUNCTION v2 (Adds Marathi Unit Translation) ---
def get_unit_expenditure_summary_data(db: Session) -> Dict[str, Any]:
    logger.info("--- (Helper REVISED v2) Fetching unit expenditure summary data ---")
    try:
        # Define columns to sum
        columns_to_sum = [
            models.UnitExpenditure.ActualAmountExpenditure20212022,
            models.UnitExpenditure.ActualAmountExpenditure20222023,
            models.UnitExpenditure.ActualAmountExpenditure20232024,
            models.UnitExpenditure.BudgetaryEstimates20242025,
            models.UnitExpenditure.ImprovedForecast20242025,
            models.UnitExpenditure.BudgetaryEstimates20252026EstimatingOfficer,
            models.UnitExpenditure.BudgetaryEstimates20252026ControllingOfficer,
            models.UnitExpenditure.BudgetaryEstimates20252026AdministrativeDepartment,
            models.UnitExpenditure.BudgetaryEstimates20252026FinanceDepartment
        ]
        # Create sum expressions with labels (internal keys)
        sum_expressions = [func.sum(col).label(col.name) for col in columns_to_sum]

        # Query and aggregate data, grouping by Primary Unit and ordering
        query = db.query(
            models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount.label("UnitAccount_EN"), # Get English key
            *sum_expressions
        ).group_by(
            models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount
        ).order_by(
            models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount # Sort by unit code
        ).all()

        logger.info(f"(Helper REVISED v2) Unit expenditure summary query returned {len(query)} rows.")

        # Process results into list of dicts and calculate totals
        summary_rows = []
        summary_totals = defaultdict(int)
        # Define internal keys based on model attributes
        internal_data_keys = [col.name for col in columns_to_sum]

        for i, row in enumerate(query, 1):
            # Start row dict with SrNo
            row_dict = {"SrNo": i}
            # Get the English Unit Account Name
            unit_account_en = getattr(row, "UnitAccount_EN", "")
            # Get Marathi translation, fallback to English
            row_dict["UnitAccount"] = UNIT_ACCOUNT_MAP_MR.get(unit_account_en, unit_account_en)

            # Process numeric columns
            for key in internal_data_keys:
                value = getattr(row, key, 0) # Get value using internal key
                int_value = int(value or 0)
                row_dict[key] = int_value
                summary_totals[key] += int_value # Add to totals

            summary_rows.append(row_dict)

        # Prepare totals row
        summary_totals["SrNo"] = "--"
        summary_totals["UnitAccount"] = "एकूण" # Marathi label for total row

        # Define the order of internal keys for the template/excel if needed, matching query + SrNo/UnitAccount
        # This helps ensure consistent column order in the template loop later
        ordered_internal_keys = ["SrNo", "UnitAccount"] + internal_data_keys

        return {
            "summary_rows": summary_rows,
            "summary_totals": dict(summary_totals), # Convert defaultdict back to dict
            "internal_keys_ordered": ordered_internal_keys # Pass ordered keys
        }

    except Exception as e:
        logger.error(f"(Helper REVISED v2) Error fetching/processing unit expenditure summary data: {e}", exc_info=True)
        return None
# --- END HELPER FUNCTION ---


# --- Updated Main GET Route (No structural changes needed) ---
@router.get("", response_class=HTMLResponse)
async def ui_list_unit_expenditure(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"), # Default view is 'edit'
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None)
):
    context = {
        "request": request,
        "resource_name": "Unit Expenditure", # Default title
        "districts": DISTRICTS,
        "primary_units": PRIMARY_UNITS, # For filtering list view
        "current_district": district,
        "current_primary_unit": primary_unit,
        "view_mode": view
    }

    if view == "summary":
        logger.info("Requesting Unit Expenditure Summary view")
        summary_data = get_unit_expenditure_summary_data(db) # Calls updated helper
        if summary_data is None:
             logger.error("Failed to get unit expenditure summary data from helper.")
             raise HTTPException(status_code=500, detail="Could not generate Unit Expenditure summary data.")

        context["resource_name"] = "Unit Expenditure Summary" # Update title
        context.update(summary_data) # Add summary rows, totals, and keys
        logger.info("Rendering Unit Expenditure Summary view")
        return templates.TemplateResponse("unit_expenditure_list.html", context)

    elif view == "edit":
        logger.info("Requesting Unit Expenditure List (edit) view")
        query = db.query(models.UnitExpenditure)
        if district: query = query.filter(models.UnitExpenditure.District == district)
        if primary_unit: query = query.filter(models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount == primary_unit)

        items = query.order_by(models.UnitExpenditure.id).all()

        query_params = {"district": district, "primary_unit": primary_unit}
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""
        context["items"] = items

        logger.info(f"Rendering Unit Expenditure List (edit) view with {len(items)} items.")
        return templates.TemplateResponse("unit_expenditure_list.html", context)

    else:
         logger.warning(f"Invalid view parameter received: {view}")
         raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


# --- Edit Form Routes (GET/POST - Remain the same) ---
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_unit_expenditure_form(request: Request, id: int, db: Session = Depends(get_db)):
    item = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not item: raise HTTPException(status_code=404, detail=f"Unit Expenditure with ID {id} not found")
    return templates.TemplateResponse("unit_expenditure_form.html", {"request": request, "districts": DISTRICTS, "primary_units": PRIMARY_UNITS, "item": item, "resource_name": "Unit Expenditure" })

@router.post("/{id}/edit", response_class=HTMLResponse)
async def ui_update_unit_expenditure(
    request: Request, id: int, db: Session = Depends(get_db),
    PrimaryAndSecondaryUnitsOfAccount: str = Form(...), District: str = Form(...),
    ActualAmountExpenditure20212022: Optional[int] = Form(None), ActualAmountExpenditure20222023: Optional[int] = Form(None),
    ActualAmountExpenditure20232024: Optional[int] = Form(None), BudgetaryEstimates20242025: Optional[int] = Form(None),
    ImprovedForecast20242025: Optional[int] = Form(None), BudgetaryEstimates20252026EstimatingOfficer: Optional[int] = Form(None),
    BudgetaryEstimates20252026ControllingOfficer: Optional[int] = Form(None),
    BudgetaryEstimates20252026AdministrativeDepartment: Optional[int] = Form(None), BudgetaryEstimates20252026FinanceDepartment: Optional[int] = Form(None)
):
    db_item = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not db_item: raise HTTPException(status_code=404, detail=f"Unit Expenditure with ID {id} not found")
    try:
        update_data = schemas.UnitExpenditureUpdate( # Use Pydantic for validation
            PrimaryAndSecondaryUnitsOfAccount=PrimaryAndSecondaryUnitsOfAccount, District=District,
            ActualAmountExpenditure20212022=ActualAmountExpenditure20212022, ActualAmountExpenditure20222023=ActualAmountExpenditure20222023,
            ActualAmountExpenditure20232024=ActualAmountExpenditure20232024, BudgetaryEstimates20242025=BudgetaryEstimates20242025,
            ImprovedForecast20242025=ImprovedForecast20242025, BudgetaryEstimates20252026EstimatingOfficer=BudgetaryEstimates20252026EstimatingOfficer,
            BudgetaryEstimates20252026ControllingOfficer=BudgetaryEstimates20252026ControllingOfficer,
            BudgetaryEstimates20252026AdministrativeDepartment=BudgetaryEstimates20252026AdministrativeDepartment, BudgetaryEstimates20252026FinanceDepartment=BudgetaryEstimates20252026FinanceDepartment )
        update_dict = update_data.model_dump(exclude_unset=True) # exclude_unset is important
        for key, value in update_dict.items():
             if value is not None: setattr(db_item, key, value) # Check value is not None before setting
        db.commit(); db.refresh(db_item)
        return RedirectResponse(url=router.url_path_for("ui_list_unit_expenditure") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback(); logger.error(f"Failed to update Unit Expenditure ID {id}: {e}", exc_info=True)
        return templates.TemplateResponse("unit_expenditure_form.html", { "request": request, "error": f"Failed to update record: {e}", "districts": DISTRICTS, "primary_units": PRIMARY_UNITS, "item": db_item, "resource_name": "Unit Expenditure" }, status_code=400)

# --- UPDATED Excel Download Route for Summary ---
@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_summary_excel(db: Session = Depends(get_db)):
    logger.info("--- Entered export_unit_expenditure_summary_excel ---")
    summary_data = get_unit_expenditure_summary_data(db)
    if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    try:
        logger.info("Preparing data for Unit Expenditure Summary Excel...")
        df_rows = pd.DataFrame(summary_data['summary_rows'])
        df_totals = pd.DataFrame([summary_data['summary_totals']])
        df = pd.concat([df_rows, df_totals], ignore_index=True)

        # Define Marathi headers in the correct order (matching helper's internal keys)
        marathi_headers = {
            "SrNo": "अ. क्र.",
            "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट", # Column with Marathi values
            "ActualAmountExpenditure20212022": "प्रत्यक्ष रक्कमा (खर्च) 2021-2022",
            "ActualAmountExpenditure20222023": "प्रत्यक्ष रक्कमा (खर्च) 2022-2023",
            "ActualAmountExpenditure20232024": "प्रत्यक्ष रक्कमा (खर्च) 2023-2024",
            "BudgetaryEstimates20242025": "अर्थसंकल्पीय अंदाज 2024-2025",
            "ImprovedForecast20242025": "सुधारीत अंदाज 2024-2025",
            "BudgetaryEstimates20252026EstimatingOfficer": "अर्थसंकल्पीय अंदाज 2025-2026 प्राकक्लन",
            "BudgetaryEstimates20252026ControllingOfficer": "अर्थसंकल्पीय अंदाज 2025-2026 नियंत्रक",
            "BudgetaryEstimates20252026AdministrativeDepartment": "अर्थसंकल्पीय अंदाज 2025-2026 प्रशासकीय",
            "BudgetaryEstimates20252026FinanceDepartment": "अर्थसंकल्पीय अंदाज 2025-2026 वित्त",
        }
        ordered_internal_keys = summary_data.get("internal_keys_ordered", list(marathi_headers.keys())) # Use ordered keys from helper

        # Add placeholder for explanation column before renaming
        # df['स्पष्टीकरणे'] = ''
        # ordered_internal_keys.append('स्पष्टीकरणे') # Add key if adding column

        # Select columns in order and rename
        df = df[[key for key in ordered_internal_keys if key in df.columns]] # Ensure key exists
        df.columns = [marathi_headers.get(col, col) for col in df.columns] # Rename based on map

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Unit Expenditure Summary', index=False)
        output.seek(0)
        logger.info("Unit Expenditure Summary Excel file created, preparing response...")
        headers = {'Content-Disposition': 'attachment; filename="unit_expenditure_summary_report.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.error(f"Failed to generate Unit Expenditure Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")

# --- Existing Excel Download Route for List View ---
@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_list_excel(
    db: Session = Depends(get_db), district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None)
):
    # (Keep existing logic)
    logger.info("--- Entered export_unit_expenditure_LIST_excel ---")
    query = db.query(models.UnitExpenditure)
    if district: query = query.filter(models.UnitExpenditure.District == district)
    if primary_unit: query = query.filter(models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount == primary_unit)
    items = query.order_by(models.UnitExpenditure.id).all()
    data_dict = [schemas.UnitExpenditureResponse.model_validate(item).model_dump() for item in items]
    df = pd.DataFrame(data_dict)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Unit Expenditure List', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="unit_expenditure_list.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
# --- End Excel ---