from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
import json
import os

from src.models import PayMatrix, AuditLog
from src.database import get_db, SessionLocal
from src.core.templates import templates
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_cache import memory_cache
from src.utils_scheme import get_scheme_from_cookies
from src.excel_template_export import export_original_workbook
from src.audit_service import AuditService
from .models import BudgetPostDetails, SUB_SCHEME_CODE
from .config import (
    CATEGORIES, CLASSES_SHEET1_2, DESIGNATIONS,
    CATEGORIES_MR, CLASSES_MR, DESIGNATIONS_MR, MARATHI_TO_ENGLISH_DESIGNATIONS
)

def _format_basic_pay(val):
    if val is None:
        return 0
    fval = float(val)
    if fval >= 1000:
        fval = round(round(fval / 100) / 10, 1)
    return int(fval) if fval == int(fval) else fval

router = APIRouter(prefix="/ui/budget-post-details", tags=["UI - प्रपत्र ड"], include_in_schema=False)

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_budget")

_BUDGET_COLUMNS = [
    'sanctioned_posts_2024_25', 'sanctioned_posts_2025_26', 'special_pay', 'basic_pay',
    'grade_pay', 'local_supplementary_allowance', 'vehicle_allowance',
    'washing_allowance', 'cash_allowance', 'footwear_allowance_other', 'hra_rate'
]


def _check_edit_permission(auth_role: str, auth_level: str, auth_unit: str, db: Session) -> bool:
    if auth_role in ("officer1", "officer2", "dco"):
        return False
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            return False
    if auth_role == 'assistant':
        from src.utils_timing import check_data_filling_allowed
        allowed, _ = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        return allowed
    return True


def _invalidate_budget_cache(district: Optional[str] = None):
    patterns = ["budget_summary", "budget_details"]
    if district:
        patterns.append(f"district_budget|{district}")
    with memory_cache._lock:
        keys = [k for k in list(memory_cache._store.keys()) if any(p in k for p in patterns)]
        for k in keys:
            memory_cache._store.pop(k, None)


def _log_audit_async(table: str, record_id: int, username: str, old_vals: dict, new_vals: dict, req_info: dict):
    try:
        session = SessionLocal()
        try:
            changed = [{"field": k, "old": old_vals.get(k), "new": new_vals.get(k)} 
                       for k in set(old_vals) | set(new_vals) if old_vals.get(k) != new_vals.get(k)]
            if not changed:
                return
            entry = AuditLog(
                table_name=table, record_id=record_id, action='UPDATE',
                username=username, user_level=req_info.get('level', ''),
                user_role=req_info.get('role', ''), user_unit=req_info.get('unit', ''),
                old_values=old_vals, new_values=new_vals, changed_fields=changed,
                ip_address=req_info.get('ip', ''), user_agent=req_info.get('ua', ''),
                session_id=req_info.get('sid', '')
            )
            session.add(entry)
            session.commit()
        finally:
            session.close()
    except Exception:
        pass


def translate_marathi_designation_search(search_term: str) -> str:
    if not search_term:
        return search_term
    search_lower = search_term.lower().strip()
    for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
        if m_term.lower() in search_lower or search_lower in m_term.lower():
            return e_desig
    for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
        m_words = m_term.lower().split()
        s_words = search_lower.split()
        for mw in m_words:
            for sw in s_words:
                if len(sw) >= 3 and (mw.startswith(sw) or sw.startswith(mw)):
                    return e_desig
    return search_term


from .ui_budget_summary import get_budget_summary_data, get_district_budget_summary_data

@router.get("/api/pay-matrix/stages", response_class=JSONResponse)
async def api_get_pay_matrix_stages(db: Session = Depends(get_db)):
    stages = db.query(PayMatrix.stage).distinct().order_by(PayMatrix.stage).all()
    sorted_stages = sorted([s[0] for s in stages], key=lambda x: int(x.split('-')[1]))
    return JSONResponse({"stages": sorted_stages})

@router.get("/api/pay-matrix/levels/{stage}", response_class=JSONResponse)
async def api_get_pay_matrix_levels(stage: str, db: Session = Depends(get_db)):
    levels = db.query(PayMatrix.level).filter(PayMatrix.stage == stage).order_by(PayMatrix.level).all()
    return JSONResponse({"levels": [l[0] for l in levels]})

@router.get("/api/pay-matrix/basic-pay", response_class=JSONResponse)
async def api_get_pay_matrix_basic_pay(stage: str = Query(...), level: int = Query(...), db: Session = Depends(get_db)):
    record = db.query(PayMatrix).filter(PayMatrix.stage == stage, PayMatrix.level == level).first()
    if not record:
        return JSONResponse({"found": False, "basic_pay": 0})
    basic_pay_thousands = record.basic_pay // 1000
    return JSONResponse({"found": True, "basic_pay": basic_pay_thousands, "basic_pay_full": record.basic_pay})

