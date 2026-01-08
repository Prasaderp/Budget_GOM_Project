"""UI controller for post status"""
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
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from ...config import (
    SCHEME_CONFIG, CATEGORIES, CLASSES_SHEET1_2, STATUSES,
    CATEGORIES_MR, CLASSES_MR, STATUSES_MR
)
from ...helpers import check_edit_permission_for_scheme
from ...shared.utils.response_utils import get_no_cache_headers
from ..repositories.post_status_repository import PostStatusRepository
from ..services.post_status_service import PostStatusService
from ..services.summary_service import PostStatusSummaryService
from ..services.export_service import PostStatusExportService
from src.utils_auth import get_auth_unit

templates.env.globals['zip'] = zip

router = APIRouter(
    prefix="/ui/s20530028/post-status",
    tags=["UI - प्रपत्र क"],
    include_in_schema=False
)


def get_post_status_service(db: Session = Depends(get_db)) -> PostStatusService:
    """Dependency to get PostStatusService"""
    return PostStatusService(db)


def get_summary_service(db: Session = Depends(get_db)) -> PostStatusSummaryService:
    """Dependency to get PostStatusSummaryService"""
    return PostStatusSummaryService(db)


def get_export_service(db: Session = Depends(get_db)) -> PostStatusExportService:
    """Dependency to get PostStatusExportService"""
    return PostStatusExportService(db)


