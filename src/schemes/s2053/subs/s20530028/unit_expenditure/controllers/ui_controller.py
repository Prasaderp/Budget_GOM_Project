"""UI controller for unit expenditure"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import urlencode
import json
import logging

from src.database import get_db
from src.core.templates import render
from src.core.ui_redirects import redirect_after_update
from src.config import DISTRICTS, REGULAR_DISTRICTS, DISTRICTS_MR
from src.utils_district import get_district_from_taluka
from src.utils_fiscal_year import (
    get_fiscal_year_from_request,
    get_relative_fiscal_years,
)
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from ...config import SCHEME_CONFIG, PRIMARY_UNITS, UNIT_ACCOUNT_MAP_MR
from ...helpers import check_edit_permission_for_scheme
from ...shared.utils.response_utils import get_no_cache_headers
from ..repositories.unit_expenditure_repository import UnitExpenditureRepository
from ..services.unit_expenditure_service import UnitExpenditureService
from ..services.summary_service import UnitExpenditureSummaryService
from ..services.export_service import UnitExpenditureExportService
from ..dto.filter_dto import UnitExpenditureFilterDTO
from ..dto.unit_expenditure_dto import UnitExpenditureFormUpdateDTO
from src.utils_auth import verify_api_auth, get_auth_level, get_auth_role, get_auth_unit
from src.core.taluka.write import (
    resolve_editable_row,
    strip_protected_update_fields,
    writable_scope,
)
from src.core.taluka.consolidation import consolidate_row
from src.core.taluka.models import natural_key_columns
from src.audit_service import AuditService
from ...helpers import invalidate_scheme_cache
from ...models import UnitExpenditure

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20530028/unit-expenditure",
    tags=["UI - प्रपत्र अ"],
    include_in_schema=False,
)


def get_unit_expenditure_service(
    db: Session = Depends(get_db),
) -> UnitExpenditureService:
    """Dependency to get unit expenditure service"""
    repository = UnitExpenditureRepository(db)
    return UnitExpenditureService(repository)


def get_summary_service(db: Session = Depends(get_db)) -> UnitExpenditureSummaryService:
    """Dependency to get summary service"""
    repository = UnitExpenditureRepository(db)
    return UnitExpenditureSummaryService(repository)


def get_export_service(db: Session = Depends(get_db)) -> UnitExpenditureExportService:
    """Dependency to get export service"""
    repository = UnitExpenditureRepository(db)
    summary_service = UnitExpenditureSummaryService(repository)
    return UnitExpenditureExportService(repository, summary_service)


@router.get("", response_class=HTMLResponse)
async def ui_list_unit_expenditure(
    request: Request,
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service),
    summary_service: UnitExpenditureSummaryService = Depends(get_summary_service),
):
    """List unit expenditure (edit or summary view)"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)

    if auth_level == "district" and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == "dco":
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS

    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)

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
        "auth_unit": auth_unit,
        "relative_years": relative_years,
    }

    if view == "summary":
        target_district = None
        if auth_level == "district" and auth_unit:
            target_district = auth_unit
        elif auth_level == "taluka" and auth_unit:
            target_district = get_district_from_taluka(auth_unit)

        try:
            data = summary_service.get_summary_and_charts(
                fiscal_year=fiscal_year,
                district=target_district,
                exclude_dco=(not target_district),
            )
        except Exception as exc:
            logger.error(f"Unit expenditure summary failed: {exc}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Could not generate summary data."
            )

        context.update(
            {
                "resource_name": "प्रपत्र अ गोषवारा",
                "chart_data_json": json.dumps(data.get("charts", {})),
                "summary_rows": data.get("summary_rows", []),
                "summary_totals": data.get("summary_totals", {}),
                "internal_keys_ordered": data.get("internal_keys_ordered", []),
            }
        )
        resp = render(
            request, "schemes/s2053/subs/s20530028/unit_expenditure_list.html", context
        )
        resp.headers.update(get_no_cache_headers())
        return resp

    elif view == "edit":
        _, sub_scheme = get_scheme_from_cookies(request)

        filters = UnitExpenditureFilterDTO(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            primary_unit=primary_unit,
            page=page,
            page_size=page_size,
        )

        items, total_count = service.get_list(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            auth_level=auth_level,
            auth_unit=auth_unit,
            filters=filters,
        )

        filtered_params = {
            k: v
            for k, v in {"district": district, "primary_unit": primary_unit}.items()
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
        resp = render(
            request, "schemes/s2053/subs/s20530028/unit_expenditure_list.html", context
        )
        resp.headers.update(get_no_cache_headers())
        return resp

    logger.warning(f"Invalid view: {view}")
    raise HTTPException(status_code=400, detail="Invalid view parameter")


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_unit_expenditure_form(
    request: Request,
    id: int,
    service: UnitExpenditureService = Depends(get_unit_expenditure_service),
):
    """Edit form for unit expenditure"""
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

    if auth_level == "district" and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == "dco":
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS

    _, sub_scheme = get_scheme_from_cookies(request)
    item = resolve_editable_row(db, UnitExpenditure, id, request)
    if item.sub_scheme_code != sub_scheme:
        raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")

    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)

    return render(
        request,
        "schemes/s2053/subs/s20530028/unit_expenditure_form.html",
        {
            "request": request,
            "districts": districts_for_filter,
            "primary_units": PRIMARY_UNITS,
            "item": item,
            "resource_name": "प्रपत्र अ संपादन",
            "districts_mr": DISTRICTS_MR,
            "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
            "auth_level": auth_level,
            "relative_years": relative_years,
        },
    )


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_unit_expenditure(
    request: Request,
    id: int,
    PrimaryAndSecondaryUnitsOfAccount: str = Form(...),
    District: str = Form(...),
    ExpenditurePrev4: Optional[int] = Form(None),
    ExpenditurePrev3: Optional[int] = Form(None),
    ExpenditurePrev2: Optional[int] = Form(None),
    BudgetPrev1: Optional[int] = Form(None),
    ForecastPrev1: Optional[int] = Form(None),
    BudgetCurrEstimatingOfficer: Optional[int] = Form(None),
    BudgetCurrControllingOfficer: Optional[int] = Form(None),
    BudgetCurrAdminDept: Optional[int] = Form(None),
    BudgetCurrFinanceDept: Optional[int] = Form(None),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service),
):
    """Update unit expenditure from form"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request) or ""

    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")

    db = service.repository.session
    is_allowed, timing_msg = check_data_filling_allowed(
        db, auth_level, auth_role, SCHEME_CONFIG.code
    )
    if not is_allowed:
        raise HTTPException(
            status_code=403, detail=timing_msg or "Data filling period has expired"
        )

    _, sub_scheme = get_scheme_from_cookies(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)

    try:
        db_item = resolve_editable_row(db, UnitExpenditure, id, request)
        if db_item.sub_scheme_code != sub_scheme:
            raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")
        original_values = AuditService.serialize_values(db_item)
        update_data = strip_protected_update_fields(
            UnitExpenditure,
            {
                "unit_account": PrimaryAndSecondaryUnitsOfAccount,
                "district": District,
                "expenditure_prev4": ExpenditurePrev4,
                "expenditure_prev3": ExpenditurePrev3,
                "expenditure_prev2": ExpenditurePrev2,
                "budget_prev1": BudgetPrev1,
                "forecast_prev1": ForecastPrev1,
                "budget_curr_estimating_officer": BudgetCurrEstimatingOfficer,
                "budget_curr_controlling_officer": BudgetCurrControllingOfficer,
                "budget_curr_admin_dept": BudgetCurrAdminDept,
                "budget_curr_finance_dept": BudgetCurrFinanceDept,
            },
        )
        update_dto = UnitExpenditureFormUpdateDTO(
            id=db_item.id,
            unit_account=db_item.unit_account,
            district=db_item.district,
            **update_data,
        )

        # writable_scope() pins the read filter to db_item's own taluka for
        # this call only, so the service's internal re-query by id finds the
        # row resolve_editable_row() already resolved (C2).
        with writable_scope(db_item):
            service.update_form(
                update_dto=update_dto,
                sub_scheme_code=sub_scheme,
                auth_role=auth_role,
                auth_level=auth_level,
                auth_unit=auth_unit,
            )
        AuditService.log_action(
            db=db,
            request=request,
            action="UPDATE",
            table_name=SCHEME_CONFIG.forms["unit_expenditure"].table_name,
            record_id=id,
            old_values=original_values,
            new_values=AuditService.serialize_values(db_item),
        )
        db.flush()
        consolidate_row(
            db,
            UnitExpenditure,
            db_item.district,
            db_item.fiscal_year,
            {c: getattr(db_item, c) for c in natural_key_columns(UnitExpenditure)},
        )
        db.commit()
        invalidate_scheme_cache(
            db_item.district, patterns=["unit_exp_summary", "unit_exp_charts"]
        )

        return redirect_after_update(request)
    except HTTPException as e:
        db.rollback()
        if e.status_code != 400:
            raise
        if auth_level == "district" and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == "dco":
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS

        db_item = service.get_by_id(id, sub_scheme)
        return render(
            request,
            "schemes/s2053/subs/s20530028/unit_expenditure_form.html",
            {
                "request": request,
                "error": e.detail,
                "districts": districts_for_filter,
                "primary_units": PRIMARY_UNITS,
                "item": db_item,
                "resource_name": "प्रपत्र अ संपादन",
                "districts_mr": DISTRICTS_MR,
                "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
                "auth_level": auth_level,
                "relative_years": relative_years,
            },
            status_code=400,
        )
    except ValueError as e:
        db.rollback()
        logger.error(f"Failed to update ID {id}: {e}", exc_info=True)
        if auth_level == "district" and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == "dco":
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS

        db_item = service.get_by_id(id, sub_scheme)
        return render(
            request,
            "schemes/s2053/subs/s20530028/unit_expenditure_form.html",
            {
                "request": request,
                "error": "अपडेट अयशस्वी. कृपया पुन्हा प्रयत्न करा.",
                "districts": districts_for_filter,
                "primary_units": PRIMARY_UNITS,
                "item": db_item,
                "resource_name": "प्रपत्र अ संपादन",
                "districts_mr": DISTRICTS_MR,
                "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
                "auth_level": auth_level,
                "relative_years": relative_years,
            },
            status_code=400,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update ID {id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.get(
    "/summary/export-excel",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_unit_expenditure_summary_excel(
    request: Request,
    export_service: UnitExpenditureExportService = Depends(get_export_service),
):
    """Export summary data to Excel"""
    try:
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_summary_excel(fiscal_year=fiscal_year)
    except Exception as e:
        logger.error(f"Failed to export summary Excel: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.get(
    "/list/export-excel",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_unit_expenditure_list_excel(
    request: Request,
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None),
    export_service: UnitExpenditureExportService = Depends(get_export_service),
):
    """Export list data to Excel"""
    try:
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        return export_service.export_list_excel(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            primary_unit=primary_unit,
        )
    except Exception as e:
        logger.error(f"Failed to export list Excel: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.get(
    "/export-original",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_unit_expenditure_original(
    request: Request,
    district: Optional[str] = Query(None),
    export_service: UnitExpenditureExportService = Depends(get_export_service),
):
    """Export original workbook template"""
    try:
        auth_level = get_auth_level(request)
        auth_unit = get_auth_unit(request)
        user_district = (
            auth_unit
            if auth_level == "district"
            else (district if auth_level in ("dco", "officer1", "officer2") else None)
        )
        _, sub_scheme = get_scheme_from_cookies(request)
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_original_workbook(
            db=db,
            user_district=user_district,
            sub_scheme_code=sub_scheme,
            fiscal_year=fiscal_year,
        )
    except Exception as e:
        logger.error(f"Failed to export original workbook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.get(
    "/export-sheet-only",
    response_class=StreamingResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def export_unit_expenditure_sheet_only(
    request: Request,
    district: Optional[str] = Query(None),
    export_service: UnitExpenditureExportService = Depends(get_export_service),
):
    """Export only unit expenditure sheet from original workbook"""
    try:
        auth_level = get_auth_level(request)
        auth_unit = get_auth_unit(request)
        user_district = (
            auth_unit
            if auth_level == "district"
            else (district if auth_level in ("dco", "officer1", "officer2") else None)
        )
        _, sub_scheme = get_scheme_from_cookies(request)
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_original_workbook(
            db=db,
            user_district=user_district,
            sub_scheme_code=sub_scheme,
            only_sheet="unit_expenditure",
            fiscal_year=fiscal_year,
        )
    except Exception as e:
        logger.error(f"Failed to export sheet only: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )
