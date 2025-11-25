from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from src import models
from src.database import get_db
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, PRIMARY_UNITS, UNIT_ACCOUNT_MAP_MR, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka, check_edit_permission
from src.utils_fiscal_year import get_fiscal_year_from_request
from urllib.parse import urlencode
from collections import defaultdict
import logging
from src.utils_cache import ttl_cache
from src.excel_template_export import export_original_workbook



templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/unit-expenditure",
    tags=["UI - प्रपत्र अ"],
    include_in_schema=False
)

logger = logging.getLogger(__name__)

@router.get("/api/primary-units", response_class=JSONResponse)
async def api_get_primary_units(request: Request, district: Optional[str] = Query(None), db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    query = db.query(models.UnitExpenditure.unit_account).distinct().filter(models.UnitExpenditure.fiscal_year == fiscal_year)
    if district:
        query = query.filter(models.UnitExpenditure.district == district)
    units = [row[0] for row in query.order_by(models.UnitExpenditure.unit_account).all()]
    return JSONResponse({"units": units})

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(request: Request, district: str = Query(...), primary_unit: str = Query(...), db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    record = db.query(models.UnitExpenditure).filter(
        models.UnitExpenditure.fiscal_year == fiscal_year,
        models.UnitExpenditure.district == district,
        models.UnitExpenditure.unit_account == primary_unit
    ).first()
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True, "id": record.id,
        "expenditure_2021_22": record.expenditure_2021_22 or 0,
        "expenditure_2022_23": record.expenditure_2022_23 or 0,
        "expenditure_2023_24": record.expenditure_2023_24 or 0,
        "budget_2024_25": record.budget_2024_25 or 0,
        "forecast_2024_25": record.forecast_2024_25 or 0,
        "budget_2025_26_estimating_officer": record.budget_2025_26_estimating_officer or 0,
        "budget_2025_26_controlling_officer": record.budget_2025_26_controlling_officer or 0,
        "budget_2025_26_admin_dept": record.budget_2025_26_admin_dept or 0,
        "budget_2025_26_finance_dept": record.budget_2025_26_finance_dept or 0
    })

