"""UI routes for scheme 0029 Section 1 - district-wise revenue."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from src.config import DISTRICTS_MR
from src.database import get_db
from src.core.templates import templates
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_taluka import is_taluka_allowed
from .models import DistrictRevenue0029, SUB_SCHEME_CODE
from .config import get_all_table_sections, get_table_section
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    check_dco_access,
    validate_access_control,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)
from src.utils_auth import get_auth_unit


router = APIRouter(
    prefix="/ui/s0029/section1",
    tags=["UI - 0029 महसूल जमा - अर्थसंकल्पीय जिल्हा"],
    include_in_schema=False,
)


@router.get("", response_class=HTMLResponse)
async def ui_list_section1(
    request: Request,
    db: Session = Depends(get_db),
    table_section: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)

    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)

    all_table_sections = get_all_table_sections()
    
    all_allowed_districts = set()
    for section in all_table_sections:
        allowed = get_allowed_districts_for_user(auth_level, auth_unit, section["code"])
        all_allowed_districts.update(allowed)
    
    districts_for_filter = sorted(list(all_allowed_districts))
    
    if auth_level == "district" and auth_unit:
        districts_for_filter = [d for d in districts_for_filter if d == auth_unit]
    elif auth_level == "taluka" and auth_unit:
        from src.utils_district import get_district_from_taluka
        district_name = get_district_from_taluka(auth_unit)
        districts_for_filter = [d for d in districts_for_filter if d == district_name]

    tables_data = []
    sections_to_process = all_table_sections

    if table_section:
        sections_to_process = [s for s in all_table_sections if s["code"] == table_section]
        if not sections_to_process:
            sections_to_process = all_table_sections

    for section in sections_to_process:
        allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, section["code"])
        if not allowed_districts:
            continue

        query = (
            db.query(DistrictRevenue0029)
            .filter(
                DistrictRevenue0029.fiscal_year == fiscal_year,
                DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictRevenue0029.table_section_code == section["code"],
                DistrictRevenue0029.district.in_(allowed_districts),
            )
        )

        if district and district in allowed_districts:
            query = query.filter(DistrictRevenue0029.district == district)

        items = query.order_by(DistrictRevenue0029.district).all()

        if not items:
            continue

        totals = {
            "actual_2017_18": sum(item.actual_2017_18 or 0 for item in items),
            "actual_2018_19": sum(item.actual_2018_19 or 0 for item in items),
            "actual_2019_20": sum(item.actual_2019_20 or 0 for item in items),
            "budget_estimate_2020_21": sum(item.budget_estimate_2020_21 or 0 for item in items),
            "revised_estimate_2020_21": sum(item.revised_estimate_2020_21 or 0 for item in items),
            "budget_estimate_2021_22": sum(item.budget_estimate_2021_22 or 0 for item in items),
        }

        tables_data.append({
            "section": section,
            "items": items,
            "totals": totals,
        })

    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)

    districts_mr = DISTRICTS_MR.copy()

    context = {
        "request": request,
        "tables_data": tables_data,
        "can_edit": can_edit,
        "resource_name": "0029 महसूल जमा - अर्थसंकल्पीय जिल्हा",
        "districts_mr": districts_mr,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "table_sections": all_table_sections,
        "districts": districts_for_filter,
        "current_table_section": table_section,
        "current_district": district,
    }

    return templates.TemplateResponse(
        "schemes/s0029/subs/s0029/section1_list.html",
        context,
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_section1_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)

    item = (
        db.query(DistrictRevenue0029)
        .filter(
            DistrictRevenue0029.id == id,
            DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, item.table_section_code)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    section = get_table_section(item.table_section_code)
    districts_mr = DISTRICTS_MR.copy()

    auth_role = request.cookies.get("auth_role", "")
    context = {
        "request": request,
        "item": item,
        "section": section,
        "districts": allowed_districts,
        "resource_name": "0029 महसूल जमा - अर्थसंकल्पीय जिल्हा संपादन",
        "districts_mr": districts_mr,
        "auth_level": auth_level,
        "auth_role": auth_role,
    }
    return templates.TemplateResponse(
        "schemes/s0029/subs/s0029/section1_form.html",
        context,
    )


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_section1(
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=timing_msg or "Data filling period has expired",
            )

    item = (
        db.query(DistrictRevenue0029)
        .filter(
            DistrictRevenue0029.id == id,
            DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, item.table_section_code)
    form = await request.form()
    district = form.get("District")

    if not district or district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    if district != item.district:
        existing = (
            db.query(DistrictRevenue0029)
            .filter(
                DistrictRevenue0029.fiscal_year == item.fiscal_year,
                DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictRevenue0029.table_section_code == item.table_section_code,
                DistrictRevenue0029.district == district,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Record already exists for this table section, district and fiscal year",
            )

    old_vals = {
        "table_section_code": item.table_section_code,
        "district": item.district,
        "actual_2017_18": item.actual_2017_18,
        "actual_2018_19": item.actual_2018_19,
        "actual_2019_20": item.actual_2019_20,
        "budget_estimate_2020_21": item.budget_estimate_2020_21,
        "revised_estimate_2020_21": item.revised_estimate_2020_21,
        "budget_estimate_2021_22": item.budget_estimate_2021_22,
    }

    item.district = district
    item.actual_2017_18 = validate_numeric_input(form.get("Actual2017_18"), "Actual2017_18")
    item.actual_2018_19 = validate_numeric_input(form.get("Actual2018_19"), "Actual2018_19")
    item.actual_2019_20 = validate_numeric_input(form.get("Actual2019_20"), "Actual2019_20")
    item.budget_estimate_2020_21 = validate_numeric_input(form.get("BudgetEstimate2020_21"), "BudgetEstimate2020_21")
    item.revised_estimate_2020_21 = validate_numeric_input(form.get("RevisedEstimate2020_21"), "RevisedEstimate2020_21")
    item.budget_estimate_2021_22 = validate_numeric_input(
        form.get("BudgetEstimate2021_22"),
        "BudgetEstimate2021_22",
    )

    new_vals = {
        "table_section_code": item.table_section_code,
        "district": item.district,
        "actual_2017_18": item.actual_2017_18,
        "actual_2018_19": item.actual_2018_19,
        "actual_2019_20": item.actual_2019_20,
        "budget_estimate_2020_21": item.budget_estimate_2020_21,
        "revised_estimate_2020_21": item.revised_estimate_2020_21,
        "budget_estimate_2021_22": item.budget_estimate_2021_22,
    }

    db.commit()
    db.refresh(item)

    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_revenue_0029",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )

    return RedirectResponse(
        url=router.url_path_for("ui_list_section1"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/api/record-data")
async def api_get_record_data(
    request: Request,
    table_section: str = Query(...),
    district: str = Query(...),
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, table_section)
    if district not in allowed_districts:
        return JSONResponse({"found": False}, status_code=403)
    
    record = (
        db.query(DistrictRevenue0029)
        .filter(
            DistrictRevenue0029.fiscal_year == fiscal_year,
            DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictRevenue0029.table_section_code == table_section,
            DistrictRevenue0029.district == district,
        )
        .first()
    )
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True,
        "id": record.id,
        "actual_2017_18": record.actual_2017_18 or 0,
        "actual_2018_19": record.actual_2018_19 or 0,
        "actual_2019_20": record.actual_2019_20 or 0,
        "budget_estimate_2020_21": record.budget_estimate_2020_21 or 0,
        "revised_estimate_2020_21": record.revised_estimate_2020_21 or 0,
        "budget_estimate_2021_22": record.budget_estimate_2021_22 or 0,
    })


@router.post("/api/update-inline")
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    Actual2017_18: int = Form(0),
    Actual2018_19: int = Form(0),
    Actual2019_20: int = Form(0),
    BudgetEstimate2020_21: int = Form(0),
    RevisedEstimate2020_21: int = Form(0),
    BudgetEstimate2021_22: int = Form(0),
):
    from src.utils_timing import check_data_filling_allowed
    
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    record = (
        db.query(DistrictRevenue0029)
        .filter(
            DistrictRevenue0029.id == id,
            DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, record.table_section_code)
    if record.district not in allowed_districts:
        return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    
    allowed, error_msg = validate_access_control(record.district, auth_level, auth_unit, db)
    if not allowed:
        return JSONResponse({"success": False, "message": error_msg or "Access denied"}, status_code=403)
    
    old_vals = {
        "actual_2017_18": record.actual_2017_18,
        "actual_2018_19": record.actual_2018_19,
        "actual_2019_20": record.actual_2019_20,
        "budget_estimate_2020_21": record.budget_estimate_2020_21,
        "revised_estimate_2020_21": record.revised_estimate_2020_21,
        "budget_estimate_2021_22": record.budget_estimate_2021_22,
    }
    
    record.actual_2017_18 = validate_numeric_input(Actual2017_18, "Actual2017_18")
    record.actual_2018_19 = validate_numeric_input(Actual2018_19, "Actual2018_19")
    record.actual_2019_20 = validate_numeric_input(Actual2019_20, "Actual2019_20")
    record.budget_estimate_2020_21 = validate_numeric_input(BudgetEstimate2020_21, "BudgetEstimate2020_21")
    record.revised_estimate_2020_21 = validate_numeric_input(RevisedEstimate2020_21, "RevisedEstimate2020_21")
    record.budget_estimate_2021_22 = validate_numeric_input(BudgetEstimate2021_22, "BudgetEstimate2021_22")
    
    db.commit()
    db.refresh(record)
    
    new_vals = {
        "actual_2017_18": record.actual_2017_18,
        "actual_2018_19": record.actual_2018_19,
        "actual_2019_20": record.actual_2019_20,
        "budget_estimate_2020_21": record.budget_estimate_2020_21,
        "revised_estimate_2020_21": record.revised_estimate_2020_21,
        "budget_estimate_2021_22": record.budget_estimate_2021_22,
    }
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_revenue_0029",
        record_id=record.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})


@router.get("/section2", response_class=HTMLResponse)
async def ui_list_section2(
    request: Request,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)
    
    all_table_sections = get_all_table_sections()
    
    summary_rows = []
    grand_totals = {
        "actual_2017_18": 0,
        "actual_2018_19": 0,
        "actual_2019_20": 0,
        "budget_estimate_2020_21": 0,
        "revised_estimate_2020_21": 0,
        "budget_estimate_2021_22": 0,
    }
    
    for idx, section in enumerate(all_table_sections, 1):
        allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, section["code"])
        if not allowed_districts:
            continue
        
        query = (
            db.query(DistrictRevenue0029)
            .filter(
                DistrictRevenue0029.fiscal_year == fiscal_year,
                DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictRevenue0029.table_section_code == section["code"],
                DistrictRevenue0029.district.in_(allowed_districts),
            )
        )
        
        items = query.all()
        
        totals = {
            "actual_2017_18": sum(item.actual_2017_18 or 0 for item in items),
            "actual_2018_19": sum(item.actual_2018_19 or 0 for item in items),
            "actual_2019_20": sum(item.actual_2019_20 or 0 for item in items),
            "budget_estimate_2020_21": sum(item.budget_estimate_2020_21 or 0 for item in items),
            "revised_estimate_2020_21": sum(item.revised_estimate_2020_21 or 0 for item in items),
            "budget_estimate_2021_22": sum(item.budget_estimate_2021_22 or 0 for item in items),
        }
        
        grand_totals["actual_2017_18"] += totals["actual_2017_18"]
        grand_totals["actual_2018_19"] += totals["actual_2018_19"]
        grand_totals["actual_2019_20"] += totals["actual_2019_20"]
        grand_totals["budget_estimate_2020_21"] += totals["budget_estimate_2020_21"]
        grand_totals["revised_estimate_2020_21"] += totals["revised_estimate_2020_21"]
        grand_totals["budget_estimate_2021_22"] += totals["budget_estimate_2021_22"]
        
        summary_rows.append({
            "sr_no": idx,
            "section": section,
            "totals": totals,
        })
    
    context = {
        "request": request,
        "summary_rows": summary_rows,
        "grand_totals": grand_totals,
        "resource_name": "0029 महसूल जमा - अर्थसंकल्पीय जिल्हा 2",
        "auth_level": auth_level,
    }
    
    return templates.TemplateResponse(
        "schemes/s0029/subs/s0029/section2_list.html",
        context,
    )


@router.get("/export")
async def ui_export_excel(
    request: Request,
    db: Session = Depends(get_db),
):
    """Export district revenue data to Excel."""
    from .excel_export import export_original_workbook
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    return export_original_workbook(db, fiscal_year)