@router.get("/api/designations", response_class=JSONResponse)
async def api_get_designations(request: Request, district: Optional[str] = Query(None), category: Optional[str] = Query(None), cls: Optional[str] = Query(None, alias="class"), db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(BudgetPostDetails.designation).distinct().filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(BudgetPostDetails.district == district)
    if category:
        query = query.filter(BudgetPostDetails.category == category)
    if cls:
        query = query.filter(BudgetPostDetails.class_type == cls)
    designations = [row[0] for row in query.order_by(BudgetPostDetails.designation).all()]
    return JSONResponse({"designations": designations})

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(request: Request, district: str = Query(...), category: str = Query(...), cls: str = Query(..., alias="class"), designation: str = Query(...), db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == sub_scheme,
        BudgetPostDetails.district == district,
        BudgetPostDetails.category == category,
        BudgetPostDetails.class_type == cls,
        BudgetPostDetails.designation == designation
    ).first()
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True, "id": record.id,
        "sanctioned_posts_2024_25": record.sanctioned_posts_2024_25 or 0,
        "sanctioned_posts_2025_26": record.sanctioned_posts_2025_26 or 0,
        "special_pay": record.special_pay or 0, "basic_pay": _format_basic_pay(record.basic_pay),
        "grade_pay": record.grade_pay or 0,
        "local_supplementary_allowance": record.local_supplementary_allowance or 0,
        "vehicle_allowance": record.vehicle_allowance or 0,
        "washing_allowance": record.washing_allowance or 0,
        "cash_allowance": record.cash_allowance or 0,
        "footwear_allowance_other": record.footwear_allowance_other or 0,
        "hra_rate": record.hra_rate or 'X'
    })

@router.post("/api/update-inline", response_class=JSONResponse)
async def api_update_inline(
    request: Request, db: Session = Depends(get_db),
    id: int = Form(...),
    SanctionedPosts202425: int = Form(0), SanctionedPosts202526: int = Form(0),
    SpecialPay: int = Form(0), BasicPay: float = Form(0), GradePay: int = Form(0),
    LocalSupplemetoryAllowance: int = Form(0), VehicleAllowance: int = Form(0),
    WashingAllowance: int = Form(0), CashAllowance: int = Form(0), FootWareAllowanceOther: int = Form(0),
    HraRate: str = Form('X')
):
    from src.utils_timing import check_data_filling_allowed
    
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if not _check_edit_permission(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    ).first()
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
    
    vals_int = [SanctionedPosts202425, SanctionedPosts202526, SpecialPay, GradePay,
                LocalSupplemetoryAllowance, VehicleAllowance, WashingAllowance, CashAllowance, FootWareAllowanceOther]
    if any(v < 0 for v in vals_int) or BasicPay < 0:
        return JSONResponse({"success": False, "message": "नकारात्मक मूल्ये स्वीकार्य नाहीत"}, status_code=400)
    if any(v > 999999999 for v in vals_int) or BasicPay > 999999999:
        return JSONResponse({"success": False, "message": "मूल्य खूप मोठे आहे"}, status_code=400)
    
    if HraRate not in ('X', 'Y', 'Z'):
        HraRate = 'X'
    
    old_values = {k: getattr(record, k) for k in _BUDGET_COLUMNS}
    
    record.sanctioned_posts_2024_25 = SanctionedPosts202425
    record.sanctioned_posts_2025_26 = SanctionedPosts202526
    record.special_pay = SpecialPay
    record.basic_pay = BasicPay
    record.grade_pay = GradePay
    record.local_supplementary_allowance = LocalSupplemetoryAllowance
    record.vehicle_allowance = VehicleAllowance
    record.washing_allowance = WashingAllowance
    record.cash_allowance = CashAllowance
    record.footwear_allowance_other = FootWareAllowanceOther
    record.hra_rate = HraRate
    
    db.commit()
    
    _invalidate_budget_cache(record.district)
    
    # async audit
    new_values = {k: getattr(record, k) for k in _BUDGET_COLUMNS}
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    req_info = {
        "level": auth_level,
        "role": auth_role,
        "unit": auth_unit,
        "ip": ip,
        "ua": request.headers.get("user-agent", "")[:200],
        "sid": request.cookies.get("session_id", "")
    }
    _audit_executor.submit(
        _log_audit_async,
        "budget_post_details",
        id,
        auth_user,
        old_values,
        new_values,
        req_info,
    )
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})

