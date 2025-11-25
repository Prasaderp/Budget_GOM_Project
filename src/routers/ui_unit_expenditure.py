from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any, List
from src import models
from src.database import get_db
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, PRIMARY_UNITS, UNIT_ACCOUNT_MAP_MR, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_cache import memory_cache
from src.excel_template_export import export_original_workbook
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
import logging
import json

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/ui/unit-expenditure", tags=["UI - प्रपत्र अ"], include_in_schema=False)
logger = logging.getLogger(__name__)

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit")

# pre-compute column definitions once
_COLUMNS_TO_SUM = [
    models.UnitExpenditure.expenditure_2021_22,
    models.UnitExpenditure.expenditure_2022_23,
    models.UnitExpenditure.expenditure_2023_24,
    models.UnitExpenditure.budget_2024_25,
    models.UnitExpenditure.forecast_2024_25,
    models.UnitExpenditure.budget_2025_26_estimating_officer,
    models.UnitExpenditure.budget_2025_26_controlling_officer,
    models.UnitExpenditure.budget_2025_26_admin_dept,
    models.UnitExpenditure.budget_2025_26_finance_dept
]
_INTERNAL_DATA_KEYS = [col.name for col in _COLUMNS_TO_SUM]
_ORDERED_KEYS = ["SrNo", "UnitAccount"] + _INTERNAL_DATA_KEYS

_CACHE_TTL = 300  # 5 minutes


def _make_cache_key(prefix: str, *args) -> str:
    return f"{prefix}|{'|'.join(str(a) for a in args)}"


def _invalidate_summary_cache(district: Optional[str] = None, fiscal_year: Optional[str] = None):
    patterns = ["unit_exp_summary", "unit_exp_charts"]
    if district:
        patterns.extend([f"district_summary|{district}", f"district_charts|{district}"])
    with memory_cache._lock:
        keys_to_del = [k for k in list(memory_cache._store.keys()) if any(p in k for p in patterns)]
        for k in keys_to_del:
            memory_cache._store.pop(k, None)


