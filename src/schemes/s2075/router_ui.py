"""UI routes for scheme 2075 - Miscellaneous General Services.

Production-grade implementation with:
- Proper authentication checks
- Timing validation for data filling
- Centralized audit logging
- Cache invalidation on updates
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.templates import templates
from src.core.template_context import get_standard_template_context
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.utils_auth import get_auth_unit, get_auth_role, get_auth_level, is_authenticated
from .fiscal_year_labels import FiscalYearLabels2075
from src.utils_timing import check_data_filling_allowed
from .models import SubHeadExpenditure2075, DistrictExpenditure2075
from .helpers import (
    check_dco_access, 
    get_allowed_districts, 
    check_edit_permission_for_scheme,
    validate_numeric_input, 
    ensure_sub_head_seeded,
    ensure_districts_seeded, 
    get_aggregated_totals,
    invalidate_scheme_cache,
    log_audit
)
from .config import SCHEME_CONFIG
from .excel_export import export_2075_workbook_async

router = APIRouter(
    prefix="/ui/s2075/expenditure", 
    tags=[f"UI - {SCHEME_CONFIG.name_mr}"], 
    include_in_schema=False
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_auth_context(request: Request) -> tuple:
    """Extract authentication context from request."""
    return (
        get_auth_role(request),
        get_auth_level(request),
        get_auth_unit(request)
    )


def _validate_timing(db: Session, auth_level: str, auth_role: str) -> None:
    """Validate data filling timing for assistants."""
    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=timing_msg or "डेटा भरण्याचा कालावधी संपला"
            )


# ============================================================================
# LIST VIEW
# ============================================================================

@router.get("", response_class=HTMLResponse)
async def ui_list_expenditure(request: Request, db: Session = Depends(get_db)):
    """Render expenditure list page."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    auth_role, auth_level, auth_unit = _get_auth_context(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    
    # Ensure data is seeded
    ensure_sub_head_seeded(db, fiscal_year)
    ensure_districts_seeded(db, fiscal_year)
    
    # Resolve dynamic fiscal year labels (single computation, zero duplication)
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2075(relative_years)
    
    # Get aggregated totals (cached)
    aggregates = get_aggregated_totals(db, fiscal_year)
    
    # Get sub-head record (DCO only)
    sub_head = None
    if check_dco_access(auth_level):
        sub_head = db.query(SubHeadExpenditure2075).filter(
            SubHeadExpenditure2075.fiscal_year == fiscal_year,
            SubHeadExpenditure2075.sub_scheme_code == "20750249",
        ).first()
    
    # Get district records (filtered by access)
    allowed_districts = get_allowed_districts(auth_level, auth_unit)
    district_items = []
    if allowed_districts:
        district_items = db.query(DistrictExpenditure2075).filter(
            DistrictExpenditure2075.fiscal_year == fiscal_year,
            DistrictExpenditure2075.sub_scheme_code == "20750294",
            DistrictExpenditure2075.district.in_(allowed_districts),
        ).order_by(DistrictExpenditure2075.district).all()
    
    context = {
        "request": request,
        "resource_name": f"{SCHEME_CONFIG.code} {SCHEME_CONFIG.name_mr}",
        "aggregates": aggregates,
        "sub_head": sub_head,
        "district_items": district_items,
        "can_edit": check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db),
        "show_sub_head": check_dco_access(auth_level),
        "fiscal_year": fiscal_year,
        "relative_years": relative_years,
        "fy_labels": fy_labels,
    }
    context.update(get_standard_template_context(request))
    
    return templates.TemplateResponse("schemes/s2075/subs/s2075/expenditure_list.html", context)


# ============================================================================
# INLINE UPDATE
# ============================================================================

@router.post("/update", response_class=JSONResponse)
async def ui_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    record_id: int = Form(...),
    record_type: str = Form(...),
    expenditure_prev3: Optional[str] = Form(None),
    expenditure_prev2: Optional[str] = Form(None),
    expenditure_prev1: Optional[str] = Form(None),
    budget_estimate_curr: Optional[str] = Form(None),
    revised_estimate_curr: Optional[str] = Form(None),
    budget_estimate_next: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
):
    """Update sub-head or district expenditure via inline editing."""
    auth_role, auth_level, auth_unit = _get_auth_context(request)
    
    # Permission check
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="संपादन अधिकार नाही")
    
    # Timing validation
    _validate_timing(db, auth_level, auth_role)
    
    # Validate and parse inputs
    parsed_values = {
        "expenditure_prev3": validate_numeric_input(expenditure_prev3, "expenditure_prev3"),
        "expenditure_prev2": validate_numeric_input(expenditure_prev2, "expenditure_prev2"),
        "expenditure_prev1": validate_numeric_input(expenditure_prev1, "expenditure_prev1"),
        "budget_estimate_curr": validate_numeric_input(budget_estimate_curr, "budget_estimate_curr"),
        "revised_estimate_curr": validate_numeric_input(revised_estimate_curr, "revised_estimate_curr"),
        "budget_estimate_next": validate_numeric_input(budget_estimate_next, "budget_estimate_next"),
    }
    
    if record_type == "sub_head":
        return _update_sub_head(request, db, record_id, parsed_values, remarks)
    elif record_type == "district":
        return _update_district(request, db, record_id, parsed_values, remarks, auth_level, auth_unit)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="अवैध नोंद प्रकार")


