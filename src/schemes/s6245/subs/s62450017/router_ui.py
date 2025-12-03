"""UI routes for sub-scheme 62450017 district-wise expenditure."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import DISTRICTS_MR, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER
from src.database import get_db
from src.utils_district import get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from src.utils_taluka import is_taluka_allowed
from .models import DistrictExpenditure62450017, SUB_SCHEME_CODE
from .schemas import KONKAN_DISTRICTS


templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/s62450017/district-expenditure",
    tags=["UI - 62450017 इतर कर्जे"],
    include_in_schema=False,
)


def _get_allowed_districts_for_user(auth_level: str, auth_unit: str) -> list[str]:
    if auth_level == "district" and auth_unit:
        return [auth_unit] if auth_unit in KONKAN_DISTRICTS else []
    if auth_level == "taluka" and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        return [district_name] if district_name in KONKAN_DISTRICTS else []
    return KONKAN_DISTRICTS


def _check_edit_permission(auth_role: str, auth_level: str, auth_unit: str, district: str | None, db: Session) -> bool:
    if auth_role in ("officer1", "officer2", "dco"):
        return True
    if auth_level == "district" and auth_unit:
        return district is None or district == auth_unit
    if auth_level == "taluka" and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            return False
        dist = get_district_from_taluka(auth_unit)
        return district is None or district == dist
    return False


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
    auth_unit = request.cookies.get("auth_unit", "")

    allowed_districts = _get_allowed_districts_for_user(auth_level, auth_unit)
    if not allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if district and district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid district selection")

    fiscal_year = get_fiscal_year_from_request(request, db)

    query = (
        db.query(DistrictExpenditure62450017)
        .filter(
            DistrictExpenditure62450017.fiscal_year == fiscal_year,
            DistrictExpenditure62450017.sub_scheme_code == SUB_SCHEME_CODE,
        )
    )

    if district:
        query = query.filter(DistrictExpenditure62450017.district == district)
    else:
        query = query.filter(DistrictExpenditure62450017.district.in_(allowed_districts))

    total_count = query.with_entities(func.count(DistrictExpenditure62450017.id)).scalar()
    items = (
        query.order_by(DistrictExpenditure62450017.district)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    can_edit = _check_edit_permission(auth_role, auth_level, auth_unit, district, db)

    context = {
        "request": request,
        "items": items,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "districts": allowed_districts,
        "current_district": district,
        "can_edit": can_edit,
        "resource_name": "62450017 जिल्हानिहाय खर्च",
        "districts_mr": DISTRICTS_MR,
    }

    return templates.TemplateResponse(
        "schemes/s6245/subs/s62450017/district_expenditure_list.html",
        context,
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_district_expenditure_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")

    item = db.query(DistrictExpenditure62450017).filter(DistrictExpenditure62450017.id == id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = _get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    context = {
        "request": request,
        "item": item,
        "districts": allowed_districts,
        "resource_name": "62450017 जिल्हानिहाय खर्च संपादन",
        "districts_mr": DISTRICTS_MR,
    }
    return templates.TemplateResponse(
        "schemes/s6245/subs/s62450017/district_expenditure_form.html",
        context,
    )


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    from fastapi import Form

    district = (await request.form()).get("District")  # minimal inline parsing

    auth_role = request.cookies.get("auth_role") or ""
    auth_level = request.cookies.get("auth_level") or ""
    auth_unit = request.cookies.get("auth_unit") or ""

    item = db.query(DistrictExpenditure62450017).filter(DistrictExpenditure62450017.id == id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = _get_allowed_districts_for_user(auth_level, auth_unit)
    if district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Re-parse with explicit fields for clarity
    form = await request.form()

    def _parse_int(name: str) -> int:
        raw = form.get(name)
        if raw in (None, ""):
            return 0
        try:
            val = int(raw)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid value for {name}")
        if val < 0 or val > 999_999_999_999:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Out of range value for {name}")
        return val

    item.district = district
    item.expenditure_2022_23 = _parse_int("Expenditure2022_23")
    item.expenditure_2023_24 = _parse_int("Expenditure2023_24")
    item.expenditure_2024_25 = _parse_int("Expenditure2024_25")
    item.budget_grant_2025_26 = _parse_int("BudgetGrant2025_26")
    item.revised_estimate_2025_26 = _parse_int("RevisedEstimate2025_26")
    item.budget_estimate_2026_27 = _parse_int("BudgetEstimate2026_27")
    item.remarks = (form.get("Remarks") or "").strip() or None

    db.commit()

    return RedirectResponse(
        url=router.url_path_for("ui_list_district_expenditure"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


