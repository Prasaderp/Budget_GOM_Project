"""UI controller for budget post details"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import urlencode
import json

from src.database import get_db
from src.core.templates import templates
from src.config import DISTRICTS, REGULAR_DISTRICTS, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_da_rate import get_da_percentage, get_da_rate
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from ...excel_export import export_original_workbook
from src.audit_service import AuditService
from ...config import (
    SCHEME_CONFIG, CATEGORIES, CLASSES_SHEET1_2, DESIGNATIONS,
    CATEGORIES_MR, CLASSES_MR, DESIGNATIONS_MR
)
from ...helpers import check_edit_permission_for_scheme
from ...shared.services.cache_service import CacheService
from ...shared.utils.request_utils import get_request_info
from ...shared.utils.response_utils import get_no_cache_headers
from ..repositories.budget_post_repository import BudgetPostRepository
from ..services.budget_post_service import BudgetPostService
from ..services.export_service import ExportService
from ..services.designation_service import DesignationService
from ..dto.filter_dto import BudgetPostFilterDTO
from ..dto.budget_post_dto import BudgetPostFormUpdateDTO
from ..utils.formatters import format_basic_pay
from ...ui_budget_summary import get_budget_summary_data, get_district_budget_summary_data
from src.utils_auth import get_auth_unit

router = APIRouter(
    prefix="/ui/s20530028/budget-post-details",
    tags=["UI - प्रपत्र ड"],
    include_in_schema=False
)


def get_budget_post_service(db: Session = Depends(get_db)) -> BudgetPostService:
    """Dependency to get budget post service"""
    repository = BudgetPostRepository(db)
    return BudgetPostService(repository)


def get_export_service(db: Session = Depends(get_db)) -> ExportService:
    """Dependency to get export service"""
    repository = BudgetPostRepository(db)
    return ExportService(repository)




@router.get("", response_class=HTMLResponse)
async def ui_list_budget_details(
    request: Request,
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    designation_search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    service: BudgetPostService = Depends(get_budget_post_service)
):
    """List budget post details (edit or summary view)"""
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    fiscal_year = get_fiscal_year_from_request(request, db)
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
    da_rate = get_da_rate(db, fiscal_year)

    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    context = {
        "request": request,
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "current_district": district,
        "current_category": category,
        "current_class": cls,
        "current_designation_search": designation_search,
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "designations_mr": DESIGNATIONS_MR,
        "auth_level": auth_level,
        "da_rate": da_rate
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
            "resource_name": "प्रपत्र ड गोषवारा",
            "view_mode": "summary",
            "auth_unit": auth_unit,
            "chart_data_summary_json": json.dumps(chart_data)
        })
        context.update(summary_data)
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response

    elif view == "edit":
        _, sub_scheme = get_scheme_from_cookies(request)
        
        # Translate designation search if provided
        translated_search = None
        if designation_search:
            translated_search = DesignationService.translate_marathi_designation_search(designation_search)
        
        # Create filter DTO
        filters = BudgetPostFilterDTO(
            district=district,
            category=category,
            class_type=cls,
            designation_search=translated_search,
            page=page,
            page_size=page_size
        )
        
        # Get list
        details, total_count = service.get_list(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            auth_level=auth_level,
            auth_unit=auth_unit,
            filters=filters
        )

        filtered_params = {k: v for k, v in {
            "district": district,
            "category": category,
            "class": cls,
            "designation_search": designation_search
        }.items() if v}
        
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
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response

    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter")


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_budget_detail_form(
    request: Request,
    id: int,
    service: BudgetPostService = Depends(get_budget_post_service)
):
    """Show edit form for budget post detail"""
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    
    if auth_role == 'assistant':
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
        if not is_allowed:
            raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    detail = service.get_by_id(id, sub_scheme)
    if not detail:
        raise HTTPException(status_code=404, detail=f"प्रपत्र ड ID {id} सापडला नाही")
    
    detail.basic_pay = format_basic_pay(detail.basic_pay)
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    from src.utils_salary_mode import get_salary_mode
    salary_mode = get_salary_mode(db, fiscal_year)
    da_percentage = get_da_percentage(db, fiscal_year)
    da_rate = get_da_rate(db, fiscal_year)
    
    response = templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "designations": DESIGNATIONS,
        "detail": detail,
        "resource_name": f"प्रपत्र ड संपादन (ID: {id})",
        "is_edit": True,
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "designations_mr": DESIGNATIONS_MR,
        "auth_level": auth_level,
        "salary_mode": salary_mode,
        "da_percentage": da_percentage,
        "da_rate": da_rate
    })
    response.headers.update(get_no_cache_headers())
    return response


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_budget_detail(
    request: Request,
    id: int,
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
    Other: Optional[int] = Form(None),
    service: BudgetPostService = Depends(get_budget_post_service)
):
    """Update budget post detail via form"""
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit) or District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=403, detail="Invalid access")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    
    try:
        # Get existing record
        db_detail = service.get_by_id(id, sub_scheme)
        if not db_detail:
            raise HTTPException(status_code=404, detail=f"प्रपत्र ड ID {id} सापडला नाही")
        
        # Serialize old values for audit
        original_values = AuditService.serialize_values(db_detail)
        
        # Create update DTO
        update_dto = BudgetPostFormUpdateDTO(
            district=District,
            category=Category,
            class_type=Class,
            designation=Designation,
            sanctioned_posts_2024_25=SanctionedPosts202425,
            sanctioned_posts_2025_26=SanctionedPosts202526,
            special_pay=SpecialPay,
            basic_pay=BasicPay,
            grade_pay=GradePay,
            local_supplementary_allowance=LocalSupplemetoryAllowance,
            vehicle_allowance=VehicleAllowance,
            washing_allowance=WashingAllowance,
            cash_allowance=CashAllowance,
            footwear_allowance_other=FootWareAllowanceOther,
            hra_rate=HraRate
        )
        
        # Update record
        service.update_form(id, sub_scheme, update_dto)
        
        # Log audit
        AuditService.log_action(
            db=db,
            request=request,
            action='UPDATE',
            table_name=SCHEME_CONFIG.forms['budget_post_details'].table_name,
            record_id=id,
            old_values=original_values,
            new_values=AuditService.serialize_values(db_detail)
        )
        
        # Invalidate cache
        CacheService.invalidate_scheme_cache(db_detail.district)
        
        return RedirectResponse(
            url=router.url_path_for("ui_list_budget_details") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        db.rollback()
        detail_for_form = service.get_by_id(id, sub_scheme)
        if detail_for_form:
            detail_for_form.basic_pay = format_basic_pay(detail_for_form.basic_pay)
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        
        return templates.TemplateResponse("schemes/s2053/subs/s20530028/budget_post_details_form.html", {
            "request": request,
            "error": f"रेकॉर्ड अपडेट करण्यात अयशस्वी: {e}",
            "districts": districts_for_filter,
            "categories": CATEGORIES,
            "classes": CLASSES_SHEET1_2,
            "designations": DESIGNATIONS,
            "detail": detail_for_form,
            "resource_name": f"प्रपत्र ड संपादन (ID: {id})",
            "is_edit": True,
            "districts_mr": DISTRICTS_MR,
            "categories_mr": CATEGORIES_MR,
            "classes_mr": CLASSES_MR,
            "designations_mr": DESIGNATIONS_MR,
            "auth_level": auth_level
        }, status_code=400)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-excel", response_class=StreamingResponse)
async def export_budget_details_excel(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    designation_search: Optional[str] = Query(None),
    export_service: ExportService = Depends(get_export_service)
):
    """Export budget post details to Excel"""
    try:
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        
        # Translate designation search if provided
        translated_search = None
        if designation_search:
            translated_search = DesignationService.translate_marathi_designation_search(designation_search)
        
        return export_service.export_to_excel(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            category=category,
            class_type=cls,
            designation_search=translated_search
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-original", response_class=StreamingResponse)
async def export_budget_details_original(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Export original workbook"""
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return export_original_workbook(db, user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year)


@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_budget_details_sheet_only(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Export only budget post details sheet"""
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return export_original_workbook(
        db,
        only_sheet="budget_post_details",
        user_district=user_district,
        sub_scheme_code=sub_scheme,
        fiscal_year=fiscal_year
    )

