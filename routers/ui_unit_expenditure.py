# routers/ui_unit_expenditure.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import models
import schemas
from database import get_db
# Import constants and the map from config
from config import DISTRICTS, PRIMARY_UNITS, UNIT_ACCOUNT_MAP_MR # Import map
import pandas as pd
import io
from urllib.parse import urlencode
from collections import defaultdict
import logging
import json

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/unit-expenditure",
    tags=["UI - Unit Expenditure"],
    include_in_schema=False
)

logger = logging.getLogger(__name__)

# --- Marathi Mapping is now imported from config ---

# --- Helper Function (Uses imported map) ---
def get_unit_expenditure_summary_data(db: Session) -> Dict[str, Any]:
    logger.info("--- (Helper REVISED v2.1) Fetching unit expenditure summary data ---")
    try:
        columns_to_sum = [ models.UnitExpenditure.ActualAmountExpenditure20212022, models.UnitExpenditure.ActualAmountExpenditure20222023, models.UnitExpenditure.ActualAmountExpenditure20232024, models.UnitExpenditure.BudgetaryEstimates20242025, models.UnitExpenditure.ImprovedForecast20242025, models.UnitExpenditure.BudgetaryEstimates20252026EstimatingOfficer, models.UnitExpenditure.BudgetaryEstimates20252026ControllingOfficer, models.UnitExpenditure.BudgetaryEstimates20252026AdministrativeDepartment, models.UnitExpenditure.BudgetaryEstimates20252026FinanceDepartment ]
        sum_expressions = [func.sum(col).label(col.name) for col in columns_to_sum]
        query = db.query( models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount.label("UnitAccount_EN"), *sum_expressions ).group_by( models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount ).order_by( models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount ).all()
        logger.info(f"(Helper REVISED v2.1) Unit expenditure summary query returned {len(query)} rows.")
        summary_rows = []; summary_totals = defaultdict(int)
        internal_data_keys = [col.name for col in columns_to_sum]
        for i, row in enumerate(query, 1):
            row_dict = {"SrNo": i}; unit_account_en = getattr(row, "UnitAccount_EN", "")
            row_dict["UnitAccount"] = UNIT_ACCOUNT_MAP_MR.get(unit_account_en, unit_account_en) # Uses imported map
            row_dict["UnitAccount_EN"] = unit_account_en
            for key in internal_data_keys: value = getattr(row, key, 0); int_value = int(value or 0); row_dict[key] = int_value; summary_totals[key] += int_value
            summary_rows.append(row_dict)
        summary_totals["SrNo"] = "--"; summary_totals["UnitAccount"] = "एकूण"
        ordered_internal_keys = ["SrNo", "UnitAccount"] + internal_data_keys
        return { "summary_rows": summary_rows, "summary_totals": dict(summary_totals), "internal_keys_ordered": ordered_internal_keys }
    except Exception as e:
        logger.error(f"(Helper REVISED v2.1) Error fetching/processing unit expenditure summary data: {e}", exc_info=True)
        return None
# --- END HELPER FUNCTION ---


