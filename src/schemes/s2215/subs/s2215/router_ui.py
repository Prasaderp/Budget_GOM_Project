"""UI routes for sub-scheme 2215 - Water Scarcity district-wise expenditure."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Form, Request, status
from starlette.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.templates import templates
from src.core.template_context import get_standard_template_context
from src.utils_fiscal_year import get_fiscal_year_from_request
from .models import DistrictExpenditure2215, SUB_SCHEME_CODE
from .config import (
    get_all_account_heads,
    DIVISION_TOTAL_DISTRICT_MR,
    DISTRICT_OFFICES_MR,
    NOTIFICATIONS_MR,
)
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    validate_access_control,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
    calculate_division_totals,
)
from src.utils_auth import get_auth_unit


router = APIRouter(
    prefix="/ui/s2215",
    tags=["UI - 2215 पाणी टंचाई"],
    include_in_schema=False,
)


@router.get("", response_class=HTMLResponse)
async def ui_list_2215(
    request: Request,
    db: Session = Depends(get_db),
):
    """Main UI page for scheme 2215 - displays account heads and district expenditure with division totals."""
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)

    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    account_heads = get_all_account_heads()
    
    # Process all account heads to build table structure
    tables_data = []
    for head in account_heads:
        allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, head["code"])
        if not allowed_districts:
            continue

        query = (
            db.query(DistrictExpenditure2215)
            .filter(
                DistrictExpenditure2215.fiscal_year == fiscal_year,
                DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2215.account_head_code == head["code"],
                DistrictExpenditure2215.district.in_(allowed_districts),
            )
            .order_by(DistrictExpenditure2215.district)
        )
        items = query.all()

        # Calculate totals for this account head
        totals = {
            "expenditure_2022_23": sum(item.expenditure_2022_23 or 0 for item in items),
            "expenditure_2023_24": sum(item.expenditure_2023_24 or 0 for item in items),
            "expenditure_2024_25": sum(item.expenditure_2024_25 or 0 for item in items),
            "budget_estimate_2025_26": sum(item.budget_estimate_2025_26 or 0 for item in items),
            "revised_demand_2025_26": sum(item.revised_demand_2025_26 or 0 for item in items),
            "budget_estimate_2026_27": sum(item.budget_estimate_2026_27 or 0 for item in items),
        }

        tables_data.append({
            "head": head,
            "items": items,
            "totals": totals,
        })

    # Calculate division totals (Konkan Division) across all account heads
    division_totals = calculate_division_totals(db, fiscal_year, auth_level, auth_unit)

    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)

    context = {
        "request": request,
        "resource_name": "2215 पाणी टंचाई",
        "fiscal_year": fiscal_year,
        "account_heads": account_heads,
        "tables_data": tables_data,
        "division_totals": division_totals,
        "can_edit": can_edit,
        "districts_mr": DISTRICT_OFFICES_MR,
    }
    context.update(get_standard_template_context(request))

    return templates.TemplateResponse(
        "schemes/s2215/subs/s2215/index.html",
        context,
    )


@router.post("/update", response_class=JSONResponse)
async def ui_update_2215(
    request: Request,
    db: Session = Depends(get_db),
    record_id: int = Form(...),
    expenditure_2022_23: Optional[str] = Form(None),
    expenditure_2023_24: Optional[str] = Form(None),
    expenditure_2024_25: Optional[str] = Form(None),
    budget_estimate_2025_26: Optional[str] = Form(None),
    revised_demand_2025_26: Optional[str] = Form(None),
    budget_estimate_2026_27: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
):
    """Update a district expenditure record via UI form."""
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    item = (
        db.query(DistrictExpenditure2215)
        .filter(
            DistrictExpenditure2215.id == record_id,
            DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, item.account_head_code)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    old_vals = {
        "account_head_code": item.account_head_code,
        "district": item.district,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_estimate_2025_26": item.budget_estimate_2025_26,
        "revised_demand_2025_26": item.revised_demand_2025_26,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }

    item.expenditure_2022_23 = validate_numeric_input(expenditure_2022_23, "expenditure_2022_23")
    item.expenditure_2023_24 = validate_numeric_input(expenditure_2023_24, "expenditure_2023_24")
    item.expenditure_2024_25 = validate_numeric_input(expenditure_2024_25, "expenditure_2024_25")
    item.budget_estimate_2025_26 = validate_numeric_input(budget_estimate_2025_26, "budget_estimate_2025_26")
    item.revised_demand_2025_26 = validate_numeric_input(revised_demand_2025_26, "revised_demand_2025_26")
    item.budget_estimate_2026_27 = validate_numeric_input(budget_estimate_2026_27, "budget_estimate_2026_27")
    if remarks is not None:
        item.remarks = remarks

    db.commit()
    db.refresh(item)

    new_vals = {
        "account_head_code": item.account_head_code,
        "district": item.district,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_estimate_2025_26": item.budget_estimate_2025_26,
        "revised_demand_2025_26": item.revised_demand_2025_26,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }

    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_2215",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )

    return JSONResponse({
        "success": True,
        "message": NOTIFICATIONS_MR["update_success"]
    })


@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(
    request: Request,
    db: Session = Depends(get_db),
    account_head_code: str = Query(...),
    district: str = Query(...),
):
    """API endpoint to fetch record data for inline editing."""
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)

    fiscal_year = get_fiscal_year_from_request(request, db)
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, account_head_code)
    if district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    item = (
        db.query(DistrictExpenditure2215)
        .filter(
            DistrictExpenditure2215.fiscal_year == fiscal_year,
            DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure2215.account_head_code == account_head_code,
            DistrictExpenditure2215.district == district,
        )
        .first()
    )

    if not item:
        return JSONResponse({"found": False})

    return JSONResponse({
        "found": True,
        "id": item.id,
        "expenditure_2022_23": item.expenditure_2022_23 or 0,
        "expenditure_2023_24": item.expenditure_2023_24 or 0,
        "expenditure_2024_25": item.expenditure_2024_25 or 0,
        "budget_estimate_2025_26": item.budget_estimate_2025_26 or 0,
        "revised_demand_2025_26": item.revised_demand_2025_26 or 0,
        "budget_estimate_2026_27": item.budget_estimate_2026_27 or 0,
        "remarks": item.remarks or "",
    })


@router.get("/totals", response_class=HTMLResponse)
async def ui_totals_2215(
    request: Request,
    db: Session = Depends(get_db),
):
    """Totals view for scheme 2215 - displays separate totals for each account head."""
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)
    
    account_heads = get_all_account_heads()
    
    # Calculate totals per account head (reusing logic from main view)
    totals_data = []
    for head in account_heads:
        allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, head["code"])
        if not allowed_districts:
            continue
        
        items = (
            db.query(DistrictExpenditure2215)
            .filter(
                DistrictExpenditure2215.fiscal_year == fiscal_year,
                DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2215.account_head_code == head["code"],
                DistrictExpenditure2215.district.in_(allowed_districts),
            )
            .all()
        )
        
        # Calculate totals for this account head
        totals = {
            "expenditure_2022_23": sum(item.expenditure_2022_23 or 0 for item in items),
            "expenditure_2023_24": sum(item.expenditure_2023_24 or 0 for item in items),
            "expenditure_2024_25": sum(item.expenditure_2024_25 or 0 for item in items),
            "budget_estimate_2025_26": sum(item.budget_estimate_2025_26 or 0 for item in items),
            "revised_demand_2025_26": sum(item.revised_demand_2025_26 or 0 for item in items),
            "budget_estimate_2026_27": sum(item.budget_estimate_2026_27 or 0 for item in items),
        }
        
        totals_data.append({
            "head": head,
            "totals": totals,
        })
    
    context = {
        "request": request,
        "resource_name": "2215 पाणी टंचाई - एकूण",
        "fiscal_year": fiscal_year,
        "totals_data": totals_data,
        "division_name_mr": DIVISION_TOTAL_DISTRICT_MR,
    }
    context.update(get_standard_template_context(request))

    return templates.TemplateResponse(
        "schemes/s2215/subs/s2215/totals.html",
        context,
    )