@router.post("/api/update-inline", response_class=JSONResponse)
async def api_update_inline(request: Request, db: Session = Depends(get_db), id: int = Form(...), Expenditure202122: int = Form(0), Expenditure202223: int = Form(0), Expenditure202324: int = Form(0), Budget202425: int = Form(0), Forecast202425: int = Form(0), Budget202526EstimatingOfficer: int = Form(0), Budget202526ControllingOfficer: int = Form(0), Budget202526AdminDept: int = Form(0), Budget202526FinanceDept: int = Form(0)):
    from src.utils_timing import check_data_filling_allowed
    from src.audit_service import AuditService
    
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if not check_edit_permission(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    record = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    if auth_level == 'district' and auth_unit:
        if auth_unit == DCO_STAFF_IDENTIFIER:
            if record.district != DCO_STAFF_IDENTIFIER:
                return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
        else:
            if record.district != auth_unit or record.district == DCO_STAFF_IDENTIFIER:
                return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    
    if auth_level == 'taluka' and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        if not district_name or record.district != district_name or record.district == DCO_STAFF_IDENTIFIER:
            return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    
    # Validate non-negative values and reasonable limits
    values_to_check = [Expenditure202122, Expenditure202223, Expenditure202324, Budget202425, Forecast202425, Budget202526EstimatingOfficer, Budget202526ControllingOfficer, Budget202526AdminDept, Budget202526FinanceDept]
    if any(v < 0 for v in values_to_check):
        return JSONResponse({"success": False, "message": "नकारात्मक मूल्ये स्वीकार्य नाहीत"}, status_code=400)
    if any(v > 999999999 for v in values_to_check):
        return JSONResponse({"success": False, "message": "मूल्य खूप मोठे आहे"}, status_code=400)
    
    old_values = {"expenditure_2021_22": record.expenditure_2021_22, "expenditure_2022_23": record.expenditure_2022_23, "expenditure_2023_24": record.expenditure_2023_24, "budget_2024_25": record.budget_2024_25, "forecast_2024_25": record.forecast_2024_25, "budget_2025_26_estimating_officer": record.budget_2025_26_estimating_officer, "budget_2025_26_controlling_officer": record.budget_2025_26_controlling_officer, "budget_2025_26_admin_dept": record.budget_2025_26_admin_dept, "budget_2025_26_finance_dept": record.budget_2025_26_finance_dept}
    
    record.expenditure_2021_22 = Expenditure202122
    record.expenditure_2022_23 = Expenditure202223
    record.expenditure_2023_24 = Expenditure202324
    record.budget_2024_25 = Budget202425
    record.forecast_2024_25 = Forecast202425
    record.budget_2025_26_estimating_officer = Budget202526EstimatingOfficer
    record.budget_2025_26_controlling_officer = Budget202526ControllingOfficer
    record.budget_2025_26_admin_dept = Budget202526AdminDept
    record.budget_2025_26_finance_dept = Budget202526FinanceDept
    
    new_values = {"expenditure_2021_22": Expenditure202122, "expenditure_2022_23": Expenditure202223, "expenditure_2023_24": Expenditure202324, "budget_2024_25": Budget202425, "forecast_2024_25": Forecast202425, "budget_2025_26_estimating_officer": Budget202526EstimatingOfficer, "budget_2025_26_controlling_officer": Budget202526ControllingOfficer, "budget_2025_26_admin_dept": Budget202526AdminDept, "budget_2025_26_finance_dept": Budget202526FinanceDept}
    
    try:
        AuditService.log_edit(db, request, "unit_expenditure", id, auth_user, old_values, new_values)
    except:
        pass
    
    db.commit()
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})

@ttl_cache(ttl_seconds=180, use_global=True)
def get_district_unit_expenditure_summary_data(db: Session, district: str, fiscal_year: str) -> Dict[str, Any]:
    logger.info(f"--- (Helper REVISED v2.1) Fetching district unit expenditure summary data for {district} ---")
    try:
        columns_to_sum = [ models.UnitExpenditure.expenditure_2021_22, models.UnitExpenditure.expenditure_2022_23, models.UnitExpenditure.expenditure_2023_24, models.UnitExpenditure.budget_2024_25, models.UnitExpenditure.forecast_2024_25, models.UnitExpenditure.budget_2025_26_estimating_officer, models.UnitExpenditure.budget_2025_26_controlling_officer, models.UnitExpenditure.budget_2025_26_admin_dept, models.UnitExpenditure.budget_2025_26_finance_dept ]
        sum_expressions = [func.sum(col).label(col.name) for col in columns_to_sum]
        query = db.query( models.UnitExpenditure.unit_account.label("UnitAccount_EN"), *sum_expressions ).filter(
            models.UnitExpenditure.district == district,
            models.UnitExpenditure.fiscal_year == fiscal_year
        ).group_by( models.UnitExpenditure.unit_account ).order_by( models.UnitExpenditure.unit_account ).all()
        logger.info(f"(Helper REVISED v2.1) District unit expenditure summary query returned {len(query)} rows.")
        summary_rows = []; summary_totals = defaultdict(int)
        internal_data_keys = [col.name for col in columns_to_sum]
        for i, row in enumerate(query, 1):
            row_dict = {"SrNo": i}; unit_account_en = getattr(row, "UnitAccount_EN", "")
            row_dict["UnitAccount"] = UNIT_ACCOUNT_MAP_MR.get(unit_account_en, unit_account_en)
            row_dict["UnitAccount_EN"] = unit_account_en
            for key in internal_data_keys: value = getattr(row, key, 0); int_value = int(value or 0); row_dict[key] = int_value; summary_totals[key] += int_value
            summary_rows.append(row_dict)
        summary_totals["SrNo"] = "--"; summary_totals["UnitAccount"] = "एकूण"
        ordered_internal_keys = ["SrNo", "UnitAccount"] + internal_data_keys
        return { "summary_rows": summary_rows, "summary_totals": dict(summary_totals), "internal_keys_ordered": ordered_internal_keys }
    except Exception as e:
        logger.error(f"(Helper REVISED v2.1) Error fetching/processing district unit expenditure summary data for {district}: {e}", exc_info=True)
        return None