def _check_edit_permission_cached(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    if auth_role in ("officer1", "officer2", "dco"):
        return False
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            return False
    if auth_role == 'assistant':
        from src.utils_timing import check_data_filling_allowed
        is_allowed, _ = check_data_filling_allowed(db, auth_level, auth_role)
        return is_allowed
    return True


def _log_audit_async(db_url: str, table: str, record_id: int, username: str, old_vals: Dict, new_vals: Dict, request_info: Dict):
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models import AuditLog
        engine = create_engine(db_url, pool_pre_ping=True, pool_size=1)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            changed = [{"field": k, "old": old_vals.get(k), "new": new_vals.get(k)} 
                       for k in set(old_vals) | set(new_vals) if old_vals.get(k) != new_vals.get(k)]
            if not changed:
                return
            entry = AuditLog(
                table_name=table, record_id=record_id, action='UPDATE',
                username=username, user_level=request_info.get('level', ''),
                user_role=request_info.get('role', ''), user_unit=request_info.get('unit', ''),
                old_values=old_vals, new_values=new_vals, changed_fields=changed,
                ip_address=request_info.get('ip', ''), user_agent=request_info.get('ua', ''),
                session_id=request_info.get('sid', '')
            )
            session.add(entry)
            session.commit()
        finally:
            session.close()
            engine.dispose()
    except Exception:
        pass


def _get_summary_and_charts(db: Session, fiscal_year: str, district: Optional[str] = None, exclude_dco: bool = True) -> Dict[str, Any]:
    cache_key = _make_cache_key("unit_exp_combined", district or "all", fiscal_year)
    cached = memory_cache.get(cache_key)
    if cached:
        return cached

    base_filter = [models.UnitExpenditure.fiscal_year == fiscal_year]
    if district:
        base_filter.append(models.UnitExpenditure.district == district)
    elif exclude_dco:
        base_filter.append(models.UnitExpenditure.district != DCO_STAFF_IDENTIFIER)

    sum_exprs = [func.sum(col).label(col.name) for col in _COLUMNS_TO_SUM]
    
    # summary by unit_account
    summary_query = db.query(
        models.UnitExpenditure.unit_account.label("unit_account"), *sum_exprs
    ).filter(*base_filter).group_by(models.UnitExpenditure.unit_account).order_by(models.UnitExpenditure.unit_account).all()

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

    # charts by district
    charts_query = db.query(
        models.UnitExpenditure.district,
        func.sum(models.UnitExpenditure.expenditure_2021_22).label("e21"),
        func.sum(models.UnitExpenditure.expenditure_2022_23).label("e22"),
        func.sum(models.UnitExpenditure.expenditure_2023_24).label("e23"),
        func.sum(models.UnitExpenditure.budget_2024_25).label("b24"),
        func.sum(models.UnitExpenditure.forecast_2024_25).label("f24"),
        func.sum(models.UnitExpenditure.budget_2025_26_estimating_officer).label("est"),
        func.sum(models.UnitExpenditure.budget_2025_26_controlling_officer).label("ctrl"),
        func.sum(models.UnitExpenditure.budget_2025_26_admin_dept).label("adm"),
        func.sum(models.UnitExpenditure.budget_2025_26_finance_dept).label("fin")
    ).filter(*base_filter).group_by(models.UnitExpenditure.district).order_by(models.UnitExpenditure.district).all()

    labels, e21, e22, e23, b24, f24, est, ctrl, adm, fin = [], [], [], [], [], [], [], [], [], []
    for r in charts_query:
        labels.append(r.district or 'Unknown')
        e21.append(int(r.e21 or 0)); e22.append(int(r.e22 or 0)); e23.append(int(r.e23 or 0))
        b24.append(int(r.b24 or 0)); f24.append(int(r.f24 or 0))
        est.append(int(r.est or 0)); ctrl.append(int(r.ctrl or 0))
        adm.append(int(r.adm or 0)); fin.append(int(r.fin or 0))

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
async def api_get_primary_units(request: Request, district: Optional[str] = Query(None), db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    cache_key = _make_cache_key("primary_units", district or "all", fiscal_year)
    cached = memory_cache.get(cache_key)
    if cached:
        return JSONResponse(cached)
    
    q = db.query(models.UnitExpenditure.unit_account).distinct().filter(models.UnitExpenditure.fiscal_year == fiscal_year)
    if district:
        q = q.filter(models.UnitExpenditure.district == district)
    units = [r[0] for r in q.order_by(models.UnitExpenditure.unit_account).limit(500).all()]
    result = {"units": units}
    memory_cache.set(cache_key, result, _CACHE_TTL)
    return JSONResponse(result)


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
async def api_update_inline(
    request: Request, db: Session = Depends(get_db),
    id: int = Form(...),
    Expenditure202122: int = Form(0), Expenditure202223: int = Form(0), Expenditure202324: int = Form(0),
    Budget202425: int = Form(0), Forecast202425: int = Form(0),
    Budget202526EstimatingOfficer: int = Form(0), Budget202526ControllingOfficer: int = Form(0),
    Budget202526AdminDept: int = Form(0), Budget202526FinanceDept: int = Form(0)
):
    from src.utils_timing import check_data_filling_allowed
    import os
    
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if not _check_edit_permission_cached(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    record = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    # access control
    if auth_level == 'district' and auth_unit:
        if auth_unit == DCO_STAFF_IDENTIFIER:
            if record.district != DCO_STAFF_IDENTIFIER:
                return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
        elif record.district != auth_unit or record.district == DCO_STAFF_IDENTIFIER:
            return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    
    if auth_level == 'taluka' and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        if not district_name or record.district != district_name or record.district == DCO_STAFF_IDENTIFIER:
            return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    
    vals = [Expenditure202122, Expenditure202223, Expenditure202324, Budget202425, Forecast202425,
            Budget202526EstimatingOfficer, Budget202526ControllingOfficer, Budget202526AdminDept, Budget202526FinanceDept]
    if any(v < 0 for v in vals):
        return JSONResponse({"success": False, "message": "नकारात्मक मूल्ये स्वीकार्य नाहीत"}, status_code=400)
    if any(v > 999999999 for v in vals):
        return JSONResponse({"success": False, "message": "मूल्य खूप मोठे आहे"}, status_code=400)
    
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
    
    # invalidate cache after update
    _invalidate_summary_cache(record.district, record.fiscal_year)
    
    # async audit
    new_vals = {k: getattr(record, k) for k in _INTERNAL_DATA_KEYS}
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    req_info = {
        "level": auth_level, "role": auth_role, "unit": auth_unit,
        "ip": ip, "ua": request.headers.get("user-agent", "")[:200],
        "sid": request.cookies.get("session_id", "")
    }
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        _audit_executor.submit(_log_audit_async, db_url, "unit_expenditure", id, auth_user, old_vals, new_vals, req_info)
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})


@router.get("", response_class=HTMLResponse)
async def ui_list_unit_expenditure(
    request: Request, db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
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
        "request": request, "resource_name": "प्रपत्र अ",
        "districts": districts_for_filter, "primary_units": PRIMARY_UNITS,
        "current_district": district, "current_primary_unit": primary_unit,
        "view_mode": view, "districts_mr": DISTRICTS_MR,
        "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level, "auth_unit": auth_unit
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
        resp = templates.TemplateResponse("unit_expenditure_list.html", context)
        resp.headers.update({"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
        return resp
    
    elif view == "edit":
        fiscal_year = get_fiscal_year_from_request(request, db)
        can_edit = _check_edit_permission_cached(auth_role, auth_level, auth_unit, db)
        q = build_district_filter(db.query(models.UnitExpenditure), auth_level, auth_unit, models.UnitExpenditure)
        q = q.filter(models.UnitExpenditure.fiscal_year == fiscal_year)
        
        if district:
            q = q.filter(models.UnitExpenditure.district == district)
        if primary_unit:
            q = q.filter(models.UnitExpenditure.unit_account == primary_unit)
        
        total_count = q.with_entities(func.count(models.UnitExpenditure.id)).scalar()
        items = q.order_by(models.UnitExpenditure.id).offset((page - 1) * page_size).limit(page_size).all()
        
        filtered_params = {k: v for k, v in {"district": district, "primary_unit": primary_unit}.items() if v}
        context.update({
            "export_query_string_list": "?" + urlencode(filtered_params) if filtered_params else "",
            "items": items, "total_count": total_count, "page": page,
            "page_size": page_size, "can_edit": can_edit
        })
        resp = templates.TemplateResponse("unit_expenditure_list.html", context)
        resp.headers.update({"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
        return resp
    
    logger.warning(f"Invalid view: {view}")
    raise HTTPException(status_code=400, detail="Invalid view parameter")


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
    if not item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
    
    return templates.TemplateResponse("unit_expenditure_form.html", {
        "request": request, "districts": districts_for_filter,
        "primary_units": PRIMARY_UNITS, "item": item,
        "resource_name": "प्रपत्र अ संपादन",
        "districts_mr": DISTRICTS_MR, "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level
    })


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_unit_expenditure(
    request: Request, id: int, db: Session = Depends(get_db),
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
    from src.utils_timing import check_data_filling_allowed
    auth_role = request.cookies.get('auth_role') or ''
    auth_level = request.cookies.get('auth_level') or ''
    auth_unit = request.cookies.get('auth_unit') or ''
    
    if auth_role in ("officer1", "officer2", "dco"):
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
    if not db_item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
    
    try:
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
        
        db.commit()
        _invalidate_summary_cache(District)
        return RedirectResponse(url=router.url_path_for("ui_list_unit_expenditure") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update ID {id}: {e}", exc_info=True)
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        return templates.TemplateResponse("unit_expenditure_form.html", {
            "request": request, "error": f"अपडेट अयशस्वी: {e}",
            "districts": districts_for_filter, "primary_units": PRIMARY_UNITS,
            "item": db_item, "resource_name": "प्रपत्र अ संपादन",
            "districts_mr": DISTRICTS_MR, "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
            "auth_level": auth_level
        }, status_code=400)


@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_unit_expenditure_summary_excel(request: Request, db: Session = Depends(get_db)):
    import pandas as pd
    import io
    
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
        "SrNo": "अ. क्र.", "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट",
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
    request: Request, db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None)
):
    import pandas as pd
    import io
    from src import schemas
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    q = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.fiscal_year == fiscal_year)
    if district:
        q = q.filter(models.UnitExpenditure.district == district)
    if primary_unit:
        q = q.filter(models.UnitExpenditure.unit_account == primary_unit)
    
    # stream in batches
    batch_size = 1000
    offset = 0
    data_list = []
    
    while True:
        batch = q.order_by(models.UnitExpenditure.id).offset(offset).limit(batch_size).all()
        if not batch:
            break
        for item in batch:
            try:
                validated = schemas.UnitExpenditureResponse.model_validate(item)
                data_list.append(validated.model_dump())
            except Exception:
                pass
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
async def export_unit_expenditure_original(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = auth_unit if auth_level == 'district' else (district if auth_level in ('dco', 'officer1', 'officer2') else None)
    return export_original_workbook(db, user_district=user_district)


@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_unit_expenditure_sheet_only(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = auth_unit if auth_level == 'district' else (district if auth_level in ('dco', 'officer1', 'officer2') else None)
    return export_original_workbook(db, only_sheet="unit_expenditure", user_district=user_district)
