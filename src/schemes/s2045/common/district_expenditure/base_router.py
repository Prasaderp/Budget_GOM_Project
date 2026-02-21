"""Base router factory for s2045 district expenditure sub-schemes."""
from typing import Optional, Callable, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import DISTRICTS_MR
from src.database import get_db
from src.core.templates import templates
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years, validate_fiscal_year
from src.utils_auth import get_auth_unit
from src.utils_district import get_request_info

from .base_helpers import DistrictExpenditureHelper


def create_district_expenditure_routers(
    sub_scheme_code: str,
    model_class,
    helper: DistrictExpenditureHelper,
    template_base_path: str,
    resource_name_mr: str,
    excel_export_fn: Optional[Callable] = None,
) -> Tuple[APIRouter, APIRouter]:
    """
    Factory function to create UI and API routers for district expenditure.
    
    Args:
        sub_scheme_code: Sub-scheme code (e.g., '20450182')
        model_class: SQLAlchemy model class
        helper: DistrictExpenditureHelper instance
        template_base_path: Base path for templates (e.g., 'schemes/s2045/subs/s20450182')
        resource_name_mr: Resource name in Marathi for display
        excel_export_fn: Optional async function for Excel export
    
    Returns:
        Tuple of (ui_router, api_router)
    """
    
    # =========================================================================
    # UI ROUTER
    # =========================================================================
    ui_router = APIRouter(
        prefix=f"/ui/s{sub_scheme_code}/district-expenditure",
        tags=[f"UI - {sub_scheme_code} जिल्हानिहाय खर्च"],
        include_in_schema=False,
    )
    
    @ui_router.get("", response_class=HTMLResponse)
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
        
        allowed_districts = helper.get_allowed_districts_for_user(auth_level, auth_unit)
        if not allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        if district and district not in allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid district selection")
        
        fiscal_year = get_fiscal_year_from_request(request, db)
        helper.ensure_fiscal_year_seeded(db, fiscal_year)
        
        query = (
            db.query(model_class)
            .filter(
                model_class.fiscal_year == fiscal_year,
                model_class.sub_scheme_code == sub_scheme_code,
            )
        )
        
        if district:
            query = query.filter(model_class.district == district)
        else:
            query = query.filter(model_class.district.in_(allowed_districts))
        
        total_count = query.with_entities(func.count(model_class.id)).scalar()
        items = (
            query.order_by(model_class.district)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        can_edit = helper.check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
        
        context = {
            "request": request,
            "items": items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "districts": allowed_districts,
            "current_district": district,
            "can_edit": can_edit,
            "resource_name": resource_name_mr,
            "districts_mr": DISTRICTS_MR,
            "auth_level": auth_level,
            "auth_role": auth_role,
            "sub_scheme_code": sub_scheme_code,
            "relative_years": get_relative_fiscal_years(fiscal_year),
        }
        
        return templates.TemplateResponse(
            f"{template_base_path}/district_expenditure_list.html",
            context,
        )
    
    @ui_router.get("/{id}/edit", response_class=HTMLResponse)
    async def ui_edit_district_expenditure_form(
        request: Request,
        id: int,
        db: Session = Depends(get_db),
    ):
        auth_level = request.cookies.get("auth_level", "")
        auth_unit = get_auth_unit(request)
        
        item = db.query(model_class).filter(model_class.id == id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        
        allowed_districts = helper.get_allowed_districts_for_user(auth_level, auth_unit)
        if item.district not in allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        allowed, error_msg = helper.validate_access_control(item.district, auth_level, auth_unit, db)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
        
        auth_role = request.cookies.get("auth_role", "")
        fiscal_year = get_fiscal_year_from_request(request, db)
        context = {
            "request": request,
            "item": item,
            "districts": allowed_districts,
            "resource_name": f"{resource_name_mr} संपादन",
            "districts_mr": DISTRICTS_MR,
            "auth_level": auth_level,
            "auth_role": auth_role,
            "sub_scheme_code": sub_scheme_code,
            "relative_years": get_relative_fiscal_years(fiscal_year),
        }
        return templates.TemplateResponse(
            f"{template_base_path}/district_expenditure_form.html",
            context,
        )
    
    @ui_router.post("/{id}/edit", response_class=RedirectResponse)
    async def ui_update_district_expenditure(
        request: Request,
        id: int,
        db: Session = Depends(get_db),
    ):
        from src.utils_timing import check_data_filling_allowed
        
        auth_role = request.cookies.get("auth_role") or ""
        auth_level = request.cookies.get("auth_level") or ""
        auth_unit = get_auth_unit(request) or ""
        
        if not helper.check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        
        if auth_role == "assistant":
            is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, sub_scheme_code)
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=timing_msg or "Data filling period has expired"
                )
        
        item = db.query(model_class).filter(model_class.id == id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        
        allowed_districts = helper.get_allowed_districts_for_user(auth_level, auth_unit)
        form = await request.form()
        district = form.get("District")
        
        if district not in allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        allowed, error_msg = helper.validate_access_control(district, auth_level, auth_unit, db)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
        
        old_vals = helper.get_record_values(item)
        
        item.district = district
        item.expenditure_2022_23 = helper.validate_numeric_input(form.get("Expenditure2022_23"), "Expenditure2022_23")
        item.expenditure_2023_24 = helper.validate_numeric_input(form.get("Expenditure2023_24"), "Expenditure2023_24")
        item.expenditure_2024_25 = helper.validate_numeric_input(form.get("Expenditure2024_25"), "Expenditure2024_25")
        item.budget_estimate_2025_26 = helper.validate_numeric_input(form.get("BudgetEstimate2025_26"), "BudgetEstimate2025_26")
        item.quarterly_expenditure_apr_jul_2025 = helper.validate_numeric_input(form.get("QuarterlyExpenditure2025"), "QuarterlyExpenditure2025")
        item.budget_estimate_2026_27 = helper.validate_numeric_input(form.get("BudgetEstimate2026_27"), "BudgetEstimate2026_27")
        item.remarks = (form.get("Remarks") or "").strip() or None
        
        new_vals = helper.get_record_values(item)
        
        db.commit()
        db.refresh(item)
        
        username = request.cookies.get("username", "unknown")
        req_info = get_request_info(request)
        helper.log_audit_async(
            record_id=item.id,
            username=username,
            old_vals=old_vals,
            new_vals=new_vals,
            req_info=req_info,
            action="UPDATE"
        )
        
        return RedirectResponse(
            url=f"/ui/s{sub_scheme_code}/district-expenditure",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    if excel_export_fn:
        @ui_router.get("/export")
        async def ui_export_excel(
            request: Request,
            db: Session = Depends(get_db),
        ):
            """Export district expenditure data to Excel."""
            fiscal_year = get_fiscal_year_from_request(request, db)
            return await excel_export_fn(db, fiscal_year)
    
    # =========================================================================
    # API ROUTER
    # =========================================================================
    api_router = APIRouter(
        prefix=f"/api/s{sub_scheme_code}",
        tags=[f"API - {sub_scheme_code} जिल्हानिहाय खर्च"],
    )
    
    @api_router.get("")
    def list_district_expenditure(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        fiscal_year: Optional[str] = None,
        db: Session = Depends(get_db),
    ):
        auth_level = request.cookies.get("auth_level", "")
        auth_unit = get_auth_unit(request)
        
        allowed_districts = helper.get_allowed_districts_for_user(auth_level, auth_unit)
        if not allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        fy = validate_fiscal_year(fiscal_year, db)
        helper.ensure_fiscal_year_seeded(db, fy)
        
        query = (
            db.query(model_class)
            .filter(
                model_class.fiscal_year == fy,
                model_class.sub_scheme_code == sub_scheme_code,
                model_class.district.in_(allowed_districts),
            )
            .order_by(model_class.district)
            .offset(skip)
            .limit(limit)
        )
        return query.all()
    
    @api_router.get("/{id}")
    def get_district_expenditure(
        request: Request,
        id: int,
        db: Session = Depends(get_db),
    ):
        auth_level = request.cookies.get("auth_level", "")
        auth_unit = get_auth_unit(request)
        
        item = (
            db.query(model_class)
            .filter(
                model_class.id == id,
                model_class.sub_scheme_code == sub_scheme_code,
            )
            .first()
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        
        allowed_districts = helper.get_allowed_districts_for_user(auth_level, auth_unit)
        if item.district not in allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        allowed, error_msg = helper.validate_access_control(item.district, auth_level, auth_unit, db)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
        
        return item
    
    @api_router.put("/{id}")
    def update_district_expenditure(
        request: Request,
        id: int,
        db: Session = Depends(get_db),
    ):
        from src.utils_timing import check_data_filling_allowed
        
        auth_role = request.cookies.get("auth_role", "")
        auth_level = request.cookies.get("auth_level", "")
        auth_unit = get_auth_unit(request)
        
        if not helper.check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        
        # Timing check for assistants (same as UI endpoint)
        if auth_role == "assistant":
            is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, sub_scheme_code)
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=timing_msg or "Data filling period has expired"
                )
        
        item = (
            db.query(model_class)
            .filter(
                model_class.id == id,
                model_class.sub_scheme_code == sub_scheme_code,
            )
            .first()
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        
        allowed_districts = helper.get_allowed_districts_for_user(auth_level, auth_unit)
        if item.district not in allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        allowed, error_msg = helper.validate_access_control(item.district, auth_level, auth_unit, db)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
        
        return item
    
    return ui_router, api_router