@ttl_cache(ttl_seconds=180, use_global=True)
def get_district_unit_expenditure_charts_data(db: Session, district: str, fiscal_year: str) -> Dict[str, Any]:
    logger.info(f"Fetching district unit expenditure charts data for {district}")
    try:
        district_data = db.query(
            models.UnitExpenditure.district,
            func.sum(models.UnitExpenditure.expenditure_2021_22).label("exp_2021_22"),
            func.sum(models.UnitExpenditure.expenditure_2022_23).label("exp_2022_23"), 
            func.sum(models.UnitExpenditure.expenditure_2023_24).label("exp_2023_24"),
            func.sum(models.UnitExpenditure.budget_2024_25).label("budget_2024_25"),
            func.sum(models.UnitExpenditure.forecast_2024_25).label("forecast_2024_25"),
            func.sum(models.UnitExpenditure.budget_2025_26_estimating_officer).label("budget_est_off"),
            func.sum(models.UnitExpenditure.budget_2025_26_controlling_officer).label("budget_ctrl_off"),
            func.sum(models.UnitExpenditure.budget_2025_26_admin_dept).label("budget_admin"),
            func.sum(models.UnitExpenditure.budget_2025_26_finance_dept).label("budget_finance")
        ).filter(
            models.UnitExpenditure.district == district,
            models.UnitExpenditure.fiscal_year == fiscal_year
        ).group_by(models.UnitExpenditure.district).order_by(models.UnitExpenditure.district).all()
        
        districts = []
        exp_2021_22, exp_2022_23, exp_2023_24 = [], [], []
        budget_2024_25, forecast_2024_25 = [], []
        budget_est_off, budget_ctrl_off, budget_admin, budget_finance = [], [], [], []
        
        for row in district_data:
            districts.append(row.district or 'Unknown')
            exp_2021_22.append(int(row.exp_2021_22 or 0))
            exp_2022_23.append(int(row.exp_2022_23 or 0))
            exp_2023_24.append(int(row.exp_2023_24 or 0))
            budget_2024_25.append(int(row.budget_2024_25 or 0))
            forecast_2024_25.append(int(row.forecast_2024_25 or 0))
            budget_est_off.append(int(row.budget_est_off or 0))
            budget_ctrl_off.append(int(row.budget_ctrl_off or 0))
            budget_admin.append(int(row.budget_admin or 0))
            budget_finance.append(int(row.budget_finance or 0))
        
        chart_data = {
            "area_trends": {
                "labels": districts,
                "exp_2021_22": exp_2021_22,
                "exp_2022_23": exp_2022_23,
                "exp_2023_24": exp_2023_24
            },
            "doughnut_budget": {
                "labels": districts,
                "values": budget_2024_25
            },
            "multi_axis_comparison": {
                "labels": districts,
                "budget_2024_25": budget_2024_25,
                "forecast_2024_25": forecast_2024_25
            },
            "radar_estimates": {
                "labels": districts,
                "estimating_officer": budget_est_off,
                "controlling_officer": budget_ctrl_off,
                "admin_dept": budget_admin,
                "finance_dept": budget_finance
            }
        }
        
        logger.info(f"Generated district charts data for {len(districts)} districts")
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating district unit expenditure charts data for {district}: {e}", exc_info=True)
        return {}