@router.get("", response_class=HTMLResponse)
async def ui_list_budget_details(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    designation_search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    fiscal_year = get_fiscal_year_from_request(request, db)
    can_edit = _check_edit_permission(auth_role, auth_level, auth_unit, db)

    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    context = {
        "request": request, "districts": districts_for_filter, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2,
        "current_district": district, "current_category": category, "current_class": cls,
        "current_designation_search": designation_search,
        "districts_mr": DISTRICTS_MR, "categories_mr": CATEGORIES_MR, "classes_mr": CLASSES_MR,
        "designations_mr": DESIGNATIONS_MR, "auth_level": auth_level
    }

    if view == "summary":
        if auth_level == 'district' and auth_unit:
            summary_data = get_district_budget_summary_data(db, auth_unit, fiscal_year)
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            summary_data = get_district_budget_summary_data(db, district_name, fiscal_year) if district_name else None
        else:
            summary_data = get_budget_summary_data(db, fiscal_year)
        
        if not summary_data:
            raise HTTPException(status_code=500, detail="Could not generate summary data.")

        district_summary = summary_data.get("district_summary", {})
        if auth_level == 'district' and auth_unit:
            labels = [auth_unit]
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            labels = [district_name] if district_name else []
        elif auth_level == 'dco':
            labels = DISTRICTS
        else:
            labels = REGULAR_DISTRICTS
        
        chart_data = {
            "district_components": summary_data.get("district_components", {}),
            "district_totals_for_scatter": summary_data.get("district_totals_for_scatter", {})
        }
        
        if labels:
            perm_posts = [int(district_summary.get(d, {}).get('Permanent', {}).get("Posts2526", 0) or 0) for d in labels]
            temp_posts = [int(district_summary.get(d, {}).get('Temporary', {}).get("Posts2526", 0) or 0) for d in labels]
            perm_cost = [int(district_summary.get(d, {}).get('Permanent', {}).get("TotalCost", 0) or 0) for d in labels]
            temp_cost = [int(district_summary.get(d, {}).get('Temporary', {}).get("TotalCost", 0) or 0) for d in labels]
            
            if any(v > 0 for v in perm_posts + temp_posts):
                chart_data["district_posts_stack"] = {"labels": labels, "स्थायी": perm_posts, "अस्थायी": temp_posts}
            if any(v > 0 for v in perm_cost + temp_cost):
                chart_data["district_cost_stack"] = {"labels": labels, "स्थायी": perm_cost, "अस्थायी": temp_cost}

        context.update({
            "resource_name": "प्रपत्र ड गोषवारा", "view_mode": "summary",
            "auth_unit": auth_unit, "chart_data_summary_json": json.dumps(chart_data)
        })
        context.update(summary_data)
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_list.html", context)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    elif view == "edit":
        _, sub_scheme = get_scheme_from_cookies(request)
        query = build_district_filter(db.query(BudgetPostDetails), auth_level, auth_unit, BudgetPostDetails).filter(
            BudgetPostDetails.fiscal_year == fiscal_year,
            BudgetPostDetails.sub_scheme_code == sub_scheme
        )
        
        if district:
            query = query.filter(BudgetPostDetails.district == district)
        if category:
            query = query.filter(BudgetPostDetails.category == category)
        if cls:
            query = query.filter(BudgetPostDetails.class_type == cls)
        if designation_search:
            translated_search = translate_marathi_designation_search(designation_search)
            query = query.filter(BudgetPostDetails.designation.ilike(f"%{translated_search}%"))
        
        total_count = query.with_entities(func.count(BudgetPostDetails.id)).scalar()
        details = query.order_by(BudgetPostDetails.id).offset((page - 1) * page_size).limit(page_size).all()

        filtered_params = {k: v for k, v in {"district": district, "category": category, "class": cls, "designation_search": designation_search}.items() if v}
        
        context.update({
            "resource_name": "प्रपत्र ड", "view_mode": "edit", "details": details,
            "total_count": total_count, "page": page, "page_size": page_size,
            "export_query_string": "?" + urlencode(filtered_params) if filtered_params else "",
            "can_edit": can_edit
        })
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_list.html", context)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter")

