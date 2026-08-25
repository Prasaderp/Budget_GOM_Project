"""UI controller for post expenses"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import urlencode
import json
import logging

from src.database import get_db
from src.core.templates import render
from src.config import DISTRICTS, REGULAR_DISTRICTS, DISTRICTS_MR
from src.utils_district import get_district_from_taluka
from src.utils_fiscal_year import (
    get_fiscal_year_from_request,
    get_relative_fiscal_years,
)
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from ...config import (
    SCHEME_CONFIG,
    CATEGORIES,
    CLASSES_SHEET3,
    CATEGORIES_MR,
    CLASSES_SHEET3_MR,
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
from src.utils_auth import verify_api_auth, get_auth_level, get_auth_role, get_auth_unit
from src.core.taluka.write import (
    resolve_editable_row,
    strip_protected_update_fields,
    writable_scope,
)
from src.core.taluka.consolidation import consolidate_row
from src.core.taluka.models import natural_key_columns
from ...models import PostExpenses
from ...derivation import acquire_derivation_locks, derive_for_row

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20530028/post-expenses", tags=["UI - प्रपत्र ब"], include_in_schema=False
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
    charts_service: PostExpensesChartsService = Depends(get_charts_service),
):
    """List post expenses (edit or summary view)"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    fiscal_year = get_fiscal_year_from_request(request, db)
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)

    if auth_level == "district" and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == "dco":
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
        "auth_unit": auth_unit,
    }

    if view == "summary":
        if auth_level == "district" and auth_unit:
            summary_data = summary_service.get_summary_data(
                fiscal_year, district=auth_unit
            )
            charts_data = charts_service.get_charts_data(
                fiscal_year, district=auth_unit
            )
        elif auth_level == "taluka" and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            if district_name:
                summary_data = summary_service.get_summary_data(
                    fiscal_year, district=district_name
                )
                charts_data = charts_service.get_charts_data(
                    fiscal_year, district=district_name
                )
            else:
                summary_data = None
                charts_data = {}
        else:
            summary_data = summary_service.get_summary_data(fiscal_year)
            charts_data = charts_service.get_charts_data(fiscal_year)

        if not summary_data:
            raise HTTPException(
                status_code=500, detail="Could not generate Post Expenses summary data."
            )

        context.update(
            {
                "resource_name": "प्रपत्र ब गोषवारा",
                "chart_data_json": json.dumps(charts_data),
                "relative_years": get_relative_fiscal_years(fiscal_year),
            }
        )
        context.update(summary_data)
        response = render(
            request, "schemes/s2053/subs/s20530028/post_expenses_list.html", context
        )
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
            page_size=page_size,
        )

        # Get list
        items, total_count = service.get_list(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            auth_level=auth_level,
            auth_unit=auth_unit,
            filters=filters,
        )

        filtered_params = {
            k: v
            for k, v in {
                "district": district,
                "category": category,
                "class": cls,
            }.items()
            if v
        }

        context.update(
            {
                "export_query_string_list": "?" + urlencode(filtered_params)
                if filtered_params
                else "",
                "items": items,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "can_edit": can_edit,
            }
        )
        response = render(
            request, "schemes/s2053/subs/s20530028/post_expenses_list.html", context
        )
        response.headers.update(get_no_cache_headers())
        return response

    else:
        raise HTTPException(
            status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'."
        )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_expense_form(
    request: Request,
    id: int,
    service: PostExpensesService = Depends(get_post_expenses_service),
):
    """Show edit form for post expense"""
    auth_level = get_auth_level(request)
    auth_role = get_auth_role(request)
    auth_unit = get_auth_unit(request)
    db = service.repository.session

    is_allowed, timing_msg = check_data_filling_allowed(
        db, auth_level, auth_role, SCHEME_CONFIG.code
    )
    if not is_allowed and auth_role == "assistant":
        raise HTTPException(
            status_code=403, detail=timing_msg or "Data filling period has expired"
        )

    _, sub_scheme = get_scheme_from_cookies(request)
    item = resolve_editable_row(db, PostExpenses, id, request)
    if item.sub_scheme_code != sub_scheme:
        raise HTTPException(status_code=404, detail=f"प्रपत्र ब ID {id} सापडला नाही")

    if auth_level == "district" and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == "dco":
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS

    # Get NPS value using NPS component service
    nps_value = NPSComponentService.get_nps_value(item)

    return render(
        request,
        "schemes/s2053/subs/s20530028/post_expenses_form.html",
        {
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
        },
    )


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
    service: PostExpensesService = Depends(get_post_expenses_service),
):
    """Update post expense via form"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    db = service.repository.session

    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    is_allowed, timing_msg = check_data_filling_allowed(
        db, auth_level, auth_role, SCHEME_CONFIG.code
    )
    if not is_allowed:
        raise HTTPException(
            status_code=403, detail=timing_msg or "Data filling period has expired"
        )

    _, sub_scheme = get_scheme_from_cookies(request)

    try:
        db_item = resolve_editable_row(db, PostExpenses, id, request)
        if db_item.sub_scheme_code != sub_scheme:
            raise HTTPException(status_code=404, detail=f"प्रपत्र ब ID {id} सापडला नाही")
        fans_out = any(
            value is not None
            for value in (
                MedicalExpenses,
                FestivalAdvance,
                SwagramMaharashtraDarshan,
                Other,
                NPSUnified,
            )
        )
        lock_categories = sorted(CATEGORIES if fans_out else (db_item.category,))
        for category in lock_categories:
            acquire_derivation_locks(
                db, db_item.district, db_item.fiscal_year, category
            )

        is_valid, nps_float, error_msg = validate_nps_value(NPSUnified)
        if not is_valid:
            raise ValueError(error_msg)

        original_values = AuditService.serialize_values(db_item)

        update_data = strip_protected_update_fields(
            PostExpenses,
            {
                "district": District,
                "category": Category,
                "class_type": Class,
                "filled_posts": FilledPosts,
                "medical_expenses": MedicalExpenses,
                "festival_advance": FestivalAdvance,
                "swagram_maharashtra_darshan": SwagramMaharashtraDarshan,
                "other": Other,
                "nps_unified": nps_float,
            },
        )
        update_dto = PostExpensesFormUpdateDTO(
            district=db_item.district,
            category=db_item.category,
            class_type=db_item.class_type,
            **update_data,
        )

        # writable_scope() pins the read filter to db_item's own taluka for
        # this call only, so the service's internal re-query by id finds the
        # row resolve_editable_row() already resolved (C2).
        with writable_scope(db_item):
            db_item, sync_update = service.update_form(db_item.id, sub_scheme, update_dto)

        affected = [db_item]
        if sync_update:
            visible_rows = db.query(PostExpenses).filter(
                PostExpenses.district == db_item.district,
                PostExpenses.fiscal_year == db_item.fiscal_year,
                PostExpenses.sub_scheme_code == sub_scheme,
            ).order_by(PostExpenses.category, PostExpenses.class_type).all()
            affected_by_id = {db_item.id: db_item}
            for row in visible_rows:
                writable_row = resolve_editable_row(db, PostExpenses, row.id, request)
                affected_by_id[writable_row.id] = writable_row
            affected = sorted(
                affected_by_id.values(),
                key=lambda row: (row.category, row.class_type),
            )
            for row in affected:
                for field, value in sync_update.items():
                    setattr(row, field, value)

        # Log audit before commit -- log_action() only flushes; a row added
        # after the final commit is discarded when the session closes.
        AuditService.log_action(
            db=db,
            request=request,
            action="UPDATE",
            table_name=SCHEME_CONFIG.forms["post_expenses"].table_name,
            record_id=id,
            old_values=original_values,
            new_values=AuditService.serialize_values(db_item),
        )

        db.flush()
        for row in affected:
            consolidate_row(
                db,
                PostExpenses,
                row.district,
                row.fiscal_year,
                {c: getattr(row, c) for c in natural_key_columns(PostExpenses)},
            )

        derive_for_row(db, db_item, request)

        db.commit()

        CacheService.invalidate_scheme_cache(db_item.district)

        return RedirectResponse(
            url=router.url_path_for("ui_list_post_expenses") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except HTTPException as e:
        db.rollback()
        if e.status_code != 400:
            raise
        db_item_reloaded = service.get_by_id(id, sub_scheme)
        nps_value = (
            NPSComponentService.get_nps_value(db_item_reloaded)
            if db_item_reloaded
            else None
        )
        active_component = NPSComponentService.get_active_component(
            db_item_reloaded.district if db_item_reloaded else None
        )
        districts_for_filter = DISTRICTS
        if auth_level == "district" and auth_unit:
            districts_for_filter = [auth_unit]
        return render(
            request,
            "schemes/s2053/subs/s20530028/post_expenses_form.html",
            {
                "request": request,
                "error": e.detail,
                "districts": districts_for_filter,
                "categories": CATEGORIES,
                "classes": CLASSES_SHEET3,
                "item": db_item_reloaded,
                "resource_name": "प्रपत्र ब संपादन",
                "active_component": active_component,
                "nps_value": nps_value,
                "districts_mr": DISTRICTS_MR,
                "categories_mr": CATEGORIES_MR,
                "classes_sheet3_mr": CLASSES_SHEET3_MR,
                "auth_level": auth_level,
            },
            status_code=400,
        )
    except ValueError as ve:
        db.rollback()
        logger.error(f"Invalid input during update for Post Expense ID {id}: {ve}")
        db_item_reloaded = service.get_by_id(id, sub_scheme)
        nps_value = (
            NPSComponentService.get_nps_value(db_item_reloaded)
            if db_item_reloaded
            else None
        )
        active_component = NPSComponentService.get_active_component(
            db_item_reloaded.district if db_item_reloaded else None
        )
        districts_for_filter = DISTRICTS
        if auth_level == "district" and auth_unit:
            districts_for_filter = [auth_unit]
        return render(
            request,
            "schemes/s2053/subs/s20530028/post_expenses_form.html",
            {
                "request": request,
                "error": f"Failed to update: {ve}",
                "districts": districts_for_filter,
                "categories": CATEGORIES,
                "classes": CLASSES_SHEET3,
                "item": db_item_reloaded,
                "resource_name": "प्रपत्र ब संपादन",
                "active_component": active_component,
                "nps_value": nps_value,
                "districts_mr": DISTRICTS_MR,
                "categories_mr": CATEGORIES_MR,
                "classes_sheet3_mr": CLASSES_SHEET3_MR,
                "auth_level": auth_level,
            },
            status_code=400,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update Post Expense ID {id}: {e}", exc_info=True)
        db_item_reloaded = service.get_by_id(id, sub_scheme)
        nps_value = (
            NPSComponentService.get_nps_value(db_item_reloaded)
            if db_item_reloaded
            else None
        )
        active_component = NPSComponentService.get_active_component(
            db_item_reloaded.district if db_item_reloaded else None
        )
        if auth_level == "district" and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == "dco":
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        return render(
            request,
            "schemes/s2053/subs/s20530028/post_expenses_form.html",
            {
                "request": request,
                "error": "Failed to update record. Please try again.",
                "districts": districts_for_filter,
                "categories": CATEGORIES,
                "classes": CLASSES_SHEET3,
                "item": db_item_reloaded,
                "resource_name": "प्रपत्र ब संपादन",
                "active_component": active_component,
                "nps_value": nps_value,
                "districts_mr": DISTRICTS_MR,
                "categories_mr": CATEGORIES_MR,
                "classes_sheet3_mr": CLASSES_SHEET3_MR,
                "auth_level": auth_level,
            },
            status_code=500,
        )


@router.get(
    "/summary/export-excel",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_post_expenses_summary_excel(
    request: Request,
    export_service: PostExpensesExportService = Depends(get_export_service),
):
    """Export post expenses summary to Excel"""
    try:
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_summary_excel(fiscal_year=fiscal_year)
    except Exception as e:
        import logging

        logging.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.get(
    "/list/export-excel",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_post_expenses_list_excel(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    export_service: PostExpensesExportService = Depends(get_export_service),
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
            class_type=cls,
        )
    except Exception as e:
        import logging

        logging.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.get(
    "/export-original",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_post_expenses_original(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export original workbook"""
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == "district":
        user_district = auth_unit
    elif auth_level in ("dco", "officer1", "officer2") and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    repository = PostExpensesRepository(db)
    summary_service = PostExpensesSummaryService(repository)
    export_service = PostExpensesExportService(repository, summary_service)
    return export_service.export_original_workbook(
        db,
        user_district=user_district,
        sub_scheme_code=sub_scheme,
        fiscal_year=fiscal_year,
    )


@router.get(
    "/export-sheet-only",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_post_expenses_sheet_only(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export only post expenses sheet"""
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == "district":
        user_district = auth_unit
    elif auth_level in ("dco", "officer1", "officer2") and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    repository = PostExpensesRepository(db)
    summary_service = PostExpensesSummaryService(repository)
    export_service = PostExpensesExportService(repository, summary_service)
    return export_service.export_original_workbook(
        db,
        only_sheet="post_expenses",
        user_district=user_district,
        sub_scheme_code=sub_scheme,
        fiscal_year=fiscal_year,
    )