@router.get("", response_class=HTMLResponse)
async def ui_list_post_status(
    request: Request,
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    service: PostStatusService = Depends(get_post_status_service),
    summary_service: PostStatusSummaryService = Depends(get_summary_service)
):
    """List post status (edit or summary view)"""
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    db = service.db

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
        if auth_level == 'district' and auth_unit:
            summary_data = summary_service.get_summary_data(fiscal_year, district=auth_unit)
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            summary_data = summary_service.get_summary_data(
                fiscal_year, district=district_name
            ) if district_name else None
        else:
            summary_data = summary_service.get_summary_data(fiscal_year)
        
        if not summary_data:
            raise HTTPException(
                status_code=500,
                detail="Could not generate Post Status summary data."
            )

        if auth_level == 'district' and auth_unit:
            labels = [auth_unit]
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            labels = [district_name] if district_name else []
        elif auth_level == 'dco':
            labels = DISTRICTS
        else:
            labels = REGULAR_DISTRICTS
        
        chart_data = summary_service.prepare_chart_data(summary_data, labels)

        context.update({
            "resource_name": "प्रपत्र क गोषवारा",
            "chart_data": chart_data,
            "chart_data_json": json.dumps(chart_data) if chart_data else "{}",
            "auth_unit": auth_unit
        })
        context.update(summary_data)
        response = templates.TemplateResponse(
            "schemes/s2053/subs/s20530028/post_status_list.html", context
        )
        response.headers.update(get_no_cache_headers())
        return response

    elif view == "edit":
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
        
        items, total_count = service.repository.get_by_filters(
            fiscal_year, sub_scheme, auth_level, auth_unit,
            district, category, cls, status_filter, page, page_size
        )
        
        filtered_params = {
            k: v for k, v in {
                "district": district, "category": category,
                "class": cls, "status": status_filter
            }.items() if v
        }
        context["export_query_string_list"] = (
            "?" + urlencode(filtered_params) if filtered_params else ""
        )
        context["items"] = items
        context["total_count"] = total_count
        context["page"] = page
        context["page_size"] = page_size
        context["chart_data"] = None
        context["can_edit"] = can_edit
        response = templates.TemplateResponse(
            "schemes/s2053/subs/s20530028/post_status_list.html", context
        )
        response.headers.update(get_no_cache_headers())
        return response

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid view parameter. Use 'edit' or 'summary'."
        )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_status_form(
    request: Request,
    id: int,
    service: PostStatusService = Depends(get_post_status_service)
):
    """Show edit form for post status"""
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = get_auth_unit(request)
    db = service.db
    
    is_allowed, timing_msg = check_data_filling_allowed(
        db, auth_level, auth_role, SCHEME_CONFIG.code
    )
    if not is_allowed and auth_role == 'assistant':
        raise HTTPException(
            status_code=403,
            detail=timing_msg or "Data filling period has expired"
        )
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    _, sub_scheme = get_scheme_from_cookies(request)
    item = service.get_by_id(id, sub_scheme)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"प्रपत्र क ID {id} सापडला नाही"
        )
    
    return templates.TemplateResponse("schemes/s2053/subs/s20530028/post_status_form.html", {
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
        "auth_level": auth_level
    })


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_post_status(
    request: Request,
    id: int,
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
    Other: Optional[int] = Form(None),
    service: PostStatusService = Depends(get_post_status_service)
):
    """Update post status record"""
    auth_role = request.cookies.get('auth_role') or ''
    auth_level = request.cookies.get('auth_level') or ''
    auth_unit = get_auth_unit(request) or ''
    db = service.db
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            raise HTTPException(status_code=403, detail="Taluka not allowed")
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(
                status_code=400,
                detail="Invalid district for taluka user"
            )
    
    is_allowed, timing_msg = check_data_filling_allowed(
        db, auth_level, auth_role, SCHEME_CONFIG.code
    )
    if not is_allowed:
        raise HTTPException(
            status_code=403,
            detail=timing_msg or "Data filling period has expired"
        )
    
    _, sub_scheme = get_scheme_from_cookies(request)
    db_item = service.get_by_id(id, sub_scheme)
    if not db_item:
        raise HTTPException(
            status_code=404,
            detail=f"प्रपत्र क ID {id} सापडला नाही"
        )
    
    try:
        service.update_record(
            db_item,
            district=District,
            category=Category,
            class_type=Class,
            status=Status,
            posts=Posts,
            salary=Salary,
            grade_pay=GradePay,
            special_pay=SpecialPay,
            dearness_allowance=DearnessAllowance,
            local_supplementary_allowance=LocalSupplemetoryAllowance,
            house_rent_allowance=HouseRentAllowance,
            travel_allowance=TravelAllowance,
            other=Other
        )
        return RedirectResponse(
            url=router.url_path_for("ui_list_post_status") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update Post Status ID {id}: {e}", exc_info=True)
        districts_for_filter = DISTRICTS
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        return templates.TemplateResponse(
            "schemes/s2053/subs/s20530028/post_status_form.html",
            {
                "request": request,
                "error": f"रेकॉर्ड अपडेट करण्यात अयशस्वी: {e}",
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
                "auth_level": auth_level
            },
            status_code=400
        )


@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_status_summary_excel(
    request: Request,
    export_service: PostStatusExportService = Depends(get_export_service)
):
    """Export post status summary to Excel"""
    db = export_service.db
    fiscal_year = get_fiscal_year_from_request(request, db)
    return export_service.export_summary_excel(fiscal_year)


@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_status_list_excel(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status"),
    export_service: PostStatusExportService = Depends(get_export_service)
):
    """Export post status list to Excel"""
    db = export_service.db
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    return export_service.export_list_excel(
        fiscal_year, sub_scheme, district, category, cls, status_filter
    )


@router.get("/export-original", response_class=StreamingResponse)
async def export_post_status_original(
    request: Request,
    district: Optional[str] = Query(None),
    export_service: PostStatusExportService = Depends(get_export_service)
):
    """Export original workbook template"""
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, export_service.db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return export_service.export_original_workbook(sub_scheme, user_district, fiscal_year)


@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_post_status_sheet_only(
    request: Request,
    district: Optional[str] = Query(None),
    export_service: PostStatusExportService = Depends(get_export_service)
):
    """Export only the post_status sheet from original workbook"""
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, export_service.db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return export_service.export_sheet_only(sub_scheme, user_district, fiscal_year)

