"""UI routes for unit expenditure (Form A) - sub-scheme 20530387"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import logging
import json
import pandas as pd
import io

from src.database import get_db
from src.core.templates import templates
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.utils_scheme import get_scheme_from_cookies
from src.utils_cache import memory_cache
from src.utils_timing import check_data_filling_allowed
from src.audit_service import AuditService
from .excel_export import export_original_workbook_async
from .models import UnitExpenditure
from .config import SCHEME_CONFIG, PRIMARY_UNITS, UNIT_ACCOUNT_MAP_MR, SCHEME_DISTRICTS, SCHEME_DISTRICTS_MR
from .helpers import (
    check_edit_permission_for_scheme, invalidate_scheme_cache, log_audit_async,
    get_request_info, get_no_cache_headers, validate_numeric_inputs, validate_access_control
)
from src.utils_auth import get_auth_unit

router = APIRouter(prefix="/ui/s20530387/unit-expenditure", tags=["UI - प्रपत्र अ"], include_in_schema=False)
logger = logging.getLogger(__name__)

_COLUMNS_TO_SUM = [
    UnitExpenditure.expenditure_2021_22,
    UnitExpenditure.expenditure_2022_23,
    UnitExpenditure.expenditure_2023_24,
    UnitExpenditure.budget_2024_25,
    UnitExpenditure.forecast_2024_25,
    UnitExpenditure.budget_2025_26_estimating_officer,
    UnitExpenditure.budget_2025_26_controlling_officer,
    UnitExpenditure.budget_2025_26_admin_dept,
    UnitExpenditure.budget_2025_26_finance_dept
]
_INTERNAL_DATA_KEYS = [col.name for col in _COLUMNS_TO_SUM]
_ORDERED_KEYS = ["SrNo", "UnitAccount"] + _INTERNAL_DATA_KEYS
_CACHE_TTL = 300

def _make_cache_key(prefix: str, *args) -> str:
    return f"{prefix}|{'|'.join(str(a) for a in args)}"

def _get_summary_and_charts(db: Session, fiscal_year: str, district: Optional[str] = None, exclude_dco: bool = True) -> Dict[str, Any]:
    cache_key = _make_cache_key("unit_exp_combined", district or "all", fiscal_year)
    cached = memory_cache.get(cache_key)
    if cached:
        return cached

    base_filter = [UnitExpenditure.fiscal_year == fiscal_year]
    if district:
        base_filter.append(UnitExpenditure.district == district)
    elif exclude_dco:
        pass # No exclusion needed for DCO Staff only scheme

    sum_exprs = [func.sum(col).label(col.name) for col in _COLUMNS_TO_SUM]
    
    summary_query = db.query(
        UnitExpenditure.unit_account.label("unit_account"), *sum_exprs
    ).filter(*base_filter).group_by(UnitExpenditure.unit_account).order_by(UnitExpenditure.unit_account).all()

    summary_rows = []
    totals = {k: 0 for k in _INTERNAL_DATA_KEYS}
    for i, row in enumerate(summary_query, 1):
        ua = row.unit_account or ""
        rd = {"SrNo": i, "UnitAccount": UNIT_ACCOUNT_MAP_MR.get(ua, ua), "UnitAccount_EN": ua}
        for k in _INTERNAL_DATA_KEYS:
            v = int(getattr(row, k, 0) or 0)
            rd[k] = v
            totals[k] += v
        summary_rows.append(rd)
    totals["SrNo"] = "--"
    totals["UnitAccount"] = "एकूण"

    charts_query = db.query(
        UnitExpenditure.district,
        func.sum(UnitExpenditure.expenditure_2021_22).label("e21"),
        func.sum(UnitExpenditure.expenditure_2022_23).label("e22"),
        func.sum(UnitExpenditure.expenditure_2023_24).label("e23"),
        func.sum(UnitExpenditure.budget_2024_25).label("b24"),
        func.sum(UnitExpenditure.forecast_2024_25).label("f24"),
        func.sum(UnitExpenditure.budget_2025_26_estimating_officer).label("est"),
        func.sum(UnitExpenditure.budget_2025_26_controlling_officer).label("ctrl"),
        func.sum(UnitExpenditure.budget_2025_26_admin_dept).label("adm"),
        func.sum(UnitExpenditure.budget_2025_26_finance_dept).label("fin")
    ).filter(*base_filter).group_by(UnitExpenditure.district).order_by(UnitExpenditure.district).all()

    labels, e21, e22, e23, b24, f24, est, ctrl, adm, fin = [], [], [], [], [], [], [], [], [], []
    for r in charts_query:
        labels.append(r.district or 'Unknown')
        e21.append(int(r.e21 or 0))
        e22.append(int(r.e22 or 0))
        e23.append(int(r.e23 or 0))
        b24.append(int(r.b24 or 0))
        f24.append(int(r.f24 or 0))
        est.append(int(r.est or 0))
        ctrl.append(int(r.ctrl or 0))
        adm.append(int(r.adm or 0))
        fin.append(int(r.fin or 0))

    result = {
        "summary_rows": summary_rows,
        "summary_totals": totals,
        "internal_keys_ordered": _ORDERED_KEYS,
        "charts": {
            "area_trends": {"labels": labels, "exp_2021_22": e21, "exp_2022_23": e22, "exp_2023_24": e23},
            "doughnut_budget": {"labels": labels, "values": b24},
            "multi_axis_comparison": {"labels": labels, "budget_2024_25": b24, "forecast_2024_25": f24},
            "radar_estimates": {"labels": labels, "estimating_officer": est, "controlling_officer": ctrl, "admin_dept": adm, "finance_dept": fin}
        }
    }
    memory_cache.set(cache_key, result, _CACHE_TTL)
    return result

@router.get("/api/primary-units", response_class=JSONResponse)
async def api_get_primary_units(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    cache_key = _make_cache_key("primary_units", district or "all", fiscal_year)
    cached = memory_cache.get(cache_key)
    if cached:
        return JSONResponse(cached)
    
    q = db.query(UnitExpenditure.unit_account).distinct().filter(
        UnitExpenditure.fiscal_year == fiscal_year,
        UnitExpenditure.sub_scheme_code == sub_scheme
    )
    if district:
        q = q.filter(UnitExpenditure.district == district)
    units = [r[0] for r in q.order_by(UnitExpenditure.unit_account).limit(500).all()]
    result = {"units": units}
    memory_cache.set(cache_key, result, _CACHE_TTL)
    return JSONResponse(result)

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(
    request: Request,
    district: str = Query(...),
    primary_unit: str = Query(...),
    db: Session = Depends(get_db)
):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(UnitExpenditure).filter(
        UnitExpenditure.fiscal_year == fiscal_year,
        UnitExpenditure.sub_scheme_code == sub_scheme,
        UnitExpenditure.district == district,
        UnitExpenditure.unit_account == primary_unit
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
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    Expenditure202122: int = Form(0),
    Expenditure202223: int = Form(0),
    Expenditure202324: int = Form(0),
    Budget202425: int = Form(0),
    Forecast202425: int = Form(0),
    Budget202526EstimatingOfficer: int = Form(0),
    Budget202526ControllingOfficer: int = Form(0),
    Budget202526AdminDept: int = Form(0),
    Budget202526FinanceDept: int = Form(0)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    auth_user = request.cookies.get('auth_user', '')
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(UnitExpenditure).filter(
        UnitExpenditure.id == id,
        UnitExpenditure.sub_scheme_code == sub_scheme
    ).first()
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    allowed, error_msg = validate_access_control(record.district, auth_level, auth_unit, db)
    if not allowed:
        return JSONResponse({"success": False, "message": error_msg}, status_code=403)
    
    vals = [
        Expenditure202122, Expenditure202223, Expenditure202324, Budget202425, Forecast202425,
        Budget202526EstimatingOfficer, Budget202526ControllingOfficer, Budget202526AdminDept, Budget202526FinanceDept
    ]
    is_valid, error_msg = validate_numeric_inputs(*vals)
    if not is_valid:
        return JSONResponse({"success": False, "message": error_msg}, status_code=400)
    
    old_vals = {k: getattr(record, k) for k in _INTERNAL_DATA_KEYS}
    
    record.expenditure_2021_22 = Expenditure202122
    record.expenditure_2022_23 = Expenditure202223
    record.expenditure_2023_24 = Expenditure202324
    record.budget_2024_25 = Budget202425
    record.forecast_2024_25 = Forecast202425
    record.budget_2025_26_estimating_officer = Budget202526EstimatingOfficer
    record.budget_2025_26_controlling_officer = Budget202526ControllingOfficer
    record.budget_2025_26_admin_dept = Budget202526AdminDept
    record.budget_2025_26_finance_dept = Budget202526FinanceDept
    
    db.commit()
    
    invalidate_scheme_cache(record.district, patterns=["unit_exp_summary", "unit_exp_charts"])
    try:
        from src.routers.ui_taluka_selection import invalidate_district_status_cache
        scheme_code, _ = get_scheme_from_cookies(request)
        invalidate_district_status_cache(scheme_code, record.fiscal_year)
    except Exception:
        pass
    
    new_vals = {k: getattr(record, k) for k in _INTERNAL_DATA_KEYS}
    req_info = get_request_info(request)
    log_audit_async("unit_expenditure", id, auth_user, old_vals, new_vals, req_info)
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})

@router.get("", response_class=HTMLResponse)
async def ui_list_unit_expenditure(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    
    # This scheme only has DCO Main Office and DCO Staff, no actual districts
    districts_for_filter = SCHEME_DISTRICTS
    
    context = {
        "request": request,
        "resource_name": "प्रपत्र अ",
        "districts": districts_for_filter,
        "primary_units": PRIMARY_UNITS,
        "current_district": district,
        "current_primary_unit": primary_unit,
        "view_mode": view,
        "districts_mr": SCHEME_DISTRICTS_MR,
        "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level,
        "auth_unit": auth_unit,
        "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
    }
    
    if view == "summary":
        fiscal_year = get_fiscal_year_from_request(request, db)
        target_district = None
        if auth_level == 'district' and auth_unit:
            target_district = auth_unit
        elif auth_level == 'taluka' and auth_unit:
            target_district = get_district_from_taluka(auth_unit)
        
        data = _get_summary_and_charts(db, fiscal_year, target_district, exclude_dco=(not target_district))
        if not data.get("summary_rows"):
            raise HTTPException(status_code=500, detail="Could not generate summary data.")
        
        context.update({
            "resource_name": "प्रपत्र अ गोषवारा",
            "chart_data_json": json.dumps(data.get("charts", {})),
            "summary_rows": data["summary_rows"],
            "summary_totals": data["summary_totals"],
            "internal_keys_ordered": data["internal_keys_ordered"]
        })
        resp = templates.TemplateResponse("schemes/s2053/subs/s20530387/unit_expenditure_list.html", context)
        resp.headers.update(get_no_cache_headers())
        return resp
    
    elif view == "edit":
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
        q = build_district_filter(db.query(UnitExpenditure), auth_level, auth_unit, UnitExpenditure)
        q = q.filter(UnitExpenditure.fiscal_year == fiscal_year, UnitExpenditure.sub_scheme_code == sub_scheme)
        
        if district:
            q = q.filter(UnitExpenditure.district == district)
        if primary_unit:
            q = q.filter(UnitExpenditure.unit_account == primary_unit)
        
        total_count = q.with_entities(func.count(UnitExpenditure.id)).scalar()
        items = q.order_by(UnitExpenditure.id).offset((page - 1) * page_size).limit(page_size).all()
        
        filtered_params = {k: v for k, v in {"district": district, "primary_unit": primary_unit}.items() if v}
        context.update({
            "export_query_string_list": "?" + urlencode(filtered_params) if filtered_params else "",
            "items": items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "can_edit": can_edit
        })
        resp = templates.TemplateResponse("schemes/s2053/subs/s20530387/unit_expenditure_list.html", context)
        resp.headers.update(get_no_cache_headers())
        return resp
    
    logger.warning(f"Invalid view: {view}")
    raise HTTPException(status_code=400, detail="Invalid view parameter")

@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_unit_expenditure_form(request: Request, id: int, db: Session = Depends(get_db)):
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = get_auth_unit(request)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed and auth_role == 'assistant':
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    # This scheme only has DCO Main Office and DCO Staff
    districts_for_filter = SCHEME_DISTRICTS
    
    _, sub_scheme = get_scheme_from_cookies(request)
    item = db.query(UnitExpenditure).filter(
        UnitExpenditure.id == id,
        UnitExpenditure.sub_scheme_code == sub_scheme
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
    
    return templates.TemplateResponse("schemes/s2053/subs/s20530387/unit_expenditure_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "primary_units": PRIMARY_UNITS,
        "item": item,
        "resource_name": "प्रपत्र अ संपादन",
        "districts_mr": SCHEME_DISTRICTS_MR,
        "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level,
        "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
    })

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_unit_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    PrimaryAndSecondaryUnitsOfAccount: str = Form(...),
    District: str = Form(...),
    ActualAmountExpenditure20212022: Optional[int] = Form(None),
    ActualAmountExpenditure20222023: Optional[int] = Form(None),
    ActualAmountExpenditure20232024: Optional[int] = Form(None),
    BudgetaryEstimates20242025: Optional[int] = Form(None),
    ImprovedForecast20242025: Optional[int] = Form(None),
    BudgetaryEstimates20252026EstimatingOfficer: Optional[int] = Form(None),
    BudgetaryEstimates20252026ControllingOfficer: Optional[int] = Form(None),
    BudgetaryEstimates20252026AdministrativeDepartment: Optional[int] = Form(None),
    BudgetaryEstimates20252026FinanceDepartment: Optional[int] = Form(None)
):
    auth_role = request.cookies.get('auth_role') or ''
    auth_level = request.cookies.get('auth_level') or ''
    auth_unit = get_auth_unit(request) or ''
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if auth_level == 'taluka' and auth_unit:
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    db_item = db.query(UnitExpenditure).filter(
        UnitExpenditure.id == id,
        UnitExpenditure.sub_scheme_code == sub_scheme
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
    
    try:
        # Capture original values for audit logging
        original_values = AuditService.serialize_values(db_item)
        
        db_item.unit_account = PrimaryAndSecondaryUnitsOfAccount
        db_item.district = District
        if ActualAmountExpenditure20212022 is not None:
            db_item.expenditure_2021_22 = ActualAmountExpenditure20212022
        if ActualAmountExpenditure20222023 is not None:
            db_item.expenditure_2022_23 = ActualAmountExpenditure20222023
        if ActualAmountExpenditure20232024 is not None:
            db_item.expenditure_2023_24 = ActualAmountExpenditure20232024
        if BudgetaryEstimates20242025 is not None:
            db_item.budget_2024_25 = BudgetaryEstimates20242025
        if ImprovedForecast20242025 is not None:
            db_item.forecast_2024_25 = ImprovedForecast20242025
        if BudgetaryEstimates20252026EstimatingOfficer is not None:
            db_item.budget_2025_26_estimating_officer = BudgetaryEstimates20252026EstimatingOfficer
        if auth_level != 'district':
            if BudgetaryEstimates20252026ControllingOfficer is not None:
                db_item.budget_2025_26_controlling_officer = BudgetaryEstimates20252026ControllingOfficer
            if BudgetaryEstimates20252026AdministrativeDepartment is not None:
                db_item.budget_2025_26_admin_dept = BudgetaryEstimates20252026AdministrativeDepartment
            if BudgetaryEstimates20252026FinanceDepartment is not None:
                db_item.budget_2025_26_finance_dept = BudgetaryEstimates20252026FinanceDepartment
        
        # Log audit trail before committing
        AuditService.log_action(
            db=db,
            request=request,
            action='UPDATE',
            table_name=SCHEME_CONFIG.forms['unit_expenditure'].table_name,
            record_id=id,
            old_values=original_values,
            new_values=AuditService.serialize_values(db_item)
        )
        
        db.commit()
        invalidate_scheme_cache(District, patterns=["unit_exp_summary", "unit_exp_charts"])
        try:
            from src.routers.ui_taluka_selection import invalidate_district_status_cache
            scheme_code, _ = get_scheme_from_cookies(request)
            invalidate_district_status_cache(scheme_code, db_item.fiscal_year)
        except Exception:
            pass
        return RedirectResponse(
            url=router.url_path_for("ui_list_unit_expenditure") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update ID {id}: {e}", exc_info=True)
        return templates.TemplateResponse("schemes/s2053/subs/s20530387/unit_expenditure_form.html", {
            "request": request,
            "error": f"अपडेट अयशस्वी: {e}",
            "districts": SCHEME_DISTRICTS,
            "primary_units": PRIMARY_UNITS,
            "item": db_item,
            "resource_name": "प्रपत्र अ संपादन",
            "districts_mr": SCHEME_DISTRICTS_MR,
            "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
            "auth_level": auth_level,
            "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
        }, status_code=400)

@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_summary_excel(request: Request, db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    data = _get_summary_and_charts(db, fiscal_year)
    if not data:
        raise HTTPException(status_code=500, detail="Could not generate summary data")
    
    rows = data['summary_rows']
    totals = data['summary_totals']
    
    df = pd.DataFrame(rows + [totals])
    if 'UnitAccount_EN' in df.columns:
        df = df.drop(columns=['UnitAccount_EN'])
    
    headers_map = {
        "SrNo": "अ. क्र.",
        "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट",
        "expenditure_2021_22": "प्रत्यक्ष रक्कमा 2021-2022",
        "expenditure_2022_23": "प्रत्यक्ष रक्कमा 2022-2023",
        "expenditure_2023_24": "प्रत्यक्ष रक्कमा 2023-2024",
        "budget_2024_25": "अर्थसंकल्पीय अंदाज 2024-2025",
        "forecast_2024_25": "सुधारीत अंदाज 2024-2025",
        "budget_2025_26_estimating_officer": "अर्थसंकल्पीय 2025-2026 प्राकक्लन",
        "budget_2025_26_controlling_officer": "अर्थसंकल्पीय 2025-2026 नियंत्रक",
        "budget_2025_26_admin_dept": "अर्थसंकल्पीय 2025-2026 प्रशासकीय",
        "budget_2025_26_finance_dept": "अर्थसंकल्पीय 2025-2026 वित्त",
    }
    
    cols = [k for k in _ORDERED_KEYS if k in df.columns]
    df = df[cols]
    df.columns = [headers_map.get(c, c) for c in df.columns]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Unit Expenditure Summary', index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        headers={'Content-Disposition': 'attachment; filename="unit_expenditure_summary.xlsx"'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_list_excel(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None)
):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    q = db.query(UnitExpenditure).filter(
        UnitExpenditure.fiscal_year == fiscal_year,
        UnitExpenditure.sub_scheme_code == sub_scheme
    )
    if district:
        q = q.filter(UnitExpenditure.district == district)
    if primary_unit:
        q = q.filter(UnitExpenditure.unit_account == primary_unit)
    
    batch_size = 1000
    offset = 0
    data_list = []
    
    while True:
        batch = q.order_by(UnitExpenditure.id).offset(offset).limit(batch_size).all()
        if not batch:
            break
        columns = [c.name for c in UnitExpenditure.__table__.columns]
        for item in batch:
            data_list.append({col: getattr(item, col, None) for col in columns})
        offset += batch_size
        if len(batch) < batch_size:
            break
    
    df = pd.DataFrame(data_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Unit Expenditure List', index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        headers={'Content-Disposition': 'attachment; filename="unit_expenditure_list.xlsx"'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.get("/export-original", response_class=StreamingResponse)
async def export_unit_expenditure_original(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    """Export original Excel workbook with production-grade throttling."""
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return await export_original_workbook_async(
        db, user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year
    )

@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_unit_expenditure_sheet_only(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    """Export only unit expenditure sheet with throttling."""
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return await export_original_workbook_async(
        db,
        only_sheet="unit_expenditure",
        user_district=user_district,
        sub_scheme_code=sub_scheme,
        fiscal_year=fiscal_year
    )