# --- Main GET Route (Keep as is) ---
@router.get("", response_class=HTMLResponse)
async def ui_list_unit_expenditure( request: Request, db: Session = Depends(get_db), view: Optional[str] = Query("edit"), district: Optional[str] = Query(None), primary_unit: Optional[str] = Query(None) ):
    # (Keep code from previous response - including chart data prep)
    context = { "request": request, "resource_name": "Unit Expenditure", "districts": DISTRICTS, "primary_units": PRIMARY_UNITS, "current_district": district, "current_primary_unit": primary_unit, "view_mode": view }
    if view == "summary":
        logger.info("Requesting Unit Expenditure Summary view")
        summary_data = get_unit_expenditure_summary_data(db)
        if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate Unit Expenditure summary data.")
        chart_data = {}
        try:
            summary_totals = summary_data.get("summary_totals", {})
            # 1. Bar Chart: Budget vs Forecast 24-25
            budget_2425 = summary_totals.get("BudgetaryEstimates20242025", 0); forecast_2425 = summary_totals.get("ImprovedForecast20242025", 0)
            if budget_2425 > 0 or forecast_2425 > 0: chart_data["bar_budget_forecast_2425"] = { "labels": ["अर्थसंकल्पीय अंदाज 24-25", "सुधारित अंदाज 24-25"], "values": [budget_2425, forecast_2425] }
            # 2. Line Chart: Actual Expenditure Trend
            line_actual_trend = { "labels": ["2021-2022", "2022-2023", "2023-2024"], "values": [ summary_totals.get("ActualAmountExpenditure20212022", 0), summary_totals.get("ActualAmountExpenditure20222023", 0), summary_totals.get("ActualAmountExpenditure20232024", 0) ] }
            if any(v > 0 for v in line_actual_trend["values"]): chart_data["line_actual_trend"] = line_actual_trend
            # 3. Grouped Bar Chart: 25-26 Estimates Comparison
            bar_estimates_2526 = { "labels": ["प्राकक्लन अधिकारी", "नियंत्रक अधिकारी", "प्रशासकीय विभाग", "वित्त विभाग"], "values": [ summary_totals.get("BudgetaryEstimates20252026EstimatingOfficer", 0), summary_totals.get("BudgetaryEstimates20252026ControllingOfficer", 0), summary_totals.get("BudgetaryEstimates20252026AdministrativeDepartment", 0), summary_totals.get("BudgetaryEstimates20252026FinanceDepartment", 0) ] }
            if any(v > 0 for v in bar_estimates_2526["values"]): chart_data["bar_estimates_comparison_2526"] = bar_estimates_2526
            logger.info(f"Prepared chart data for Unit Expenditure: {chart_data}")
        except Exception as e: logger.error(f"Error preparing chart data for Unit Expenditure: {e}", exc_info=True); chart_data = {}
        context["resource_name"] = "Unit Expenditure Summary"; context.update(summary_data); context["chart_data"] = chart_data
        logger.info("Rendering Unit Expenditure Summary view with charts")
        return templates.TemplateResponse("unit_expenditure_list.html", context)
    elif view == "edit":
        logger.info("Requesting Unit Expenditure List (edit) view")
        query = db.query(models.UnitExpenditure);
        if district: query = query.filter(models.UnitExpenditure.District == district)
        if primary_unit: query = query.filter(models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount == primary_unit)
        items = query.order_by(models.UnitExpenditure.id).all(); query_params = {"district": district, "primary_unit": primary_unit}
        filtered_params = {k: v for k, v in query_params.items() if v is not None}; context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""
        context["items"] = items; context["chart_data"] = None
        logger.info(f"Rendering Unit Expenditure List (edit) view with {len(items)} items.")
        return templates.TemplateResponse("unit_expenditure_list.html", context)
    else: logger.warning(f"Invalid view parameter received: {view}"); raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


