"""UI controller for unit expenditure"""
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
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
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

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20530028/unit-expenditure",
    tags=["UI - प्रपत्र अ"],
    include_in_schema=False
)


def get_unit_expenditure_service(db: Session = Depends(get_db)) -> UnitExpenditureService:
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
    summary_service: UnitExpenditureSummaryService = Depends(get_summary_service)
):
    """List unit expenditure (edit or summary view)"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    db = service.repository.session
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
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
        "relative_years": relative_years
    }
    
    if view == "summary":
        target_district = None
        if auth_level == 'district' and auth_unit:
            target_district = auth_unit
        elif auth_level == 'taluka' and auth_unit:
            target_district = get_district_from_taluka(auth_unit)
        
        data = summary_service.get_summary_and_charts(
            fiscal_year=fiscal_year,
            district=target_district,
            exclude_dco=(not target_district)
        )
        if not data.get("summary_rows"):
            raise HTTPException(status_code=500, detail="Could not generate summary data.")
        
        context.update({
            "resource_name": "प्रपत्र अ गोषवारा",
            "chart_data_json": json.dumps(data.get("charts", {})),
            "summary_rows": data["summary_rows"],
            "summary_totals": data["summary_totals"],
            "internal_keys_ordered": data["internal_keys_ordered"]
        })
        resp = templates.TemplateResponse("schemes/s2053/subs/s20530028/unit_expenditure_list.html", context)
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
            page_size=page_size
        )
        
        items, total_count = service.get_list(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            auth_level=auth_level,
            auth_unit=auth_unit,
            filters=filters
        )
        
        filtered_params = {k: v for k, v in {"district": district, "primary_unit": primary_unit}.items() if v}
        context.update({
            "export_query_string_list": "?" + urlencode(filtered_params) if filtered_params else "",
            "items": items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "can_edit": can_edit
        })
        resp = templates.TemplateResponse("schemes/s2053/subs/s20530028/unit_expenditure_list.html", context)
        resp.headers.update(get_no_cache_headers())
        return resp
    
    logger.warning(f"Invalid view: {view}")
    raise HTTPException(status_code=400, detail="Invalid view parameter")


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_unit_expenditure_form(
    request: Request,
    id: int,
    service: UnitExpenditureService = Depends(get_unit_expenditure_service)
):
    """Edit form for unit expenditure"""
    auth_level = get_auth_level(request)
    auth_role = get_auth_role(request)
    auth_unit = get_auth_unit(request)
    
    db = service.repository.session
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
    item = service.get_by_id(id, sub_scheme)
    if not item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र अ ID {id} सापडला नाही")

    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)

    return templates.TemplateResponse("schemes/s2053/subs/s20530028/unit_expenditure_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "primary_units": PRIMARY_UNITS,
        "item": item,
        "resource_name": "प्रपत्र अ संपादन",
        "districts_mr": DISTRICTS_MR,
        "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
        "auth_level": auth_level,
        "relative_years": relative_years
    })


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_unit_expenditure(
    request: Request,
    id: int,
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
    BudgetaryEstimates20252026FinanceDepartment: Optional[int] = Form(None),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service)
):
    """Update unit expenditure from form"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request) or ''
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    db = service.repository.session
    if auth_level == 'taluka' and auth_unit:
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    
    try:
        update_dto = UnitExpenditureFormUpdateDTO(
            id=id,
            unit_account=PrimaryAndSecondaryUnitsOfAccount,
            district=District,
            expenditure_2021_22=ActualAmountExpenditure20212022,
            expenditure_2022_23=ActualAmountExpenditure20222023,
            expenditure_2023_24=ActualAmountExpenditure20232024,
            budget_2024_25=BudgetaryEstimates20242025,
            forecast_2024_25=ImprovedForecast20242025,
            budget_2025_26_estimating_officer=BudgetaryEstimates20252026EstimatingOfficer,
            budget_2025_26_controlling_officer=BudgetaryEstimates20252026ControllingOfficer,
            budget_2025_26_admin_dept=BudgetaryEstimates20252026AdministrativeDepartment,
            budget_2025_26_finance_dept=BudgetaryEstimates20252026FinanceDepartment
        )
        
        service.update_form(
            request=request,
            update_dto=update_dto,
            sub_scheme_code=sub_scheme,
            auth_role=auth_role,
            auth_level=auth_level,
            auth_unit=auth_unit
        )
        
        return RedirectResponse(
            url=router.url_path_for("ui_list_unit_expenditure") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        db.rollback()
        logger.error(f"Failed to update ID {id}: {e}", exc_info=True)
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        
        db_item = service.get_by_id(id, sub_scheme)
        return templates.TemplateResponse("schemes/s2053/subs/s20530028/unit_expenditure_form.html", {
            "request": request,
            "error": "अपडेट अयशस्वी. कृपया पुन्हा प्रयत्न करा.",
            "districts": districts_for_filter,
            "primary_units": PRIMARY_UNITS,
            "item": db_item,
            "resource_name": "प्रपत्र अ संपादन",
            "districts_mr": DISTRICTS_MR,
            "unit_account_map_mr": UNIT_ACCOUNT_MAP_MR,
            "auth_level": auth_level
        }, status_code=400)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update ID {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/summary/export-excel", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
async def export_unit_expenditure_summary_excel(
    request: Request,
    export_service: UnitExpenditureExportService = Depends(get_export_service)
):
    """Export summary data to Excel"""
    try:
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_summary_excel(fiscal_year=fiscal_year)
    except Exception as e:
        logger.error(f"Failed to export summary Excel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/list/export-excel", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
async def export_unit_expenditure_list_excel(
    request: Request,
    district: Optional[str] = Query(None),
    primary_unit: Optional[str] = Query(None),
    export_service: UnitExpenditureExportService = Depends(get_export_service)
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
            primary_unit=primary_unit
        )
    except Exception as e:
        logger.error(f"Failed to export list Excel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/export-original", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
async def export_unit_expenditure_original(
    request: Request,
    district: Optional[str] = Query(None),
    export_service: UnitExpenditureExportService = Depends(get_export_service)
):
    """Export original workbook template"""
    try:
        auth_level = get_auth_level(request)
        auth_unit = get_auth_unit(request)
        user_district = auth_unit if auth_level == 'district' else (
            district if auth_level in ('dco', 'officer1', 'officer2') else None
        )
        _, sub_scheme = get_scheme_from_cookies(request)
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_original_workbook(
            db=db,
            user_district=user_district,
            sub_scheme_code=sub_scheme,
            fiscal_year=fiscal_year
        )
    except Exception as e:
        logger.error(f"Failed to export original workbook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/export-sheet-only", response_class=StreamingResponse, dependencies=[Depends(verify_api_auth)])
async def export_unit_expenditure_sheet_only(
    request: Request,
    district: Optional[str] = Query(None),
    export_service: UnitExpenditureExportService = Depends(get_export_service)
):
    """Export only unit expenditure sheet from original workbook"""
    try:
        auth_level = get_auth_level(request)
        auth_unit = get_auth_unit(request)
        user_district = auth_unit if auth_level == 'district' else (
            district if auth_level in ('dco', 'officer1', 'officer2') else None
        )
        _, sub_scheme = get_scheme_from_cookies(request)
        db = export_service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        return export_service.export_original_workbook(
            db=db,
            user_district=user_district,
            sub_scheme_code=sub_scheme,
            only_sheet="unit_expenditure",
            fiscal_year=fiscal_year
        )
    except Exception as e:
        logger.error(f"Failed to export sheet only: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

