"""UI routes for sub-scheme 22350311 district-wise expenditure."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import DISTRICTS_MR
from src.database import get_db
from src.core.templates import render
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.schemes.s2235.fiscal_year_labels import FiscalYearLabels2235
from .models import DistrictExpenditure22350311, SUB_SCHEME_CODE
from .config import KONKAN_DISTRICTS
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    validate_access_control,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)
from src.utils_auth import is_authenticated, get_auth_role, get_auth_level, get_auth_user, get_auth_unit

router = APIRouter(
    prefix="/ui/s22350311/district-expenditure",
    tags=["UI - 22350311 सामाजिक सुरक्षा व कल्याण"],
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

    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2235(relative_years)

    query = (
        db.query(DistrictExpenditure22350311)
        .filter(
            DistrictExpenditure22350311.fiscal_year == fiscal_year,
            DistrictExpenditure22350311.sub_scheme_code == SUB_SCHEME_CODE,
        )
    )

    if district:
        query = query.filter(DistrictExpenditure22350311.district == district)
    else:
        query = query.filter(DistrictExpenditure22350311.district.in_(allowed_districts))

    total_count = query.with_entities(func.count(DistrictExpenditure22350311.id)).scalar()
    items = (
        query.order_by(DistrictExpenditure22350311.district)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)

    context = {
        "request": request,
        "items": items,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "districts": allowed_districts,
        "current_district": district,
        "can_edit": can_edit,
        "resource_name": "22350311 जिल्हानिहाय खर्च",
        "districts_mr": DISTRICTS_MR,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "fy_labels": fy_labels,
    }

    return render(
        request,
        "schemes/s2235/subs/s22350311/district_expenditure_list.html",
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

    from src.core.taluka.write import resolve_editable_row
    item = resolve_editable_row(db, DistrictExpenditure22350311, id, request)

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    auth_role = get_auth_role(request)

    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2235(relative_years)

    context = {
        "request": request,
        "item": item,
        "districts": allowed_districts,
        "resource_name": "22350311 जिल्हानिहाय खर्च संपादन",
        "districts_mr": DISTRICTS_MR,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "fy_labels": fy_labels,
    }
    return render(
        request,
        "schemes/s2235/subs/s22350311/district_expenditure_form.html",
        context,
    )


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    from src.utils_timing import check_data_filling_allowed

    auth_role = get_auth_role(request) or ""
    auth_level = get_auth_level(request) or ""
    auth_unit = get_auth_unit(request) or ""

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=timing_msg or "Data filling period has expired")

    from src.core.taluka.write import resolve_editable_row
    item = resolve_editable_row(db, DistrictExpenditure22350311, id, request)

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    form = await request.form()
    district = form.get("District")

    if district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    old_vals = {
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_grant_curr": item.budget_grant_curr,
        "revised_grant_curr": item.revised_grant_curr,
        "budget_estimate_next": item.budget_estimate_next,
    }

    item.district = district
    item.expenditure_prev3 = validate_numeric_input(form.get("ExpenditurePrev3"), "ExpenditurePrev3")
    item.expenditure_prev2 = validate_numeric_input(form.get("ExpenditurePrev2"), "ExpenditurePrev2")
    item.expenditure_prev1 = validate_numeric_input(form.get("ExpenditurePrev1"), "ExpenditurePrev1")
    item.budget_grant_curr = validate_numeric_input(form.get("BudgetGrantCurr"), "BudgetGrantCurr")
    item.revised_grant_curr = validate_numeric_input(form.get("RevisedGrantCurr"), "RevisedGrantCurr")
    item.budget_estimate_next = validate_numeric_input(form.get("BudgetEstimateNext"), "BudgetEstimateNext")

    new_vals = {
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_grant_curr": item.budget_grant_curr,
        "revised_grant_curr": item.revised_grant_curr,
        "budget_estimate_next": item.budget_estimate_next,
    }

    from src.core.taluka.consolidation import consolidate_row
    from src.core.taluka.models import natural_key_columns
    db.flush()
    key_cols = natural_key_columns(DistrictExpenditure22350311)
    consolidate_row(db, DistrictExpenditure22350311, item.district, item.fiscal_year,
                     {c: getattr(item, c) for c in key_cols})
    db.commit()
    db.refresh(item)

    username = (get_auth_user(request) or "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_22350311",
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


@router.get("/division-total", response_class=HTMLResponse)
async def ui_division_total(
    request: Request,
    db: Session = Depends(get_db),
):
    """Display auto-calculated division totals from all district data."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2235(relative_years)

    totals = (
        db.query(
            func.sum(DistrictExpenditure22350311.expenditure_prev3).label("total_exp_prev3"),
            func.sum(DistrictExpenditure22350311.expenditure_prev2).label("total_exp_prev2"),
            func.sum(DistrictExpenditure22350311.expenditure_prev1).label("total_exp_prev1"),
            func.sum(DistrictExpenditure22350311.budget_grant_curr).label("total_bg_curr"),
            func.sum(DistrictExpenditure22350311.revised_grant_curr).label("total_rg_curr"),
            func.sum(DistrictExpenditure22350311.budget_estimate_next).label("total_be_next"),
        )
        .filter(
            DistrictExpenditure22350311.fiscal_year == fiscal_year,
            DistrictExpenditure22350311.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure22350311.district.in_(KONKAN_DISTRICTS),
        )
        .first()
    )

    division_total = {
        "expenditure_prev3": totals.total_exp_prev3 or 0,
        "expenditure_prev2": totals.total_exp_prev2 or 0,
        "expenditure_prev1": totals.total_exp_prev1 or 0,
        "budget_grant_curr": totals.total_bg_curr or 0,
        "revised_grant_curr": totals.total_rg_curr or 0,
        "budget_estimate_next": totals.total_be_next or 0,
    }

    context = {
        "request": request,
        "division_total": division_total,
        "resource_name": "22350311 विभाग एकूण",
        "districts_mr": DISTRICTS_MR,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "fiscal_year": fiscal_year,
        "fy_labels": fy_labels,
    }

    return render(
        request,
        "schemes/s2235/subs/s22350311/division_total.html",
        context,
    )


@router.get("/export")
async def ui_export_excel(
    request: Request,
    db: Session = Depends(get_db),
):
    """Export unified 2235 budget data (all 4 sub-schemas) to Excel.
    
    This exports data from ALL sub-schemas:
    - 22353195: आत्महत्या केलेल्या शेतकऱ्यांच्या वारसांना वित्तीय सहाय्य
    - 22350338: ठेव संलग्न विमा योजना
    - 22350311: आपघातग्रस्तांना आर्थिक मदत
    - 22353408: मुक्त वेठबिगारांसाठी पुनर्वसन योजना
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from src.schemes.s2235 import export_2235_workbook_async
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    return await export_2235_workbook_async(db, fiscal_year)

