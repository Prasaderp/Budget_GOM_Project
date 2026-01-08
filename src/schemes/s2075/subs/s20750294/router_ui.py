"""UI routes for sub-scheme 20750294 sub-head expenditure."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.templates import templates
from src.utils_fiscal_year import get_fiscal_year_from_request
from .models import SubHeadExpenditure20750294, SUB_SCHEME_CODE
from .helpers import (
    check_dco_access,
    check_edit_permission_for_scheme,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)

router = APIRouter(
    prefix="/ui/s20750294/sub-head-expenditure",
    tags=["UI - 20750294 उपशिर्ष / गौणशिर्ष खर्च"],
    include_in_schema=False,
)


@router.get("", response_class=HTMLResponse)
async def ui_list_sub_head_expenditure(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")

    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO only")

    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    query = (
        db.query(SubHeadExpenditure20750294)
        .filter(
            SubHeadExpenditure20750294.fiscal_year == fiscal_year,
            SubHeadExpenditure20750294.sub_scheme_code == SUB_SCHEME_CODE,
        )
    )

    total_count = query.with_entities(func.count(SubHeadExpenditure20750294.id)).scalar()
    items = (
        query.order_by(SubHeadExpenditure20750294.id)
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
        "can_edit": can_edit,
        "resource_name": "20750294 उपशिर्ष / गौणशिर्ष खर्च",
        "auth_level": auth_level,
        "auth_role": auth_role,
    }

    return templates.TemplateResponse(
        "schemes/s2075/subs/s20750294/sub_head_expenditure_list.html",
        context,
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_sub_head_expenditure_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")

    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO only")

    item = (
        db.query(SubHeadExpenditure20750294)
        .filter(
            SubHeadExpenditure20750294.id == id,
            SubHeadExpenditure20750294.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    auth_role = request.cookies.get("auth_role", "")
    context = {
        "request": request,
        "item": item,
        "resource_name": "20750294 उपशिर्ष / गौणशिर्ष खर्च संपादन",
        "auth_level": auth_level,
        "auth_role": auth_role,
    }
    return templates.TemplateResponse(
        "schemes/s2075/subs/s20750294/sub_head_expenditure_form.html",
        context,
    )


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_sub_head_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    from src.utils_timing import check_data_filling_allowed

    auth_role = request.cookies.get("auth_role") or ""
    auth_level = request.cookies.get("auth_level") or ""
    auth_unit = request.cookies.get("auth_unit") or ""

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=timing_msg or "Data filling period has expired")

    item = (
        db.query(SubHeadExpenditure20750294)
        .filter(
            SubHeadExpenditure20750294.id == id,
            SubHeadExpenditure20750294.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    form = await request.form()

    old_vals = {
        "sub_head": item.sub_head,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }
    item.expenditure_2022_23 = validate_numeric_input(form.get("Expenditure2022_23"), "Expenditure2022_23")
    item.expenditure_2023_24 = validate_numeric_input(form.get("Expenditure2023_24"), "Expenditure2023_24")
    item.expenditure_2024_25 = validate_numeric_input(form.get("Expenditure2024_25"), "Expenditure2024_25")
    item.budget_estimate = validate_numeric_input(form.get("BudgetEstimate"), "BudgetEstimate")
    item.revised_estimate = validate_numeric_input(form.get("RevisedEstimate"), "RevisedEstimate")
    item.budget_estimate_2026_27 = validate_numeric_input(form.get("BudgetEstimate2026_27"), "BudgetEstimate2026_27")
    item.remarks = (form.get("Remarks") or "").strip() or None

    new_vals = {
        "sub_head": item.sub_head,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }

    db.commit()
    db.refresh(item)

    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="sub_head_expenditure_20750294",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE"
    )

    return RedirectResponse(
        url=router.url_path_for("ui_list_sub_head_expenditure"),
        status_code=status.HTTP_303_SEE_OTHER,
    )

