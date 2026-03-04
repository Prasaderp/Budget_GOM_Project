"""UI routes for sub-scheme 76100149 district-wise expenditure."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import DISTRICTS_MR
from src.database import get_db
from src.core.templates import templates
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.schemes.s7610.fiscal_year_labels import FiscalYearLabels7610
from .models import DistrictExpenditure76100149, SUB_SCHEME_CODE
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    validate_access_control,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)
from src.utils_auth import (
    get_auth_unit,
    get_auth_level,
    get_auth_role,
    get_auth_user,
    is_authenticated
)

router = APIRouter(
    prefix="/ui/s76100149/district-expenditure",
    tags=["UI - 76100149 जिल्हानिहाय खर्च"],
    include_in_schema=False,
)


@router.get("", response_class=HTMLResponse)
async def ui_list_district_expenditure(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if not allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if district and district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid district selection")

    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    query = (
        db.query(DistrictExpenditure76100149)
        .filter(
            DistrictExpenditure76100149.fiscal_year == fiscal_year,
            DistrictExpenditure76100149.sub_scheme_code == SUB_SCHEME_CODE,
        )
    )

    if district:
        query = query.filter(DistrictExpenditure76100149.district == district)
    else:
        query = query.filter(DistrictExpenditure76100149.district.in_(allowed_districts))

    total_count = query.with_entities(func.count(DistrictExpenditure76100149.id)).scalar()
    items = (
        query.order_by(DistrictExpenditure76100149.district)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)

    fy_labels = FiscalYearLabels7610(get_relative_fiscal_years(fiscal_year))

    context = {
        "request": request,
        "items": items,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "districts": allowed_districts,
        "current_district": district,
        "can_edit": can_edit,
        "resource_name": "76100149 जिल्हानिहाय खर्च",
        "districts_mr": DISTRICTS_MR,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "fy_labels": fy_labels,
    }

    return templates.TemplateResponse(
        "schemes/s7610/subs/s76100149/district_expenditure_list.html",
        context,
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_district_expenditure_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    item = (
        db.query(DistrictExpenditure76100149)
        .filter(
            DistrictExpenditure76100149.id == id,
            DistrictExpenditure76100149.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    auth_role = get_auth_role(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    fy_labels = FiscalYearLabels7610(get_relative_fiscal_years(fiscal_year))

    context = {
        "request": request,
        "item": item,
        "districts": allowed_districts,
        "resource_name": "76100149 जिल्हानिहाय खर्च संपादन",
        "districts_mr": DISTRICTS_MR,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "fy_labels": fy_labels,
    }
    return templates.TemplateResponse(
        "schemes/s7610/subs/s76100149/district_expenditure_form.html",
        context,
    )


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    from src.utils_timing import check_data_filling_allowed

    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request) or ""

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=timing_msg or "Data filling period has expired")

    item = (
        db.query(DistrictExpenditure76100149)
        .filter(
            DistrictExpenditure76100149.id == id,
            DistrictExpenditure76100149.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    form = await request.form()
    district = form.get("District")

    if not district or district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    if district != item.district:
        existing = (
            db.query(DistrictExpenditure76100149)
            .filter(
                DistrictExpenditure76100149.fiscal_year == item.fiscal_year,
                DistrictExpenditure76100149.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure76100149.district == district,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Record already exists for this district and fiscal year",
            )

    old_vals = {
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }

    item.district = district
    item.expenditure_prev3 = validate_numeric_input(form.get("ExpenditurePrev3"), "ExpenditurePrev3")
    item.expenditure_prev2 = validate_numeric_input(form.get("ExpenditurePrev2"), "ExpenditurePrev2")
    item.expenditure_prev1 = validate_numeric_input(form.get("ExpenditurePrev1"), "ExpenditurePrev1")
    item.budget_estimate = validate_numeric_input(form.get("BudgetEstimate"), "BudgetEstimate")
    item.revised_estimate = validate_numeric_input(form.get("RevisedEstimate"), "RevisedEstimate")
    item.budget_estimate_next = validate_numeric_input(form.get("BudgetEstimateNext"), "BudgetEstimateNext")
    item.remarks = (form.get("Remarks") or "").strip() or None

    new_vals = {
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }

    db.commit()
    db.refresh(item)

    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_76100149",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE"
    )

    return RedirectResponse(
        url=router.url_path_for("ui_list_district_expenditure"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/export")
async def ui_export_excel(
    request: Request,
    db: Session = Depends(get_db),
):
    """Export unified 7610 budget data (all 4 sub-schemas) to Excel.
    
    This exports data from ALL sub-schemas:
    - 76100149: घरबांधणी अग्रिमे
    - 76100158: मोटार वाहनांच्या खरेदीसाठी अग्रिमे
    - 76100167: इतर वाहनांच्या खरेदीसाठी अग्रिमे
    - 76101871: वैयक्तीक संगणक यंत्रे खरेदीसाठी अग्रिमे
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    from src.schemes.s7610 import export_7610_workbook_async
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    return await export_7610_workbook_async(db, fiscal_year)