@ttl_cache(ttl_seconds=180, use_global=True)
def get_unit_expenditure_summary_data(db: Session, fiscal_year: str = '2025-26') -> Dict[str, Any]:
    logger.info("--- (Helper REVISED v2.1) Fetching unit expenditure summary data ---")
    try:
        columns_to_sum = [ models.UnitExpenditure.expenditure_2021_22, models.UnitExpenditure.expenditure_2022_23, models.UnitExpenditure.expenditure_2023_24, models.UnitExpenditure.budget_2024_25, models.UnitExpenditure.forecast_2024_25, models.UnitExpenditure.budget_2025_26_estimating_officer, models.UnitExpenditure.budget_2025_26_controlling_officer, models.UnitExpenditure.budget_2025_26_admin_dept, models.UnitExpenditure.budget_2025_26_finance_dept ]
        sum_expressions = [func.sum(col).label(col.name) for col in columns_to_sum]
        query = db.query( models.UnitExpenditure.unit_account.label("UnitAccount_EN"), *sum_expressions ).filter(
            models.UnitExpenditure.fiscal_year == fiscal_year,
            models.UnitExpenditure.district != DCO_STAFF_IDENTIFIER
        ).group_by( models.UnitExpenditure.unit_account ).order_by( models.UnitExpenditure.unit_account ).all()
        logger.info(f"(Helper REVISED v2.1) Unit expenditure summary query returned {len(query)} rows.")
        summary_rows = []; summary_totals = defaultdict(int)
        internal_data_keys = [col.name for col in columns_to_sum]
        for i, row in enumerate(query, 1):
            row_dict = {"SrNo": i}; unit_account_en = getattr(row, "UnitAccount_EN", "")
            row_dict["UnitAccount"] = UNIT_ACCOUNT_MAP_MR.get(unit_account_en, unit_account_en)
            row_dict["UnitAccount_EN"] = unit_account_en
            for key in internal_data_keys: value = getattr(row, key, 0); int_value = int(value or 0); row_dict[key] = int_value; summary_totals[key] += int_value
            summary_rows.append(row_dict)
        summary_totals["SrNo"] = "--"; summary_totals["UnitAccount"] = "एकूण"
        ordered_internal_keys = ["SrNo", "UnitAccount"] + internal_data_keys
        return { "summary_rows": summary_rows, "summary_totals": dict(summary_totals), "internal_keys_ordered": ordered_internal_keys }
    except Exception as e:
        logger.error(f"(Helper REVISED v2.1) Error fetching/processing unit expenditure summary data: {e}", exc_info=True)
        return None

