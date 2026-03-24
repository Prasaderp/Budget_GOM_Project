"""UI routes for unit expenditure (Form A) - sub-scheme 20530153"""
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
from src.core.templates import render
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.utils_scheme import get_scheme_from_cookies
from src.utils_cache import memory_cache
from src.utils_timing import check_data_filling_allowed
from .excel_export import export_original_workbook_async
from .models import UnitExpenditure
from .config import SCHEME_CONFIG, PRIMARY_UNITS, UNIT_ACCOUNT_MAP_MR
from .helpers import (
    check_edit_permission_for_scheme, invalidate_scheme_cache,
    get_no_cache_headers, validate_numeric_inputs
)
from src.audit_service import AuditService
from src.utils_district import validate_access_control
from src.utils_auth import verify_api_auth, get_auth_unit, get_auth_role, get_auth_level, get_auth_user

router = APIRouter(prefix="/ui/s20530153/unit-expenditure", tags=["UI - प्रपत्र अ"], include_in_schema=False)
logger = logging.getLogger(__name__)

_COLUMNS_TO_SUM = [
    UnitExpenditure.expenditure_prev4,
    UnitExpenditure.expenditure_prev3,
    UnitExpenditure.expenditure_prev2,
    UnitExpenditure.budget_prev1,
    UnitExpenditure.forecast_prev1,
    UnitExpenditure.budget_curr_estimating_officer,
    UnitExpenditure.budget_curr_controlling_officer,
    UnitExpenditure.budget_curr_admin_dept,
    UnitExpenditure.budget_curr_finance_dept
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
        base_filter.append(UnitExpenditure.district != DCO_STAFF_IDENTIFIER)

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
        func.sum(UnitExpenditure.expenditure_prev4).label("e21"),
        func.sum(UnitExpenditure.expenditure_prev3).label("e22"),
        func.sum(UnitExpenditure.expenditure_prev2).label("e23"),
        func.sum(UnitExpenditure.budget_prev1).label("b24"),
        func.sum(UnitExpenditure.forecast_prev1).label("f24"),
        func.sum(UnitExpenditure.budget_curr_estimating_officer).label("est"),
        func.sum(UnitExpenditure.budget_curr_controlling_officer).label("ctrl"),
        func.sum(UnitExpenditure.budget_curr_admin_dept).label("adm"),
        func.sum(UnitExpenditure.budget_curr_finance_dept).label("fin")
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
            "area_trends": {"labels": labels, "exp_prev4": e21, "exp_prev3": e22, "exp_prev2": e23},
            "doughnut_budget": {"labels": labels, "values": b24},
            "multi_axis_comparison": {"labels": labels, "budget_prev1": b24, "forecast_prev1": f24},
            "radar_estimates": {"labels": labels, "estimating_officer": est, "controlling_officer": ctrl, "admin_dept": adm, "finance_dept": fin}
        }
    }
    memory_cache.set(cache_key, result, _CACHE_TTL)
    return result

@router.get("/api/primary-units", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
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

@router.get("/api/record-data", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
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
        "expenditure_prev4": record.expenditure_prev4 or 0,
        "expenditure_prev3": record.expenditure_prev3 or 0,
        "expenditure_prev2": record.expenditure_prev2 or 0,
        "budget_prev1": record.budget_prev1 or 0,
        "forecast_prev1": record.forecast_prev1 or 0,
        "budget_curr_estimating_officer": record.budget_curr_estimating_officer or 0,
        "budget_curr_controlling_officer": record.budget_curr_controlling_officer or 0,
        "budget_curr_admin_dept": record.budget_curr_admin_dept or 0,
        "budget_curr_finance_dept": record.budget_curr_finance_dept or 0
    })