# --- Edit Form Routes (GET/POST - Unchanged) ---
# (Keep original code)
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_unit_expenditure_form(request: Request, id: int, db: Session = Depends(get_db)):
    item = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not item: raise HTTPException(status_code=404, detail=f"Unit Expenditure with ID {id} not found")
    return templates.TemplateResponse("unit_expenditure_form.html", {"request": request, "districts": DISTRICTS, "primary_units": PRIMARY_UNITS, "item": item, "resource_name": "Unit Expenditure" })

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_unit_expenditure( request: Request, id: int, db: Session = Depends(get_db), PrimaryAndSecondaryUnitsOfAccount: str = Form(...), District: str = Form(...), ActualAmountExpenditure20212022: Optional[int] = Form(None), ActualAmountExpenditure20222023: Optional[int] = Form(None), ActualAmountExpenditure20232024: Optional[int] = Form(None), BudgetaryEstimates20242025: Optional[int] = Form(None), ImprovedForecast20242025: Optional[int] = Form(None), BudgetaryEstimates20252026EstimatingOfficer: Optional[int] = Form(None), BudgetaryEstimates20252026ControllingOfficer: Optional[int] = Form(None), BudgetaryEstimates20252026AdministrativeDepartment: Optional[int] = Form(None), BudgetaryEstimates20252026FinanceDepartment: Optional[int] = Form(None) ):
    db_item = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not db_item: raise HTTPException(status_code=404, detail=f"Unit Expenditure with ID {id} not found")
    try:
        update_data = schemas.UnitExpenditureUpdate( PrimaryAndSecondaryUnitsOfAccount=PrimaryAndSecondaryUnitsOfAccount, District=District, ActualAmountExpenditure20212022=ActualAmountExpenditure20212022, ActualAmountExpenditure20222023=ActualAmountExpenditure20222023, ActualAmountExpenditure20232024=ActualAmountExpenditure20232024, BudgetaryEstimates20242025=BudgetaryEstimates20242025, ImprovedForecast20242025=ImprovedForecast20242025, BudgetaryEstimates20252026EstimatingOfficer=BudgetaryEstimates20252026EstimatingOfficer, BudgetaryEstimates20252026ControllingOfficer=BudgetaryEstimates20252026ControllingOfficer, BudgetaryEstimates20252026AdministrativeDepartment=BudgetaryEstimates20252026AdministrativeDepartment, BudgetaryEstimates20252026FinanceDepartment=BudgetaryEstimates20252026FinanceDepartment )
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
             if value is not None: setattr(db_item, key, value)
        db.commit(); db.refresh(db_item)
        return RedirectResponse(url=router.url_path_for("ui_list_unit_expenditure") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback(); logger.error(f"Failed to update Unit Expenditure ID {id}: {e}", exc_info=True)
        return templates.TemplateResponse("unit_expenditure_form.html", { "request": request, "error": f"Failed to update record: {e}", "districts": DISTRICTS, "primary_units": PRIMARY_UNITS, "item": db_item, "resource_name": "Unit Expenditure" }, status_code=400)

# --- Excel Download Route for Summary - CORRECTED FORMATTING ---
@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_summary_excel(db: Session = Depends(get_db)):
    logger.info("--- Entered export_unit_expenditure_summary_excel ---")
    summary_data = get_unit_expenditure_summary_data(db)
    if summary_data is None:
        raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    try:
        logger.info("Preparing data for Unit Expenditure Summary Excel...")
        df_rows = pd.DataFrame(summary_data['summary_rows'])
        # Ensure 'UnitAccount_EN' is dropped if it exists before processing totals
        if 'UnitAccount_EN' in df_rows.columns:
            df_rows = df_rows.drop(columns=['UnitAccount_EN'])

        df_totals = pd.DataFrame([summary_data['summary_totals']])
        # Ensure totals row index aligns if needed, or just concat
        df = pd.concat([df_rows, df_totals], ignore_index=True)

        # Define headers correctly, ensure keys exist in your model/helper output
        marathi_headers = {
            "SrNo": "अ. क्र.",
            "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट",
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
        ordered_internal_keys = summary_data.get("internal_keys_ordered", list(marathi_headers.keys()))

        # Select and order columns that actually exist in the DataFrame
        cols_to_export = [key for key in ordered_internal_keys if key in df.columns]
        df_export = df[cols_to_export].copy() # Create a copy to avoid SettingWithCopyWarning

        # Rename columns for export
        df_export.columns = [marathi_headers.get(col, col) for col in df_export.columns]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name='Unit Expenditure Summary', index=False)

        output.seek(0)
        logger.info("Unit Expenditure Summary Excel file created, preparing response...")
        headers = {'Content-Disposition': 'attachment; filename="unit_expenditure_summary_report.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        logger.error(f"Failed to generate Unit Expenditure Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")


# --- Excel Download Route for List View - Unchanged ---
@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_list_excel( db: Session = Depends(get_db), district: Optional[str] = Query(None), primary_unit: Optional[str] = Query(None) ):
    # (Keep original code)
    logger.info("--- Entered export_unit_expenditure_LIST_excel ---"); query = db.query(models.UnitExpenditure)
    if district: query = query.filter(models.UnitExpenditure.District == district)
    if primary_unit: query = query.filter(models.UnitExpenditure.PrimaryAndSecondaryUnitsOfAccount == primary_unit)
    items = query.order_by(models.UnitExpenditure.id).all(); data_dict_list = []
    if items:
        for item in items:
            try: validated_item = schemas.UnitExpenditureResponse.model_validate(item); data_dict_list.append(validated_item.model_dump())
            except Exception as e: logger.warning(f"Skipping item {getattr(item, 'id', 'N/A')} due to validation error: {e}")
    df = pd.DataFrame(data_dict_list); output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, sheet_name='Unit Expenditure List', index=False)
    output.seek(0); headers = {'Content-Disposition': 'attachment; filename="unit_expenditure_list.xlsx"'}; return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')