@ttl_cache(ttl_seconds=180, use_global=True)
def get_unit_expenditure_charts_data(db: Session, fiscal_year: str = '2025-26') -> Dict[str, Any]:
    logger.info("Fetching unit expenditure charts data")
    try:
        district_data = db.query(
            models.UnitExpenditure.district,
            func.sum(models.UnitExpenditure.expenditure_2021_22).label("exp_2021_22"),
            func.sum(models.UnitExpenditure.expenditure_2022_23).label("exp_2022_23"), 
            func.sum(models.UnitExpenditure.expenditure_2023_24).label("exp_2023_24"),
            func.sum(models.UnitExpenditure.budget_2024_25).label("budget_2024_25"),
            func.sum(models.UnitExpenditure.forecast_2024_25).label("forecast_2024_25"),
            func.sum(models.UnitExpenditure.budget_2025_26_estimating_officer).label("budget_est_off"),
            func.sum(models.UnitExpenditure.budget_2025_26_controlling_officer).label("budget_ctrl_off"),
            func.sum(models.UnitExpenditure.budget_2025_26_admin_dept).label("budget_admin"),
            func.sum(models.UnitExpenditure.budget_2025_26_finance_dept).label("budget_finance")
        ).filter(
            models.UnitExpenditure.fiscal_year == fiscal_year,
            models.UnitExpenditure.district != DCO_STAFF_IDENTIFIER
        ).group_by(models.UnitExpenditure.district).order_by(models.UnitExpenditure.district).all()
        
        districts = []
        exp_2021_22, exp_2022_23, exp_2023_24 = [], [], []
        budget_2024_25, forecast_2024_25 = [], []
        budget_est_off, budget_ctrl_off, budget_admin, budget_finance = [], [], [], []
        
        for row in district_data:
            districts.append(row.district or 'Unknown')
            exp_2021_22.append(int(row.exp_2021_22 or 0))
            exp_2022_23.append(int(row.exp_2022_23 or 0))
            exp_2023_24.append(int(row.exp_2023_24 or 0))
            budget_2024_25.append(int(row.budget_2024_25 or 0))
            forecast_2024_25.append(int(row.forecast_2024_25 or 0))
            budget_est_off.append(int(row.budget_est_off or 0))
            budget_ctrl_off.append(int(row.budget_ctrl_off or 0))
            budget_admin.append(int(row.budget_admin or 0))
            budget_finance.append(int(row.budget_finance or 0))
        
        chart_data = {
            "area_trends": {
                "labels": districts,
                "exp_2021_22": exp_2021_22,
                "exp_2022_23": exp_2022_23,
                "exp_2023_24": exp_2023_24
            },
            "doughnut_budget": {
                "labels": districts,
                "values": budget_2024_25
            },
            "multi_axis_comparison": {
                "labels": districts,
                "budget_2024_25": budget_2024_25,
                "forecast_2024_25": forecast_2024_25
            },
            "radar_estimates": {
                "labels": districts,
                "estimating_officer": budget_est_off,
                "controlling_officer": budget_ctrl_off,
                "admin_dept": budget_admin,
                "finance_dept": budget_finance
            }
        }
        
        logger.info(f"Generated charts data for {len(districts)} districts")
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating unit expenditure charts data: {e}", exc_info=True)
        return {}

