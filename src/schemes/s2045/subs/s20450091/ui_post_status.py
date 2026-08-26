"""UI routes for post status (Form C) - sub-scheme 20450091"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from collections import defaultdict
import json
import logging
import pandas as pd
import io

from src.database import get_db
from src.core.templates import render, templates
from src.core.ui_redirects import redirect_after_update
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.utils_scheme import get_scheme_from_cookies
from src.utils_cache import ttl_cache
from src.utils_timing import check_data_filling_allowed
from .excel_export import export_original_workbook_async
from src.audit_service import AuditService
from src.schemes.s2045.common.services.post_status_service import PostStatusService
from src.schemes.s2045.common.utils.constants import (
    CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY, VALID_CLASS_KEYS,
    CLASS_MAPPING, METRICS_DB_KEYS, METRICS_LABELS, CLASS_MR_MAP
)
from .models import PostStatus
from src.core.taluka.consolidation import consolidate_row
from src.core.taluka.models import natural_key_columns
from src.core.taluka.write import resolve_editable_row
from .config import (
    SCHEME_CONFIG, CATEGORIES, CLASSES_SHEET1_2, STATUSES,
    CATEGORIES_MR, CLASSES_MR, STATUSES_MR
)
from .helpers import (
    check_edit_permission_for_scheme, validate_access_control,
    validate_numeric_inputs, get_no_cache_headers
)
from src.utils_auth import get_auth_unit, get_auth_role, get_auth_level, get_auth_user, is_authenticated

templates.env.globals['zip'] = zip

router = APIRouter(
    prefix="/ui/s20450091/post-status",
    tags=["UI - प्रपत्र क"],
    include_in_schema=False
)

logger = logging.getLogger(__name__)

_post_status_service = PostStatusService(post_status_model=PostStatus)


@router.get("/api/statuses", response_class=JSONResponse)
async def api_get_statuses(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    db: Session = Depends(get_db)
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(PostStatus.status).distinct().filter(
        PostStatus.fiscal_year == fiscal_year,
        PostStatus.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(PostStatus.district == district)
    if category:
        query = query.filter(PostStatus.category == category)
    if cls:
        query = query.filter(PostStatus.class_type == cls)
    statuses = [row[0] for row in query.order_by(PostStatus.status).all()]
    return JSONResponse({"statuses": statuses})

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(
    request: Request,
    district: str = Query(...),
    category: str = Query(...),
    cls: str = Query(..., alias="class"),
    status: str = Query(...),
    db: Session = Depends(get_db)
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(PostStatus).filter(
        PostStatus.fiscal_year == fiscal_year,
        PostStatus.sub_scheme_code == sub_scheme,
        PostStatus.district == district,
        PostStatus.category == category,
        PostStatus.class_type == cls,
        PostStatus.status == status
    ).first()
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True, "id": record.id,
        "posts": record.posts or 0,
        "salary": record.salary or 0,
        "grade_pay": record.grade_pay or 0,
        "special_pay": record.special_pay or 0,
        "dearness_allowance": record.dearness_allowance or 0,
        "local_supplementary_allowance": record.local_supplementary_allowance or 0,
        "house_rent_allowance": record.house_rent_allowance or 0,
        "travel_allowance": record.travel_allowance or 0,
        "other": record.other or 0
    })

@router.post("/api/update-inline", response_class=JSONResponse)
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    Posts: int = Form(0),
    Salary: int = Form(0),
    GradePay: int = Form(0),
    SpecialPay: int = Form(0),
    DearnessAllowance: int = Form(0),
    LocalSupplemetoryAllowance: int = Form(0),
    HouseRentAllowance: int = Form(0),
    TravelAllowance: int = Form(0),
    Other: int = Form(0)
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
    record = resolve_editable_row(db, PostStatus, id, request)
    if record.sub_scheme_code != sub_scheme:
        raise HTTPException(status_code=404, detail="Not found")
    
    allowed, error_msg = validate_access_control(record.district, auth_level, auth_unit, db)
    if not allowed:
        return JSONResponse({"success": False, "message": error_msg}, status_code=403)
    
    values_to_check = [Posts, Salary, GradePay, SpecialPay, DearnessAllowance, LocalSupplemetoryAllowance, HouseRentAllowance, TravelAllowance, Other]
    is_valid, error_msg = validate_numeric_inputs(*values_to_check)
    if not is_valid:
        return JSONResponse({"success": False, "message": error_msg}, status_code=400)
    
    old_values = {
        "posts": record.posts, "salary": record.salary, "grade_pay": record.grade_pay,
        "special_pay": record.special_pay, "dearness_allowance": record.dearness_allowance,
        "local_supplementary_allowance": record.local_supplementary_allowance,
        "house_rent_allowance": record.house_rent_allowance,
        "travel_allowance": record.travel_allowance, "other": record.other
    }
    
    record.posts = Posts
    record.salary = Salary
    record.grade_pay = GradePay
    record.special_pay = SpecialPay
    record.dearness_allowance = DearnessAllowance
    record.local_supplementary_allowance = LocalSupplemetoryAllowance
    record.house_rent_allowance = HouseRentAllowance
    record.travel_allowance = TravelAllowance
    record.other = Other
    
    new_values = {
        "posts": Posts, "salary": Salary, "grade_pay": GradePay, "special_pay": SpecialPay,
        "dearness_allowance": DearnessAllowance, "local_supplementary_allowance": LocalSupplemetoryAllowance,
        "house_rent_allowance": HouseRentAllowance, "travel_allowance": TravelAllowance, "other": Other
    }
    
    try:
        AuditService.log_action(
            db=db,
            request=request,
            action='UPDATE',
            table_name=SCHEME_CONFIG.forms['post_status'].table_name,
            record_id=id,
            old_values=old_values,
            new_values=new_values
        )
    except Exception:
        pass
    
    db.flush()
    keys = natural_key_columns(PostStatus)
    consolidate_row(db, PostStatus, record.district, record.fiscal_year, {key: getattr(record, key) for key in keys})
    db.commit()
    try:
        from src.routers.ui_taluka_selection import invalidate_district_status_cache
        scheme_code, _ = get_scheme_from_cookies(request)
        invalidate_district_status_cache(scheme_code, record.fiscal_year)
    except Exception:
        pass
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})

@router.get("", response_class=HTMLResponse)
async def ui_list_post_status(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status"),
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
        "resource_name": "प्रपत्र क",
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "statuses": STATUSES,
        "current_district": district,
        "current_category": category,
        "current_class": cls,
        "current_status": status_filter,
        "view_mode": view,
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "statuses_mr": STATUSES_MR,
        "auth_level": auth_level
    }

    if view == "summary":
        fiscal_year = get_fiscal_year_from_request(request, db)
        relative_years = get_relative_fiscal_years(fiscal_year)
        context["relative_years"] = relative_years
        _, sub_scheme = get_scheme_from_cookies(request)
        if not sub_scheme:
            raise HTTPException(status_code=400, detail="Subscheme not specified")
        if auth_level == 'district' and auth_unit:
            summary_data = _post_status_service.get_post_status_summary_data(
                db=db, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year, district=auth_unit
            )
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            summary_data = _post_status_service.get_post_status_summary_data(
                db=db, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year, district=district_name
            ) if district_name else None
        else:
            summary_data = _post_status_service.get_post_status_summary_data(
                db=db, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year
            )
        
        if not summary_data:
            raise HTTPException(status_code=500, detail="Could not generate Post Status summary data.")

        district_summary = summary_data.get('district_summary', {})
        
        if auth_level == 'district' and auth_unit:
            labels = [auth_unit]
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            labels = [district_name] if district_name else []
        elif auth_level == 'dco':
            labels = DISTRICTS
        else:
            labels = REGULAR_DISTRICTS
        
        chart_data = {}
        try:
            dist_filled = []
            dist_vacant = []
            dist_cost = []
            dist_salary = []
            dist_grade = []
            dist_special = []
            dist_allowances = []
            for d in labels:
                ds = district_summary.get(d, {})
                dcomp = summary_data.get('district_components_sums', {}).get(d, {})
                dist_filled.append(int(ds.get('Filled', {}).get('Posts', 0) or 0))
                dist_vacant.append(int(ds.get('Vacant', {}).get('Posts', 0) or 0))
                dist_cost.append(int(ds.get('TotalCost', 0) or 0))
                dist_salary.append(int(dcomp.get('Salary', 0) or 0))
                dist_grade.append(int(dcomp.get('GradePay', 0) or 0))
                dist_special.append(int(dcomp.get('SpecialPay', 0) or 0))
                dist_allowances.append(int(dcomp.get('Allowances', 0) or 0))
            
            if not any(v > 0 for v in dist_filled + dist_vacant + dist_cost + dist_salary + dist_grade + dist_special + dist_allowances):
                dyn_labels = list(district_summary.keys())
                dist_filled = [int((district_summary.get(d, {}).get('Filled', {}) or {}).get('Posts', 0) or 0) for d in dyn_labels]
                dist_vacant = [int((district_summary.get(d, {}).get('Vacant', {}) or {}).get('Posts', 0) or 0) for d in dyn_labels]
                dist_cost = [int((district_summary.get(d, {}) or {}).get('TotalCost', 0) or 0) for d in dyn_labels]
                dist_salary = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('Salary', 0) or 0) for d in dyn_labels]
                dist_grade = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('GradePay', 0) or 0) for d in dyn_labels]
                dist_special = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('SpecialPay', 0) or 0) for d in dyn_labels]
                dist_allowances = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('Allowances', 0) or 0) for d in dyn_labels]
                labels = dyn_labels

            if labels:
                chart_data['district_posts_by_status'] = {'labels': labels, 'भरलेली': dist_filled, 'रिक्त': dist_vacant}
                chart_data['district_total_cost'] = {'labels': labels, 'values': dist_cost}
                chart_data['district_allowance_breakdown'] = {
                    'labels': labels,
                    'Salary': dist_salary,
                    'GradePay': dist_grade,
                    'SpecialPay': dist_special,
                    'Allowances': dist_allowances
                }
                
                dcmap = summary_data.get('district_category_posts', {})
                chart_data['district_category_posts'] = {
                    'labels': labels,
                    'Permanent': [int((dcmap.get(d, {}) or {}).get('Permanent', 0) or 0) for d in labels],
                    'Temporary': [int((dcmap.get(d, {}) or {}).get('Temporary', 0) or 0) for d in labels]
                }

        except Exception as e:
            logger.error(f"Error preparing chart data for Post Status: {e}", exc_info=True)
            chart_data = {}

        context.update({
            "resource_name": "प्रपत्र क गोषवारा",
            "chart_data": chart_data,
            "chart_data_json": json.dumps(chart_data) if chart_data else "{}",
            "auth_unit": auth_unit
        })
        context.update(summary_data)
        response = render(request, "schemes/s2045/subs/s20450091/post_status_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response

    elif view == "edit":
        fiscal_year = get_fiscal_year_from_request(request, db)
        relative_years = get_relative_fiscal_years(fiscal_year)
        _, sub_scheme = get_scheme_from_cookies(request)
        can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
        query = build_district_filter(db.query(PostStatus), auth_level, auth_unit, PostStatus).filter(
            PostStatus.fiscal_year == fiscal_year,
            PostStatus.sub_scheme_code == sub_scheme
        )
        
        if district:
            query = query.filter(PostStatus.district == district)
        if category:
            query = query.filter(PostStatus.category == category)
        if cls:
            query = query.filter(PostStatus.class_type == cls)
        if status_filter:
            query = query.filter(PostStatus.status == status_filter)
        
        total_count = query.with_entities(func.count()).scalar()
        items = query.order_by(PostStatus.id).offset((page - 1) * page_size).limit(page_size).all()
        
        filtered_params = {k: v for k, v in {"district": district, "category": category, "class": cls, "status": status_filter}.items() if v}
        context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""
        context["items"] = items
        context["total_count"] = total_count
        context["page"] = page
        context["page_size"] = page_size
        context["chart_data"] = None
        context["can_edit"] = can_edit
        context["relative_years"] = relative_years
        response = render(request, "schemes/s2045/subs/s20450091/post_status_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response

    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")

@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_status_form(request: Request, id: int, db: Session = Depends(get_db)):
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
    item = resolve_editable_row(db, PostStatus, id, request)
    if item.sub_scheme_code != sub_scheme:
        raise HTTPException(status_code=404, detail="Not found")
    
    from src.utils_district import validate_access_control
    is_allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Access denied")
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)

    return render(request, "schemes/s2045/subs/s20450091/post_status_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "statuses": STATUSES,
        "item": item,
        "resource_name": "प्रपत्र क संपादन",
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "statuses_mr": STATUSES_MR,
        "auth_level": auth_level,
        "relative_years": relative_years
    })

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_post_status(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    District: str = Form(...),
    Category: str = Form(...),
    Class: str = Form(...),
    Status: str = Form(...),
    Posts: Optional[int] = Form(None),
    Salary: Optional[int] = Form(None),
    GradePay: Optional[int] = Form(None),
    SpecialPay: Optional[int] = Form(None),
    DearnessAllowance: Optional[int] = Form(None),
    LocalSupplemetoryAllowance: Optional[int] = Form(None),
    HouseRentAllowance: Optional[int] = Form(None),
    TravelAllowance: Optional[int] = Form(None),
    Other: Optional[int] = Form(None)
):
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    
    if District not in DISTRICTS and District != DCO_STAFF_IDENTIFIER:
        raise HTTPException(status_code=400, detail="Invalid district")
    if Category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    if Class not in CLASSES_SHEET1_2:
        raise HTTPException(status_code=400, detail="Invalid class")
    if Status not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    db_item = resolve_editable_row(db, PostStatus, id, request)
    if db_item.sub_scheme_code != sub_scheme:
        raise HTTPException(status_code=404, detail="Not found")
    
    try:
        # Capture original values for audit logging
        original_values = AuditService.serialize_values(db_item)
        
        update_dict = {
            "district": District, "category": Category, "class_type": Class, "status": Status,
            "posts": Posts, "salary": Salary, "grade_pay": GradePay, "special_pay": SpecialPay,
            "dearness_allowance": DearnessAllowance, "local_supplementary_allowance": LocalSupplemetoryAllowance,
            "house_rent_allowance": HouseRentAllowance, "travel_allowance": TravelAllowance, "other": Other
        }
        for key, value in update_dict.items():
            if value is not None and hasattr(db_item, key):
                setattr(db_item, key, value)
        
        # Log audit trail before committing
        AuditService.log_action(
            db=db,
            request=request,
            action='UPDATE',
            table_name=SCHEME_CONFIG.forms['post_status'].table_name,
            record_id=id,
            old_values=original_values,
            new_values=AuditService.serialize_values(db_item)
        )
        
        db.flush()
        keys = natural_key_columns(PostStatus)
        consolidate_row(db, PostStatus, db_item.district, db_item.fiscal_year, {key: getattr(db_item, key) for key in keys})
        db.commit()
        db.refresh(db_item)
        try:
            from src.routers.ui_taluka_selection import invalidate_district_status_cache
            scheme_code, _ = get_scheme_from_cookies(request)
            invalidate_district_status_cache(scheme_code, db_item.fiscal_year)
        except Exception:
            pass
        return redirect_after_update(request)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update Post Status ID {id}: {e}", exc_info=True)
        districts_for_filter = DISTRICTS
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        return render(request, "schemes/s2045/subs/s20450091/post_status_form.html", {
            "request": request,
            "error": "रेकॉर्ड अपडेट करण्यात अयशस्वी: कृपया पुन्हा प्रयत्न करा.",
            "districts": districts_for_filter,
            "categories": CATEGORIES,
            "classes": CLASSES_SHEET1_2,
            "statuses": STATUSES,
            "item": db_item,
            "resource_name": "प्रपत्र क संपादन",
            "districts_mr": DISTRICTS_MR,
            "categories_mr": CATEGORIES_MR,
            "classes_mr": CLASSES_MR,
            "statuses_mr": STATUSES_MR,
            "auth_level": auth_level,
            "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
        }, status_code=400)

@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_status_summary_excel(request: Request, db: Session = Depends(get_db)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    if not sub_scheme:
        raise HTTPException(status_code=400, detail="Subscheme not specified")
    summary_data = _post_status_service.get_post_status_summary_data(
        db=db, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year
    )
    if summary_data is None:
        raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            CLASS_KEYS_ORDER = ['वर्ग-1 व 2', 'वर्ग-3', 'वर्ग-4', 'एकूण']
            METRICS_ORDER_COMP = summary_data.get('comparison_metrics_keys', [])
            
            perm_rows_df = pd.DataFrame(summary_data['permanent_metric_rows'])
            cols_perm = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']
            perm_rows_df = perm_rows_df[cols_perm]
            perm_rows_df.to_excel(writer, sheet_name='Permanent Posts Summary', index=False)
            
            temp_rows_df = pd.DataFrame(summary_data['temporary_metric_rows'])
            cols_temp = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']
            temp_rows_df = temp_rows_df[cols_temp]
            temp_rows_df.to_excel(writer, sheet_name='Temporary Posts Summary', index=False)
            
            comp_df = pd.DataFrame(summary_data['comparison_summary'])
            if METRICS_ORDER_COMP:
                comp_df = comp_df[['वर्ग'] + METRICS_ORDER_COMP]
            comp_df.to_excel(writer, sheet_name='Overall Comparison', index=False)
            
            final_sum_df = pd.DataFrame(summary_data['final_class_summary_table'])
            final_sum_df = final_sum_df[['CategoryLabel', 'ClassKey', 'Amt', 'Post']]
            final_sum_df.columns = ['Category', 'Class', 'Amount', 'Posts']
            final_sum_df.to_excel(writer, sheet_name='Final Class Summary', index=False)
        
        output.seek(0)
        headers = {'Content-Disposition': 'attachment; filename="post_status_summary_report.xlsx"'}
        return StreamingResponse(
            output,
            headers=headers,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Failed to generate Post Status Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not generate Excel file. Please try again.")

@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_status_list_excel(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status")
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(PostStatus).filter(
        PostStatus.fiscal_year == fiscal_year,
        PostStatus.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(PostStatus.district == district)
    if category:
        query = query.filter(PostStatus.category == category)
    if cls:
        query = query.filter(PostStatus.class_type == cls)
    if status_filter:
        query = query.filter(PostStatus.status == status_filter)
    
    items = query.order_by(PostStatus.id).all()
    data_dict_list = []
    if items:
        columns = [c.name for c in PostStatus.__table__.columns]
        for item in items:
            data_dict_list.append({col: getattr(item, col, None) for col in columns})
    
    df = pd.DataFrame(data_dict_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Post Status List', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="post_status_list.xlsx"'}
    return StreamingResponse(
        output,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.get("/export-original", response_class=StreamingResponse)
async def export_post_status_original(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str]  = Query(None)
):
    """Export original Excel workbook with production-grade throttling."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    auth_level = get_auth_level(request)
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
async def export_post_status_sheet_only(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    """Export only post_status sheet with throttling."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    auth_level = get_auth_level(request)
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
        only_sheet="post_status",
        user_district=user_district,
        sub_scheme_code=sub_scheme,
        fiscal_year=fiscal_year
    )
