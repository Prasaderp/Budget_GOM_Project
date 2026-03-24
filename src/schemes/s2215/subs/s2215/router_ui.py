"""UI routes for sub-scheme 2215 - Water Scarcity district-wise expenditure."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Form, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.templates import render
from src.core.template_context import get_standard_template_context
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.schemes.s2215.fiscal_year_labels import FiscalYearLabels2215
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
    validate_numeric_input,
    log_audit,
    ensure_fiscal_year_seeded,
    calculate_division_totals,
)
from src.utils_auth import get_auth_unit, get_auth_role, get_auth_level, is_authenticated


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
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    # Resolve dynamic fiscal year labels (single computation, zero duplication)
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2215(relative_years)

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
            "expenditure_prev3": sum(item.expenditure_prev3 or 0 for item in items),
            "expenditure_prev2": sum(item.expenditure_prev2 or 0 for item in items),
            "expenditure_prev1": sum(item.expenditure_prev1 or 0 for item in items),
            "budget_estimate_curr": sum(item.budget_estimate_curr or 0 for item in items),
            "revised_demand_curr": sum(item.revised_demand_curr or 0 for item in items),
            "budget_estimate_next": sum(item.budget_estimate_next or 0 for item in items),
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
        "relative_years": relative_years,
        "fy_labels": fy_labels,
    }
    context.update(get_standard_template_context(request))

    return render(request, 
        "schemes/s2215/subs/s2215/index.html",
        context,
    )


@router.post("/update", response_class=JSONResponse)
async def ui_update_2215(
    request: Request,
    db: Session = Depends(get_db),
    record_id: int = Form(...),
    expenditure_prev3: Optional[str] = Form(None),
    expenditure_prev2: Optional[str] = Form(None),
    expenditure_prev1: Optional[str] = Form(None),
    budget_estimate_curr: Optional[str] = Form(None),
    revised_demand_curr: Optional[str] = Form(None),
    budget_estimate_next: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
):
    """Update a district expenditure record via UI form."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
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

    old_vals = {
        "account_head_code": item.account_head_code,
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_estimate_curr": item.budget_estimate_curr,
        "revised_demand_curr": item.revised_demand_curr,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }

    item.expenditure_prev3 = validate_numeric_input(expenditure_prev3, "expenditure_prev3")
    item.expenditure_prev2 = validate_numeric_input(expenditure_prev2, "expenditure_prev2")
    item.expenditure_prev1 = validate_numeric_input(expenditure_prev1, "expenditure_prev1")
    item.budget_estimate_curr = validate_numeric_input(budget_estimate_curr, "budget_estimate_curr")
    item.revised_demand_curr = validate_numeric_input(revised_demand_curr, "revised_demand_curr")
    item.budget_estimate_next = validate_numeric_input(budget_estimate_next, "budget_estimate_next")
    if remarks is not None:
        item.remarks = remarks

    db.commit()
    db.refresh(item)

    new_vals = {
        "account_head_code": item.account_head_code,
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_estimate_curr": item.budget_estimate_curr,
        "revised_demand_curr": item.revised_demand_curr,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }

    log_audit(
        db=db,
        request=request,
        table="district_expenditure_2215",
        record_id=item.id,
        old_vals=old_vals,
        new_vals=new_vals,
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
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    auth_level = get_auth_level(request)
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
        "expenditure_prev3": item.expenditure_prev3 or 0,
        "expenditure_prev2": item.expenditure_prev2 or 0,
        "expenditure_prev1": item.expenditure_prev1 or 0,
        "budget_estimate_curr": item.budget_estimate_curr or 0,
        "revised_demand_curr": item.revised_demand_curr or 0,
        "budget_estimate_next": item.budget_estimate_next or 0,
        "remarks": item.remarks or "",
    })


@router.get("/totals", response_class=HTMLResponse)
async def ui_totals_2215(
    request: Request,
    db: Session = Depends(get_db),
):
    """Totals view for scheme 2215 - displays separate totals for each account head."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    # Resolve dynamic fiscal year labels
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2215(relative_years)
    
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
            "expenditure_prev3": sum(item.expenditure_prev3 or 0 for item in items),
            "expenditure_prev2": sum(item.expenditure_prev2 or 0 for item in items),
            "expenditure_prev1": sum(item.expenditure_prev1 or 0 for item in items),
            "budget_estimate_curr": sum(item.budget_estimate_curr or 0 for item in items),
            "revised_demand_curr": sum(item.revised_demand_curr or 0 for item in items),
            "budget_estimate_next": sum(item.budget_estimate_next or 0 for item in items),
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
        "relative_years": relative_years,
        "fy_labels": fy_labels,
    }
    context.update(get_standard_template_context(request))

    return render(request, 
        "schemes/s2215/subs/s2215/totals.html",
        context,
    )


@router.get("/export")
async def ui_export_excel(
    request: Request,
    db: Session = Depends(get_db),
):
    """Export combined 2245-2215 budget data to Excel."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    from src.schemes.s2245_2215 import export_combined_workbook_async
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    return await export_combined_workbook_async(db, fiscal_year)