@router.get("", response_class=HTMLResponse)
async def ui_list_unit_expenditure( request: Request, db: Session = Depends(get_db), view: Optional[str] = Query("edit"), district: Optional[str] = Query(None), primary_unit: Optional[str] = Query(None), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500) ):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    context = {
        "request": request, "resource_name": "प्रपत्र अ", "districts": districts_for_filter, "primary_units": PRIMARY_UNITS,
        "current_district": district, "current_primary_unit": primary_unit, "view_mode": view,
        "districts_mr": DISTRICTS_MR, "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level, "auth_unit": auth_unit
    }
    if view == "summary":
        fiscal_year = get_fiscal_year_from_request(request, db)
        if auth_level == 'district' and auth_unit:
            summary_data = get_district_unit_expenditure_summary_data(db, auth_unit, fiscal_year)
            charts_data = get_district_unit_expenditure_charts_data(db, auth_unit, fiscal_year)
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            if district_name:
                summary_data = get_district_unit_expenditure_summary_data(db, district_name, fiscal_year)
                charts_data = get_district_unit_expenditure_charts_data(db, district_name, fiscal_year)
            else:
                summary_data = None
                charts_data = {}
        else:
            summary_data = get_unit_expenditure_summary_data(db, fiscal_year)
            charts_data = get_unit_expenditure_charts_data(db, fiscal_year)
        
        if not summary_data:
            raise HTTPException(status_code=500, detail="Could not generate Unit Expenditure summary data.")
        context.update({"resource_name": "प्रपत्र अ गोषवारा", "chart_data_json": json.dumps(charts_data)})
        context.update(summary_data)
        response = templates.TemplateResponse("unit_expenditure_list.html", context)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    elif view == "edit":
        fiscal_year = get_fiscal_year_from_request(request, db)
        can_edit = check_edit_permission(auth_role, auth_level, auth_unit, db)
        query = build_district_filter(db.query(models.UnitExpenditure), auth_level, auth_unit, models.UnitExpenditure).filter(models.UnitExpenditure.fiscal_year == fiscal_year)
        
        if district:
            query = query.filter(models.UnitExpenditure.district == district)
        if primary_unit:
            query = query.filter(models.UnitExpenditure.unit_account == primary_unit)
        
        total_count = query.with_entities(func.count()).scalar()
        items = query.order_by(models.UnitExpenditure.id).offset((page - 1) * page_size).limit(page_size).all()
        
        filtered_params = {k: v for k, v in {"district": district, "primary_unit": primary_unit}.items() if v}
        context.update({
            "export_query_string_list": "?" + urlencode(filtered_params) if filtered_params else "",
            "items": items, "total_count": total_count, "page": page,
            "page_size": page_size, "can_edit": can_edit
        })
        response = templates.TemplateResponse("unit_expenditure_list.html", context)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    else: logger.warning(f"Invalid view parameter received: {view}"); raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_unit_expenditure_form(request: Request, id: int, db: Session = Depends(get_db)):
    from src.utils_timing import check_data_filling_allowed
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = request.cookies.get('auth_unit')
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role)
    if not is_allowed and auth_role == 'assistant':
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    item = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not item: raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
    return templates.TemplateResponse("unit_expenditure_form.html", {"request": request, "districts": districts_for_filter, "primary_units": PRIMARY_UNITS, "item": item, "resource_name": "प्रपत्र अ संपादन", "districts_mr": DISTRICTS_MR, "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR, "auth_level": auth_level })

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_unit_expenditure( request: Request, id: int, db: Session = Depends(get_db), PrimaryAndSecondaryUnitsOfAccount: str = Form(...), District: str = Form(...), ActualAmountExpenditure20212022: Optional[int] = Form(None), ActualAmountExpenditure20222023: Optional[int] = Form(None), ActualAmountExpenditure20232024: Optional[int] = Form(None), BudgetaryEstimates20242025: Optional[int] = Form(None), ImprovedForecast20242025: Optional[int] = Form(None), BudgetaryEstimates20252026EstimatingOfficer: Optional[int] = Form(None), BudgetaryEstimates20252026ControllingOfficer: Optional[int] = Form(None), BudgetaryEstimates20252026AdministrativeDepartment: Optional[int] = Form(None), BudgetaryEstimates20252026FinanceDepartment: Optional[int] = Form(None) ):
    from src.utils_timing import check_data_filling_allowed
    auth_role = request.cookies.get('auth_role') or ''
    auth_level = request.cookies.get('auth_level') or ''
    auth_unit = request.cookies.get('auth_unit') or ''
    if auth_role in ("officer1","officer2","dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            raise HTTPException(status_code=403, detail="Taluka not allowed")
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    db_item = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not db_item: raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
    try:
        update_dict = {
            "unit_account": PrimaryAndSecondaryUnitsOfAccount,
            "district": District,
            "expenditure_2021_22": ActualAmountExpenditure20212022,
            "expenditure_2022_23": ActualAmountExpenditure20222023,
            "expenditure_2023_24": ActualAmountExpenditure20232024,
            "budget_2024_25": BudgetaryEstimates20242025,
            "forecast_2024_25": ImprovedForecast20242025,
            "budget_2025_26_estimating_officer": BudgetaryEstimates20252026EstimatingOfficer
        }
        if auth_level != 'district':
            update_dict["budget_2025_26_controlling_officer"] = BudgetaryEstimates20252026ControllingOfficer
            update_dict["budget_2025_26_admin_dept"] = BudgetaryEstimates20252026AdministrativeDepartment
            update_dict["budget_2025_26_finance_dept"] = BudgetaryEstimates20252026FinanceDepartment
        for key, value in update_dict.items():
            if value is not None and hasattr(db_item, key):
                setattr(db_item, key, value)
        db.commit(); db.refresh(db_item)
        return RedirectResponse(url=router.url_path_for("ui_list_unit_expenditure") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback(); logger.error(f"Failed to update Unit Expenditure ID {id}: {e}", exc_info=True)
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        return templates.TemplateResponse("unit_expenditure_form.html", { "request": request, "error": f"रेकॉर्ड अपडेट करण्यात अयशस्वी: {e}", "districts": districts_for_filter, "primary_units": PRIMARY_UNITS, "item": db_item, "resource_name": "प्रपत्र अ संपादन", "districts_mr": DISTRICTS_MR, "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR, "auth_level": auth_level }, status_code=400)

@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_summary_excel(request: Request, db: Session = Depends(get_db)):
    import pandas as pd
    import io
    
    logger.info("--- Entered export_unit_expenditure_summary_excel ---")
    fiscal_year = get_fiscal_year_from_request(request, db)
    summary_data = get_unit_expenditure_summary_data(db, fiscal_year)
    if summary_data is None:
        raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    try:
        logger.info("Preparing data for Unit Expenditure Summary Excel...")
        df_rows = pd.DataFrame(summary_data['summary_rows'])
        if 'UnitAccount_EN' in df_rows.columns:
            df_rows = df_rows.drop(columns=['UnitAccount_EN'])

        df_totals = pd.DataFrame([summary_data['summary_totals']])
        df = pd.concat([df_rows, df_totals], ignore_index=True)

        marathi_headers = {
            "SrNo": "अ. क्र.",
            "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट",
            "expenditure_2021_22": "प्रत्यक्ष रक्कमा (खर्च) 2021-2022",
            "expenditure_2022_23": "प्रत्यक्ष रक्कमा (खर्च) 2022-2023",
            "expenditure_2023_24": "प्रत्यक्ष रक्कमा (खर्च) 2023-2024",
            "budget_2024_25": "अर्थसंकल्पीय अंदाज 2024-2025",
            "forecast_2024_25": "सुधारीत अंदाज 2024-2025",
            "budget_2025_26_estimating_officer": "अर्थसंकल्पीय अंदाज 2025-2026 प्राकक्लन",
            "budget_2025_26_controlling_officer": "अर्थसंकल्पीय अंदाज 2025-2026 नियंत्रक",
            "budget_2025_26_admin_dept": "अर्थसंकल्पीय अंदाज 2025-2026 प्रशासकीय",
            "budget_2025_26_finance_dept": "अर्थसंकल्पीय अंदाज 2025-2026 वित्त",
        }
        ordered_internal_keys = summary_data.get("internal_keys_ordered", list(marathi_headers.keys()))

        cols_to_export = [key for key in ordered_internal_keys if key in df.columns]
        df_export = df[cols_to_export].copy()

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


@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_list_excel( request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None), primary_unit: Optional[str] = Query(None) ):
    import pandas as pd
    import io
    from src import schemas
    
    logger.info("--- Entered export_unit_expenditure_LIST_excel ---")
    fiscal_year = get_fiscal_year_from_request(request, db)
    query = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.fiscal_year == fiscal_year)
    if district: query = query.filter(models.UnitExpenditure.district == district)
    if primary_unit: query = query.filter(models.UnitExpenditure.unit_account == primary_unit)
    items = query.order_by(models.UnitExpenditure.id).all(); data_dict_list = []
    if items:
        for item in items:
            try: validated_item = schemas.UnitExpenditureResponse.model_validate(item); data_dict_list.append(validated_item.model_dump())
            except Exception as e: logger.warning(f"Skipping item {getattr(item, 'id', 'N/A')} due to validation error: {e}")
    df = pd.DataFrame(data_dict_list); output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, sheet_name='Unit Expenditure List', index=False)
    output.seek(0); headers = {'Content-Disposition': 'attachment; filename="unit_expenditure_list.xlsx"'}; return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@router.get("/export-original", response_class=StreamingResponse)
async def export_unit_expenditure_original(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    return export_original_workbook(db, user_district=user_district)

@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_unit_expenditure_sheet_only(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    return export_original_workbook(db, only_sheet="unit_expenditure", user_district=user_district)