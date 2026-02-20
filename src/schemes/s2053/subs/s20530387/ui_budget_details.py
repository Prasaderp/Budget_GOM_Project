"""UI routes for budget post details (Form D) - sub-scheme 20530387"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from urllib.parse import urlencode
import json
import pandas as pd
import io

from src.database import get_db
from src.core.templates import templates
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.utils_da_rate import get_da_percentage, get_da_rate
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from .excel_export import export_original_workbook_async
from src.audit_service import AuditService
from .models import BudgetPostDetails
from .config import (
    SCHEME_CONFIG, CATEGORIES, CLASSES_SHEET1_2, DESIGNATIONS,
    CATEGORIES_MR, CLASSES_MR, DESIGNATIONS_MR, MARATHI_TO_ENGLISH_DESIGNATIONS,
    SCHEME_DISTRICTS, SCHEME_DISTRICTS_MR, SUB_SCHEME_CODE
)
from .helpers import (
    check_edit_permission_for_scheme, invalidate_scheme_cache, log_audit_async,
    get_request_info, get_no_cache_headers, validate_numeric_inputs, validate_access_control
)
from .ui_budget_summary import get_budget_summary_data, get_district_budget_summary_data
from src.utils_auth import get_auth_unit

router = APIRouter(prefix="/ui/s20530387/budget-post-details", tags=["UI - प्रपत्र ड"], include_in_schema=False)

def _format_basic_pay(val):
    """Format basic pay value for display"""
    if val is None:
        return 0
    fval = float(val)
    if fval >= 1000:
        fval = round(round(fval / 100) / 10, 1)
    return int(fval) if fval == int(fval) else fval

def translate_marathi_designation_search(search_term: str) -> str:
    """Translate Marathi designation search to English"""
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
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
    da_rate = get_da_rate(db, fiscal_year)

    # This scheme only has DCO Main Office and DCO Staff, no actual districts
    districts_for_filter = SCHEME_DISTRICTS
    
    context = {
        "request": request,
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "current_district": district,
        "current_category": category,
        "current_class": cls,
        "current_designation_search": designation_search,
        "districts_mr": SCHEME_DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "designations_mr": DESIGNATIONS_MR,
        "auth_level": auth_level,
        "da_rate": da_rate,
        "relative_years": get_relative_fiscal_years(fiscal_year)
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
        # This scheme only has DCO Main Office and DCO Staff
        labels = SCHEME_DISTRICTS
        
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
            "resource_name": "प्रपत्र ड गोषवारा",
            "view_mode": "summary",
            "auth_unit": auth_unit,
            "chart_data_summary_json": json.dumps(chart_data)
        })
        context.update(summary_data)
        response = templates.TemplateResponse("schemes/s2053/subs/s20530387/budget_post_details_list.html", context)
        response.headers.update(get_no_cache_headers())
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
            "resource_name": "प्रपत्र ड",
            "view_mode": "edit",
            "details": details,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "export_query_string": "?" + urlencode(filtered_params) if filtered_params else "",
            "can_edit": can_edit
        })
        response = templates.TemplateResponse("schemes/s2053/subs/s20530387/budget_post_details_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response

    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter")

@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_budget_detail_form(request: Request, id: int, db: Session = Depends(get_db)):
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = get_auth_unit(request)
    
    if auth_role == 'assistant':
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
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
    
    # This scheme only has DCO Main Office and DCO Staff
    districts_for_filter = SCHEME_DISTRICTS
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    from src.utils_salary_mode import get_salary_mode
    salary_mode = get_salary_mode(db, fiscal_year)
    da_percentage = get_da_percentage(db, fiscal_year)
    da_rate = get_da_rate(db, fiscal_year)
    
    response = templates.TemplateResponse("schemes/s2053/subs/s20530387/budget_post_details_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "salary_mode": salary_mode,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "designations": DESIGNATIONS,
        "detail": detail,
        "resource_name": f"प्रपत्र ड संपादन (ID: {id})",
        "is_edit": True,
        "districts_mr": SCHEME_DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "designations_mr": DESIGNATIONS_MR,
        "auth_level": auth_level,
        "api_base_path": "/ui/s20530387/budget-post-details/api/post-levels",
        "pay_matrix_api_path": "/ui/s20530387/budget-post-details/api/pay-matrix",
        "sub_scheme_code": SUB_SCHEME_CODE,
        "table_name": "budget_post_details_20530387",
        "da_percentage": da_percentage,
        "da_rate": da_rate,
        "relative_years": get_relative_fiscal_years(fiscal_year)
    })
    response.headers.update(get_no_cache_headers())
    return response

@router.post("/{id}/edit", response_class=RedirectResponse)
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
    SpecialPay: Optional[int] = Form(None),
    BasicPay: Optional[float] = Form(None),
    GradePay: Optional[int] = Form(None),
    LocalSupplemetoryAllowance: Optional[int] = Form(None),
    VehicleAllowance: Optional[int] = Form(None),
    WashingAllowance: Optional[int] = Form(None),
    CashAllowance: Optional[int] = Form(None),
    FootWareAllowanceOther: Optional[int] = Form(None),
    HraRate: Optional[str] = Form('X'),
    Other: Optional[int] = Form(None)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
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
            "district": District,
            "category": Category,
            "class_type": Class,
            "designation": Designation,
            "sanctioned_posts_2024_25": SanctionedPosts202425,
            "sanctioned_posts_2025_26": SanctionedPosts202526,
            "special_pay": SpecialPay,
            "basic_pay": BasicPay,
            "grade_pay": GradePay,
            "local_supplementary_allowance": LocalSupplemetoryAllowance,
            "vehicle_allowance": VehicleAllowance,
            "washing_allowance": WashingAllowance,
            "cash_allowance": CashAllowance,
            "footwear_allowance_other": FootWareAllowanceOther,
            "hra_rate": HraRate
        }
        for key, value in update_dict.items():
            if value is not None and hasattr(db_detail, key):
                setattr(db_detail, key, value)
        
        AuditService.log_action(
            db=db,
            request=request,
            action='UPDATE',
            table_name=SCHEME_CONFIG.forms['budget_post_details'].table_name,
            record_id=id,
            old_values=original_values,
            new_values=AuditService.serialize_values(db_detail)
        )
        db.commit()
        invalidate_scheme_cache(db_detail.district)
        try:
            from src.routers.ui_taluka_selection import invalidate_district_status_cache
            scheme_code, _ = get_scheme_from_cookies(request)
            invalidate_district_status_cache(scheme_code, db_detail.fiscal_year)
        except Exception:
            pass
        return RedirectResponse(
            url=router.url_path_for("ui_list_budget_details") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        detail_for_form = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id).first()
        if detail_for_form:
            detail_for_form.basic_pay = _format_basic_pay(detail_for_form.basic_pay)
        
        return templates.TemplateResponse("schemes/s2053/subs/s20530387/budget_post_details_form.html", {
            "request": request,
            "error": f"रेकॉर्ड अपडेट करण्यात अयशस्वी: {e}",
            "districts": SCHEME_DISTRICTS,
            "categories": CATEGORIES,
            "classes": CLASSES_SHEET1_2,
            "designations": DESIGNATIONS,
            "detail": detail_for_form,
            "resource_name": f"प्रपत्र ड संपादन (ID: {id})",
            "is_edit": True,
            "districts_mr": SCHEME_DISTRICTS_MR,
            "categories_mr": CATEGORIES_MR,
            "classes_mr": CLASSES_MR,
            "designations_mr": DESIGNATIONS_MR,
            "auth_level": auth_level,
            "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
        }, status_code=400)

@router.get("/export-excel", response_class=StreamingResponse)
async def export_budget_details_excel(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    designation_search: Optional[str] = Query(None)
):
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
    return StreamingResponse(
        output,
        headers={'Content-Disposition': 'attachment; filename="budget_post_details.xlsx"'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.get("/export-original", response_class=StreamingResponse)
async def export_budget_details_original(
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
async def export_budget_details_sheet_only(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    """Export only budget post details sheet with throttling."""
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
        only_sheet="budget_post_details",
        user_district=user_district,
        sub_scheme_code=sub_scheme,
        fiscal_year=fiscal_year
    )