@router.post("/api/update-inline", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    ExpenditurePrev4: int = Form(0),
    ExpenditurePrev3: int = Form(0),
    ExpenditurePrev2: int = Form(0),
    BudgetPrev1: int = Form(0),
    ForecastPrev1: int = Form(0),
    BudgetCurrEstimatingOfficer: int = Form(0),
    BudgetCurrControllingOfficer: int = Form(0),
    BudgetCurrAdminDept: int = Form(0),
    BudgetCurrFinanceDept: int = Form(0)
):
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_user = get_auth_user(request)
    
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
        ExpenditurePrev4, ExpenditurePrev3, ExpenditurePrev2, BudgetPrev1, ForecastPrev1,
        BudgetCurrEstimatingOfficer, BudgetCurrControllingOfficer, BudgetCurrAdminDept, BudgetCurrFinanceDept
    ]
    is_valid, error_msg = validate_numeric_inputs(*vals)
    if not is_valid:
        return JSONResponse({"success": False, "message": error_msg}, status_code=400)
    
    old_vals = {k: getattr(record, k) for k in _INTERNAL_DATA_KEYS}
    
    record.expenditure_prev4 = ExpenditurePrev4
    record.expenditure_prev3 = ExpenditurePrev3
    record.expenditure_prev2 = ExpenditurePrev2
    record.budget_prev1 = BudgetPrev1
    record.forecast_prev1 = ForecastPrev1
    record.budget_curr_estimating_officer = BudgetCurrEstimatingOfficer
    record.budget_curr_controlling_officer = BudgetCurrControllingOfficer
    record.budget_curr_admin_dept = BudgetCurrAdminDept
    record.budget_curr_finance_dept = BudgetCurrFinanceDept
    
    db.commit()
    
    invalidate_scheme_cache(record.district, patterns=["unit_exp_summary", "unit_exp_charts"])
    try:
        from src.routers.ui_taluka_selection import invalidate_district_status_cache
        scheme_code, _ = get_scheme_from_cookies(request)
        invalidate_district_status_cache(scheme_code, record.fiscal_year)
    except Exception:
        pass
    
    new_vals = {k: getattr(record, k) for k in _INTERNAL_DATA_KEYS}
    AuditService.log_edit(db, request, "unit_expenditure", id, auth_user, old_vals, new_vals)
    
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
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    context = {
        "request": request,
        "resource_name": "प्रपत्र अ",
        "districts": districts_for_filter,
        "primary_units": PRIMARY_UNITS,
        "current_district": district,
        "current_primary_unit": primary_unit,
        "view_mode": view,
        "districts_mr": DISTRICTS_MR,
        "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level,
        "auth_unit": auth_unit
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
            "internal_keys_ordered": data["internal_keys_ordered"],
            "relative_years": get_relative_fiscal_years(fiscal_year)
        })
        resp = render(request, "schemes/s2053/subs/s20530153/unit_expenditure_list.html", context)
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
            "can_edit": can_edit,
            "relative_years": get_relative_fiscal_years(fiscal_year)
        })
        resp = render(request, "schemes/s2053/subs/s20530153/unit_expenditure_list.html", context)
        resp.headers.update(get_no_cache_headers())
        return resp
    
    logger.warning(f"Invalid view: {view}")
    raise HTTPException(status_code=400, detail="Invalid view parameter")