def _update_sub_head(request: Request, db: Session, record_id: int, 
                     values: dict, remarks: Optional[str]) -> JSONResponse:
    """Update sub-head record."""
    auth_level = get_auth_level(request)
    
    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="केवळ DCO साठी")
    
    item = db.query(SubHeadExpenditure2075).filter(
        SubHeadExpenditure2075.id == record_id,
        SubHeadExpenditure2075.sub_scheme_code == "20750249",
    ).first()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="नोंद सापडली नाही")
    
    # Capture old values for audit
    audit_fields = list(values.keys()) + ["remarks"]
    old_vals = {k: getattr(item, k) for k in audit_fields}
    
    # Apply updates
    for key, value in values.items():
        setattr(item, key, value)
    item.remarks = remarks.strip() if remarks else None
    
    db.commit()
    db.refresh(item)
    
    # Audit and cache invalidation
    new_vals = {k: getattr(item, k) for k in audit_fields}
    log_audit(db, request, "sub_head_expenditure_2075", item.id, old_vals, new_vals)
    invalidate_scheme_cache()
    
    return JSONResponse({"success": True, "message": "उपशिर्ष डेटा यशस्वीरित्या अपडेट झाला"})


def _update_district(request: Request, db: Session, record_id: int,
                     values: dict, remarks: Optional[str], 
                     auth_level: str, auth_unit: str) -> JSONResponse:
    """Update district record."""
    item = db.query(DistrictExpenditure2075).filter(
        DistrictExpenditure2075.id == record_id,
        DistrictExpenditure2075.sub_scheme_code == "20750294",
    ).first()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="नोंद सापडली नाही")
    
    # Access check
    allowed = get_allowed_districts(auth_level, auth_unit)
    if item.district not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="या जिल्ह्यासाठी प्रवेश नाही")
    
    # Capture old values for audit
    audit_fields = list(values.keys()) + ["remarks"]
    old_vals = {k: getattr(item, k) for k in audit_fields}
    
    # Apply updates
    for key, value in values.items():
        setattr(item, key, value)
    item.remarks = remarks.strip() if remarks else None
    
    db.commit()
    db.refresh(item)
    
    # Audit and cache invalidation
    new_vals = {k: getattr(item, k) for k in audit_fields}
    log_audit(db, request, "district_expenditure_2075", item.id, old_vals, new_vals)
    invalidate_scheme_cache(item.district)
    
    return JSONResponse({"success": True, "message": "जिल्हा डेटा यशस्वीरित्या अपडेट झाला"})


# ============================================================================
# RECORD DATA API (for inline edit form population)
# ============================================================================

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(
    request: Request,
    db: Session = Depends(get_db),
    record_type: str = Query(...),
    record_id: int = Query(...),
):
    """Fetch record data for inline editing form."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    
    if record_type == "sub_head":
        return _get_sub_head_data(db, record_id, fiscal_year, auth_level)
    elif record_type == "district":
        return _get_district_data(db, record_id, fiscal_year, auth_level, auth_unit)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="अवैध नोंद प्रकार")


def _get_sub_head_data(db: Session, record_id: int, fiscal_year: str, auth_level: str) -> JSONResponse:
    """Get sub-head record data for form."""
    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="केवळ DCO साठी")
    
    item = db.query(SubHeadExpenditure2075).filter(
        SubHeadExpenditure2075.id == record_id,
        SubHeadExpenditure2075.fiscal_year == fiscal_year,
        SubHeadExpenditure2075.sub_scheme_code == "20750249",
    ).first()
    
    if not item:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True,
        "id": item.id,
        "expenditure_prev3": int(item.expenditure_prev3 or 0),
        "expenditure_prev2": int(item.expenditure_prev2 or 0),
        "expenditure_prev1": int(item.expenditure_prev1 or 0),
        "budget_estimate_curr": int(item.budget_estimate_curr or 0),
        "revised_estimate_curr": int(item.revised_estimate_curr or 0),
        "budget_estimate_next": int(item.budget_estimate_next or 0),
        "remarks": item.remarks or "",
    })


def _get_district_data(db: Session, record_id: int, fiscal_year: str, 
                       auth_level: str, auth_unit: str) -> JSONResponse:
    """Get district record data for form."""
    item = db.query(DistrictExpenditure2075).filter(
        DistrictExpenditure2075.id == record_id,
        DistrictExpenditure2075.fiscal_year == fiscal_year,
        DistrictExpenditure2075.sub_scheme_code == "20750294",
    ).first()
    
    if not item:
        return JSONResponse({"found": False})
    
    allowed = get_allowed_districts(auth_level, auth_unit)
    if item.district not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="प्रवेश नाही")
    
    return JSONResponse({
        "found": True,
        "id": item.id,
        "district": item.district,
        "expenditure_prev3": int(item.expenditure_prev3 or 0),
        "expenditure_prev2": int(item.expenditure_prev2 or 0),
        "expenditure_prev1": int(item.expenditure_prev1 or 0),
        "budget_estimate_curr": int(item.budget_estimate_curr or 0),
        "revised_estimate_curr": int(item.revised_estimate_curr or 0),
        "budget_estimate_next": int(item.budget_estimate_next or 0),
        "remarks": item.remarks or "",
    })


# ============================================================================
# EXCEL EXPORT
# ============================================================================

@router.get("/download", response_class=StreamingResponse)
async def download_2075_excel(request: Request, db: Session = Depends(get_db)):
    """Download Excel workbook with all 2075 scheme data."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    fiscal_year = get_fiscal_year_from_request(request, db)
    
    # Ensure data is seeded before export
    ensure_sub_head_seeded(db, fiscal_year)
    ensure_districts_seeded(db, fiscal_year)
    
    return await export_2075_workbook_async(db, fiscal_year)