@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_budget_detail_form(request: Request, id: int, db: Session = Depends(get_db)):
    from src.utils_timing import check_data_filling_allowed
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = request.cookies.get('auth_unit')
    
    if auth_role == 'assistant':
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    detail = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    ).first()
    if not detail:
        raise HTTPException(status_code=404, detail=f"प्रपत्र ड ID {id} सापडला नाही")
    
    detail.basic_pay = _format_basic_pay(detail.basic_pay)
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    return templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_form.html", { "request": request, "districts": districts_for_filter, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2, "designations": DESIGNATIONS, "detail": detail, "resource_name": f"प्रपत्र ड संपादन (ID: {id})", "is_edit": True, "districts_mr": DISTRICTS_MR, "categories_mr": CATEGORIES_MR, "classes_mr": CLASSES_MR, "designations_mr": DESIGNATIONS_MR, "auth_level": auth_level })

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_budget_detail( request: Request, id: int, db: Session = Depends(get_db), District: str = Form(...), Category: str = Form(...), Class: str = Form(...), Designation: str = Form(...), SanctionedPosts202425: Optional[int] = Form(None), SanctionedPosts202526: Optional[int] = Form(None), SpecialPay: Optional[int] = Form(None), BasicPay: Optional[float] = Form(None), GradePay: Optional[int] = Form(None), LocalSupplemetoryAllowance: Optional[int] = Form(None), VehicleAllowance: Optional[int] = Form(None), WashingAllowance: Optional[int] = Form(None), CashAllowance: Optional[int] = Form(None), FootWareAllowanceOther: Optional[int] = Form(None), HraRate: Optional[str] = Form('X'), Other: Optional[int] = Form(None) ):
    from src.utils_timing import check_data_filling_allowed
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit) or District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=403, detail="Invalid access")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    db_detail = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    ).first()
    if not db_detail:
        raise HTTPException(status_code=404, detail=f"प्रपत्र ड ID {id} सापडला नाही")
    
    try:
        if HraRate not in ('X', 'Y', 'Z'):
            HraRate = 'X'
        original_values = AuditService.serialize_values(db_detail)
        update_dict = {
            "district": District, "category": Category, "class_type": Class, "designation": Designation,
            "sanctioned_posts_2024_25": SanctionedPosts202425, "sanctioned_posts_2025_26": SanctionedPosts202526,
            "special_pay": SpecialPay, "basic_pay": BasicPay, "grade_pay": GradePay,
            "local_supplementary_allowance": LocalSupplemetoryAllowance, "vehicle_allowance": VehicleAllowance,
            "washing_allowance": WashingAllowance, "cash_allowance": CashAllowance,
            "footwear_allowance_other": FootWareAllowanceOther, "hra_rate": HraRate
        }
        for key, value in update_dict.items():
            if value is not None and hasattr(db_detail, key):
                setattr(db_detail, key, value)
        
        AuditService.log_action(db=db, request=request, action='UPDATE', table_name='budget_post_details',
                                record_id=id, old_values=original_values,
                                new_values=AuditService.serialize_values(db_detail))
        db.commit()
        return RedirectResponse(url=router.url_path_for("ui_list_budget_details") + "?view=edit",
                                status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        detail_for_form = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id).first()
        if detail_for_form:
            detail_for_form.basic_pay = _format_basic_pay(detail_for_form.basic_pay)
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        
        return templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_form.html", { "request": request, "error": f"रेकॉर्ड अपडेट करण्यात अयशस्वी: {e}", "districts": districts_for_filter, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2, "designations": DESIGNATIONS, "detail": detail_for_form, "resource_name": f"प्रपत्र ड संपादन (ID: {id})", "is_edit": True, "districts_mr": DISTRICTS_MR, "categories_mr": CATEGORIES_MR, "classes_mr": CLASSES_MR, "designations_mr": DESIGNATIONS_MR, "auth_level": auth_level }, status_code=400)

@router.get("/export-excel", response_class=StreamingResponse)
async def export_budget_details_excel( request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None), category: Optional[str] = Query(None), cls: Optional[str] = Query(None, alias="class"), designation_search: Optional[str] = Query(None) ):
    import pandas as pd
    import io
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(BudgetPostDetails.district == district)
    if category:
        query = query.filter(BudgetPostDetails.category == category)
    if cls:
        query = query.filter(BudgetPostDetails.class_type == cls)
    if designation_search:
        query = query.filter(BudgetPostDetails.designation.ilike(f"%{translate_marathi_designation_search(designation_search)}%"))
    
    details = query.order_by(BudgetPostDetails.id).all()
    columns = [c.name for c in BudgetPostDetails.__table__.columns]
    df = pd.DataFrame([{col: getattr(item, col, None) for col in columns} for item in details])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Budget Post Details', index=False)
    output.seek(0)
    return StreamingResponse(output, headers={'Content-Disposition': 'attachment; filename="budget_post_details.xlsx"'},
                             media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/export-original", response_class=StreamingResponse)
async def export_budget_details_original(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    return export_original_workbook(db, user_district=user_district)

@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_budget_details_sheet_only(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    return export_original_workbook(db, only_sheet="budget_post_details", user_district=user_district)