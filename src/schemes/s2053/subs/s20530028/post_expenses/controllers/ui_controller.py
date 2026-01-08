"""UI controller for post expenses"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import urlencode
import json
import logging

from src.database import get_db
from src.core.templates import templates
from src.config import DISTRICTS, REGULAR_DISTRICTS, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from ...config import (
    SCHEME_CONFIG, CATEGORIES, CLASSES_SHEET3,
    POST_EXPENSES_DISTRICT_COMPONENT,
    CATEGORIES_MR, CLASSES_SHEET3_MR
)
from ...helpers import check_edit_permission_for_scheme
from ...shared.services.cache_service import CacheService
from ...shared.services.audit_service import AuditService
from ...shared.utils.response_utils import get_no_cache_headers
from ..repositories.post_expenses_repository import PostExpensesRepository
from ..services.post_expenses_service import PostExpensesService
from ..services.summary_service import PostExpensesSummaryService
from ..services.charts_service import PostExpensesChartsService
from ..services.export_service import PostExpensesExportService
from ..services.nps_component_service import NPSComponentService
from ..dto.filter_dto import PostExpensesFilterDTO
from ..dto.post_expenses_dto import PostExpensesFormUpdateDTO
from ..utils.validators import validate_nps_value
from src.utils_auth import get_auth_unit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20530028/post-expenses",
    tags=["UI - प्रपत्र ब"],
    include_in_schema=False
)


def get_post_expenses_service(db: Session = Depends(get_db)) -> PostExpensesService:
    """Dependency to get post expenses service"""
    repository = PostExpensesRepository(db)
    return PostExpensesService(repository)


def get_summary_service(db: Session = Depends(get_db)) -> PostExpensesSummaryService:
    """Dependency to get summary service"""
    repository = PostExpensesRepository(db)
    return PostExpensesSummaryService(repository)


def get_charts_service(db: Session = Depends(get_db)) -> PostExpensesChartsService:
    """Dependency to get charts service"""
    repository = PostExpensesRepository(db)
    return PostExpensesChartsService(repository)


def get_export_service(db: Session = Depends(get_db)) -> PostExpensesExportService:
    """Dependency to get export service"""
    repository = PostExpensesRepository(db)
    summary_service = PostExpensesSummaryService(repository)
    return PostExpensesExportService(repository, summary_service)


@router.get("", response_class=HTMLResponse)
async def ui_list_post_expenses(
    request: Request,
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    service: PostExpensesService = Depends(get_post_expenses_service),
    summary_service: PostExpensesSummaryService = Depends(get_summary_service),
    charts_service: PostExpensesChartsService = Depends(get_charts_service)
):
    """List post expenses (edit or summary view)"""
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    fiscal_year = get_fiscal_year_from_request(request, db)
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    context = {
        "request": request,
        "resource_name": "प्रपत्र ब",
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET3,
        "current_district": district,
        "current_category": category,
        "current_class": cls,
        "view_mode": view,
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_sheet3_mr": CLASSES_SHEET3_MR,
        "auth_level": auth_level,
        "auth_unit": auth_unit
    }
    
    if view == "summary":
        if auth_level == 'district' and auth_unit:
            summary_data = summary_service.get_summary_data(fiscal_year, district=auth_unit)
            charts_data = charts_service.get_charts_data(fiscal_year, district=auth_unit)
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            if district_name:
                summary_data = summary_service.get_summary_data(fiscal_year, district=district_name)
                charts_data = charts_service.get_charts_data(fiscal_year, district=district_name)
            else:
                summary_data = None
                charts_data = {}
        else:
            summary_data = summary_service.get_summary_data(fiscal_year)
            charts_data = charts_service.get_charts_data(fiscal_year)
        
        if not summary_data:
            raise HTTPException(status_code=500, detail="Could not generate Post Expenses summary data.")
        
        context.update({
            "resource_name": "प्रपत्र ब गोषवारा",
            "chart_data_json": json.dumps(charts_data)
        })
        context.update(summary_data)
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response
    
    elif view == "edit":
        _, sub_scheme = get_scheme_from_cookies(request)
        
        # Create filter DTO
        filters = PostExpensesFilterDTO(
            district=district,
            category=category,
            class_type=cls,
            page=page,
            page_size=page_size
        )
        
        # Get list
        items, total_count = service.get_list(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            auth_level=auth_level,
            auth_unit=auth_unit,
            filters=filters
        )
        
        filtered_params = {k: v for k, v in {
            "district": district,
            "category": category,
            "class": cls
        }.items() if v}
        
        context.update({
            "export_query_string_list": "?" + urlencode(filtered_params) if filtered_params else "",
            "items": items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "can_edit": can_edit
        })
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response
    
    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_expense_form(
    request: Request,
    id: int,
    service: PostExpensesService = Depends(get_post_expenses_service)
):
    """Show edit form for post expense"""
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed and auth_role == 'assistant':
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    item = service.get_by_id(id, sub_scheme)
    if not item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र ब ID {id} सापडला नाही")
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    # Get NPS value using NPS component service
    nps_value = NPSComponentService.get_nps_value(item)
    
    return templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET3,
        "item": item,
        "resource_name": "प्रपत्र ब संपादन",
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_sheet3_mr": CLASSES_SHEET3_MR,
        "auth_level": auth_level,
        "nps_value": nps_value,
    })


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_post_expense(
    request: Request,
    id: int,
    Class: str = Form(...),
    Category: str = Form(...),
    District: str = Form(...),
    FilledPosts: Optional[int] = Form(None),
    VacantPosts: Optional[int] = Form(None),
    MedicalExpenses: Optional[int] = Form(None),
    FestivalAdvance: Optional[int] = Form(None),
    SwagramMaharashtraDarshan: Optional[int] = Form(None),
    Other: Optional[int] = Form(None),
    NPSUnified: Optional[str] = Form(None),
    service: PostExpensesService = Depends(get_post_expenses_service)
):
    """Update post expense via form"""
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            raise HTTPException(status_code=403, detail="Taluka not allowed")
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    
    try:
        # Get existing record
        db_item = service.get_by_id(id, sub_scheme)
        if not db_item:
            raise HTTPException(status_code=404, detail=f"प्रपत्र ब ID {id} सापडला नाही")
        
        # Validate and convert NPS value
        is_valid, nps_float, error_msg = validate_nps_value(NPSUnified)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Create update DTO
        update_dto = PostExpensesFormUpdateDTO(
            district=District,
            category=Category,
            class_type=Class,
            filled_posts=FilledPosts,
            vacant_posts=VacantPosts,
            medical_expenses=MedicalExpenses,
            festival_advance=FestivalAdvance,
            swagram_maharashtra_darshan=SwagramMaharashtraDarshan,
            other=Other,
            nps_unified=nps_float
        )
        
        # Update record
        service.update_form(id, sub_scheme, update_dto)
        
        # Log audit
        AuditService.log_action(
            db=db,
            request=request,
            action='UPDATE',
            table_name=SCHEME_CONFIG.forms['post_expenses'].table_name,
            record_id=id,
            old_values=AuditService.serialize_values(db_item),
            new_values=AuditService.serialize_values(db_item)
        )
        
        # Invalidate cache
        CacheService.invalidate_scheme_cache(db_item.district)
        
        logger.info(f"Successfully updated Post Expense ID {id}")
        return RedirectResponse(
            url=router.url_path_for("ui_list_post_expenses") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as ve:
        db.rollback()
        logger.error(f"Invalid input during update for Post Expense ID {id}: {ve}")
        db_item_reloaded = service.get_by_id(id, sub_scheme)
        active_component = NPSComponentService.get_active_component(
            db_item_reloaded.district if db_item_reloaded else None
        )
        districts_for_filter = DISTRICTS
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        return templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_form.html", {
            "request": request,
            "error": f"Failed to update: {ve}",
            "districts": districts_for_filter,
            "categories": CATEGORIES,
            "classes": CLASSES_SHEET3,
            "item": db_item_reloaded,
            "resource_name": "प्रपत्र ब संपादन",
            "active_component": active_component,
            "districts_mr": DISTRICTS_MR,
            "categories_mr": CATEGORIES_MR,
            "classes_sheet3_mr": CLASSES_SHEET3_MR,
            "auth_level": auth_level
        }, status_code=400)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update Post Expense ID {id}: {e}", exc_info=True)
        db_item_reloaded = service.get_by_id(id, sub_scheme)
        active_component = NPSComponentService.get_active_component(
            db_item_reloaded.district if db_item_reloaded else None
        )
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        return templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_form.html", {
            "request": request,
            "error": f"Failed to update record: {e}",
            "districts": districts_for_filter,
            "categories": CATEGORIES,
            "classes": CLASSES_SHEET3,
            "item": db_item_reloaded,
            "resource_name": "प्रपत्र ब संपादन",
            "active_component": active_component,
            "districts_mr": DISTRICTS_MR,
            "categories_mr": CATEGORIES_MR,
            "classes_sheet3_mr": CLASSES_SHEET3_MR,
            "auth_level": auth_level
        }, status_code=500)


@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_expenses_summary_excel(
    request: Request,
    export_service: PostExpensesExportService = Depends(get_export_service)
):
    """Export post expenses summary to Excel"""
    try:
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_summary_excel(fiscal_year=fiscal_year)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_expenses_list_excel(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    export_service: PostExpensesExportService = Depends(get_export_service)
):
    """Export post expenses list to Excel"""
    try:
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        return export_service.export_list_excel(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            category=category,
            class_type=cls
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-original", response_class=StreamingResponse)
async def export_post_expenses_original(
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
    repository = PostExpensesRepository(db)
    summary_service = PostExpensesSummaryService(repository)
    export_service = PostExpensesExportService(repository, summary_service)
    return export_service.export_original_workbook(
        db, user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year
    )


@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_post_expenses_sheet_only(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Export only post expenses sheet"""
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    repository = PostExpensesRepository(db)
    summary_service = PostExpensesSummaryService(repository)
    export_service = PostExpensesExportService(repository, summary_service)
    return export_service.export_original_workbook(
        db, only_sheet="post_expenses", user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year
    )

