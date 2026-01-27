"""UI routes for sub-scheme 22353408 district-wise expenditure."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.config import DISTRICTS_MR
from src.database import get_db
from src.core.templates import templates
from src.utils_fiscal_year import get_fiscal_year_from_request
from .models import DistrictExpenditure22353408, SUB_SCHEME_CODE
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    validate_access_control,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)
from src.utils_auth import get_auth_unit

router = APIRouter(
    prefix="/ui/s22353408/district-expenditure",
    tags=["UI - 22353408 वृद्धांचे कल्याण"],
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
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if not allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if district and district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid district selection")

    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    query = (
        db.query(DistrictExpenditure22353408)
        .filter(
            DistrictExpenditure22353408.fiscal_year == fiscal_year,
            DistrictExpenditure22353408.sub_scheme_code == SUB_SCHEME_CODE,
        )
    )

    if district:
        query = query.filter(DistrictExpenditure22353408.district == district)
    else:
        query = query.filter(DistrictExpenditure22353408.district.in_(allowed_districts))

    total_count = query.with_entities(func.count(DistrictExpenditure22353408.id)).scalar()
    items = (
        query.order_by(DistrictExpenditure22353408.district)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Compute totals for all numeric columns
    totals_query = (
        db.query(
            func.coalesce(func.sum(DistrictExpenditure22353408.expenditure_2022_23), 0).label("expenditure_2022_23"),
            func.coalesce(func.sum(DistrictExpenditure22353408.expenditure_2023_24), 0).label("expenditure_2023_24"),
            func.coalesce(func.sum(DistrictExpenditure22353408.expenditure_2024_25), 0).label("expenditure_2024_25"),
            func.coalesce(func.sum(DistrictExpenditure22353408.budget_grant_2025_26), 0).label("budget_grant_2025_26"),
            func.coalesce(func.sum(DistrictExpenditure22353408.revised_grant_2025_26), 0).label("revised_grant_2025_26"),
            func.coalesce(func.sum(DistrictExpenditure22353408.budget_estimate_2026_27), 0).label("budget_estimate_2026_27"),
        )
        .filter(
            DistrictExpenditure22353408.fiscal_year == fiscal_year,
            DistrictExpenditure22353408.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure22353408.district.in_(allowed_districts),
        )
    )
    totals_row = totals_query.first()
    totals = {
        "expenditure_2022_23": totals_row.expenditure_2022_23 if totals_row else 0,
        "expenditure_2023_24": totals_row.expenditure_2023_24 if totals_row else 0,
        "expenditure_2024_25": totals_row.expenditure_2024_25 if totals_row else 0,
        "budget_grant_2025_26": totals_row.budget_grant_2025_26 if totals_row else 0,
        "revised_grant_2025_26": totals_row.revised_grant_2025_26 if totals_row else 0,
        "budget_estimate_2026_27": totals_row.budget_estimate_2026_27 if totals_row else 0,
    }


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
        "resource_name": "22353408 जिल्हानिहाय खर्च",
        "districts_mr": DISTRICTS_MR,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "totals": totals,
    }

    return templates.TemplateResponse(
        "schemes/s2235/subs/s22353408/district_expenditure_list.html",
        context,
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_district_expenditure_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)

    item = db.query(DistrictExpenditure22353408).filter(DistrictExpenditure22353408.id == id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    auth_role = request.cookies.get("auth_role", "")
    context = {
        "request": request,
        "item": item,
        "districts": allowed_districts,
        "resource_name": "22353408 जिल्हानिहाय खर्च संपादन",
        "districts_mr": DISTRICTS_MR,
        "auth_level": auth_level,
        "auth_role": auth_role,
    }
    return templates.TemplateResponse(
        "schemes/s2235/subs/s22353408/district_expenditure_form.html",
        context,
    )


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    from src.utils_timing import check_data_filling_allowed

    auth_role = request.cookies.get("auth_role") or ""
    auth_level = request.cookies.get("auth_level") or ""
    auth_unit = get_auth_unit(request) or ""

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=timing_msg or "Data filling period has expired")

    item = db.query(DistrictExpenditure22353408).filter(DistrictExpenditure22353408.id == id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

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
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_grant_2025_26": item.budget_grant_2025_26,
        "revised_grant_2025_26": item.revised_grant_2025_26,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
    }

    item.district = district
    item.expenditure_2022_23 = validate_numeric_input(form.get("Expenditure2022_23"), "Expenditure2022_23")
    item.expenditure_2023_24 = validate_numeric_input(form.get("Expenditure2023_24"), "Expenditure2023_24")
    item.expenditure_2024_25 = validate_numeric_input(form.get("Expenditure2024_25"), "Expenditure2024_25")
    item.budget_grant_2025_26 = validate_numeric_input(form.get("BudgetGrant2025_26"), "BudgetGrant2025_26")
    item.revised_grant_2025_26 = validate_numeric_input(form.get("RevisedGrant2025_26"), "RevisedGrant2025_26")
    item.budget_estimate_2026_27 = validate_numeric_input(form.get("BudgetEstimate2026_27"), "BudgetEstimate2026_27")

    new_vals = {
        "district": item.district,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_grant_2025_26": item.budget_grant_2025_26,
        "revised_grant_2025_26": item.revised_grant_2025_26,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
    }

    db.commit()
    db.refresh(item)

    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_22353408",
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
    """Export unified 2235 budget data (all 4 sub-schemas) to Excel.
    
    This exports data from ALL sub-schemas:
    - 22353195: आत्महत्या केलेल्या शेतकऱ्यांच्या वारसांना वित्तीय सहाय्य
    - 22350338: ठेव संलग्न विमा योजना
    - 22350311: आपघातग्रस्तांना आर्थिक मदत
    - 22353408: मुक्त वेठबिगारांसाठी पुनर्वसन योजना
    """
    from src.schemes.s2235 import export_2235_workbook_async
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    return await export_2235_workbook_async(db, fiscal_year)