@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_unit_expenditure_form(request: Request, id: int, db: Session = Depends(get_db)):
    auth_level = get_auth_level(request)
    auth_role = get_auth_role(request)
    auth_unit = get_auth_unit(request)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed and auth_role == 'assistant':
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    _, sub_scheme = get_scheme_from_cookies(request)
    item = db.query(UnitExpenditure).filter(
        UnitExpenditure.id == id,
        UnitExpenditure.sub_scheme_code == sub_scheme
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    return render(request, "schemes/s2053/subs/s20530153/unit_expenditure_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "primary_units": PRIMARY_UNITS,
        "item": item,
        "resource_name": "प्रपत्र अ संपादन",
        "districts_mr": DISTRICTS_MR,
        "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level,
        "relative_years": get_relative_fiscal_years(fiscal_year)
    })

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_unit_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    PrimaryAndSecondaryUnitsOfAccount: str = Form(...),
    District: str = Form(...),
    ActualAmountExpenditurePrev4: Optional[int] = Form(None),
    ActualAmountExpenditurePrev3: Optional[int] = Form(None),
    ActualAmountExpenditurePrev2: Optional[int] = Form(None),
    BudgetaryEstimatesPrev1: Optional[int] = Form(None),
    ImprovedForecastPrev1: Optional[int] = Form(None),
    BudgetaryEstimatesCurrEstimatingOfficer: Optional[int] = Form(None),
    BudgetaryEstimatesCurrControllingOfficer: Optional[int] = Form(None),
    BudgetaryEstimatesCurrAdministrativeDepartment: Optional[int] = Form(None),
    BudgetaryEstimatesCurrFinanceDepartment: Optional[int] = Form(None)
):
    auth_role = get_auth_role(request) or ''
    auth_level = get_auth_level(request) or ''
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
        db_item.unit_account = PrimaryAndSecondaryUnitsOfAccount
        db_item.district = District
        if ActualAmountExpenditurePrev4 is not None:
            db_item.expenditure_prev4 = ActualAmountExpenditurePrev4
        if ActualAmountExpenditurePrev3 is not None:
            db_item.expenditure_prev3 = ActualAmountExpenditurePrev3
        if ActualAmountExpenditurePrev2 is not None:
            db_item.expenditure_prev2 = ActualAmountExpenditurePrev2
        if BudgetaryEstimatesPrev1 is not None:
            db_item.budget_prev1 = BudgetaryEstimatesPrev1
        if ImprovedForecastPrev1 is not None:
            db_item.forecast_prev1 = ImprovedForecastPrev1
        if BudgetaryEstimatesCurrEstimatingOfficer is not None:
            db_item.budget_curr_estimating_officer = BudgetaryEstimatesCurrEstimatingOfficer
        if auth_level != 'district':
            if BudgetaryEstimatesCurrControllingOfficer is not None:
                db_item.budget_curr_controlling_officer = BudgetaryEstimatesCurrControllingOfficer
            if BudgetaryEstimatesCurrAdministrativeDepartment is not None:
                db_item.budget_curr_admin_dept = BudgetaryEstimatesCurrAdministrativeDepartment
            if BudgetaryEstimatesCurrFinanceDepartment is not None:
                db_item.budget_curr_finance_dept = BudgetaryEstimatesCurrFinanceDepartment
        
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
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        return render(request, "schemes/s2053/subs/s20530153/unit_expenditure_form.html", {
            "request": request,
            "error": "अपडेट अयशस्वी. कृपया पुन्हा प्रयत्न करा.",
            "districts": districts_for_filter,
            "primary_units": PRIMARY_UNITS,
            "item": db_item,
            "resource_name": "प्रपत्र अ संपादन",
            "districts_mr": DISTRICTS_MR,
            "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
            "auth_level": auth_level,
            "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
        }, status_code=400)

@router.get("/summary/export-excel", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
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
        "expenditure_prev4": "प्रत्यक्ष रक्कमा 2021-2022",
        "expenditure_prev3": "प्रत्यक्ष रक्कमा 2022-2023",
        "expenditure_prev2": "प्रत्यक्ष रक्कमा 2023-2024",
        "budget_prev1": "अर्थसंकल्पीय अंदाज 2024-2025",
        "forecast_prev1": "सुधारीत अंदाज 2024-2025",
        "budget_curr_estimating_officer": "अर्थसंकल्पीय 2025-2026 प्राकक्लन",
        "budget_curr_controlling_officer": "अर्थसंकल्पीय 2025-2026 नियंत्रक",
        "budget_curr_admin_dept": "अर्थसंकल्पीय 2025-2026 प्रशासकीय",
        "budget_curr_finance_dept": "अर्थसंकल्पीय 2025-2026 वित्त",
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

@router.get("/list/export-excel", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
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

@router.get("/export-original", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
async def export_unit_expenditure_original(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    """Export original Excel workbook with production-grade throttling."""
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = auth_unit if auth_level == 'district' else (district if auth_level in ('dco', 'officer1', 'officer2') else None)
    _, sub_scheme = get_scheme_from_cookies(request)
    return await export_original_workbook_async(db, user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year)

@router.get("/export-sheet-only", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
async def export_unit_expenditure_sheet_only(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    """Export only unit expenditure sheet with throttling."""
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = auth_unit if auth_level == 'district' else (district if auth_level in ('dco', 'officer1', 'officer2') else None)
    _, sub_scheme = get_scheme_from_cookies(request)
    return await export_original_workbook_async(db, only_sheet="unit_expenditure", user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year)
