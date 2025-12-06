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
from .models import DistrictRevenue0029, DistrictRevenue0029Section3, DistrictRevenue0029Section4, DistrictRevenue0029JamaTalmel, SUB_SCHEME_CODE
from .config import get_all_table_sections, get_table_section, get_section3_table_sections, get_section3_table_section, get_section4_table_sections, get_section4_table_section, get_jama_talmel_table_sections, get_jama_talmel_table_section, JAMA_TALMEL_DISTRICTS, JAMA_TALMEL_DISTRICTS_MR, KONKAN_DISTRICTS
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    check_edit_permission_for_section3,
    check_edit_permission_for_section5,
    check_dco_access,
    validate_access_control,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
    ensure_fiscal_year_seeded_section3,
    ensure_fiscal_year_seeded_section4,
    ensure_fiscal_year_seeded_jama_talmel,
    get_user_editable_districts,
)


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
    auth_unit = request.cookies.get("auth_unit", "")

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
    auth_unit = request.cookies.get("auth_unit", "")

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
    auth_unit = request.cookies.get("auth_unit") or ""

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

    if auth_level == "taluka" and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Taluka not allowed")

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
        "remarks": item.remarks,
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
    item.remarks = (form.get("Remarks") or "").strip() or None

    new_vals = {
        "table_section_code": item.table_section_code,
        "district": item.district,
        "actual_2017_18": item.actual_2017_18,
        "actual_2018_19": item.actual_2018_19,
        "actual_2019_20": item.actual_2019_20,
        "budget_estimate_2020_21": item.budget_estimate_2020_21,
        "revised_estimate_2020_21": item.revised_estimate_2020_21,
        "budget_estimate_2021_22": item.budget_estimate_2021_22,
        "remarks": item.remarks,
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
    auth_unit = request.cookies.get("auth_unit", "")
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
        "remarks": record.remarks or "",
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
    Remarks: str = Form(""),
):
    from src.utils_timing import check_data_filling_allowed
    
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
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
        "remarks": record.remarks,
    }
    
    record.actual_2017_18 = validate_numeric_input(Actual2017_18, "Actual2017_18")
    record.actual_2018_19 = validate_numeric_input(Actual2018_19, "Actual2018_19")
    record.actual_2019_20 = validate_numeric_input(Actual2019_20, "Actual2019_20")
    record.budget_estimate_2020_21 = validate_numeric_input(BudgetEstimate2020_21, "BudgetEstimate2020_21")
    record.revised_estimate_2020_21 = validate_numeric_input(RevisedEstimate2020_21, "RevisedEstimate2020_21")
    record.budget_estimate_2021_22 = validate_numeric_input(BudgetEstimate2021_22, "BudgetEstimate2021_22")
    record.remarks = Remarks.strip() or None
    
    db.commit()
    db.refresh(record)
    
    new_vals = {
        "actual_2017_18": record.actual_2017_18,
        "actual_2018_19": record.actual_2018_19,
        "actual_2019_20": record.actual_2019_20,
        "budget_estimate_2020_21": record.budget_estimate_2020_21,
        "revised_estimate_2020_21": record.revised_estimate_2020_21,
        "budget_estimate_2021_22": record.budget_estimate_2021_22,
        "remarks": record.remarks,
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
    auth_unit = request.cookies.get("auth_unit", "")
    
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


@router.get("/section3", response_class=HTMLResponse)
async def ui_list_section3(
    request: Request,
    db: Session = Depends(get_db),
    table_section: Optional[str] = Query(None),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    auth_role = request.cookies.get("auth_role", "")
    
    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO level required")
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded_section3(db, fiscal_year)
    
    section3_sections = get_section3_table_sections()
    
    sections_to_process = section3_sections
    if table_section:
        sections_to_process = [s for s in section3_sections if s["code"] == table_section]
        if not sections_to_process:
            sections_to_process = section3_sections
    
    summary_rows = []
    grand_totals = {
        "actual_2014_15": 0,
        "actual_2015_16": 0,
        "actual_2016_17": 0,
        "budget_estimate_2017_18": 0,
        "revised_estimate_2017_18": 0,
        "budget_estimate_2018_19": 0,
    }
    
    for idx, section in enumerate(sections_to_process, 1):
        record = (
            db.query(DistrictRevenue0029Section3)
            .filter(
                DistrictRevenue0029Section3.fiscal_year == fiscal_year,
                DistrictRevenue0029Section3.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictRevenue0029Section3.table_section_code == section["code"],
            )
            .first()
        )
        
        if not record:
            totals = {
                "actual_2014_15": 0,
                "actual_2015_16": 0,
                "actual_2016_17": 0,
                "budget_estimate_2017_18": 0,
                "revised_estimate_2017_18": 0,
                "budget_estimate_2018_19": 0,
            }
        else:
            totals = {
                "actual_2014_15": record.actual_2014_15 or 0,
                "actual_2015_16": record.actual_2015_16 or 0,
                "actual_2016_17": record.actual_2016_17 or 0,
                "budget_estimate_2017_18": record.budget_estimate_2017_18 or 0,
                "revised_estimate_2017_18": record.revised_estimate_2017_18 or 0,
                "budget_estimate_2018_19": record.budget_estimate_2018_19 or 0,
            }
        
        grand_totals["actual_2014_15"] += totals["actual_2014_15"]
        grand_totals["actual_2015_16"] += totals["actual_2015_16"]
        grand_totals["actual_2016_17"] += totals["actual_2016_17"]
        grand_totals["budget_estimate_2017_18"] += totals["budget_estimate_2017_18"]
        grand_totals["revised_estimate_2017_18"] += totals["revised_estimate_2017_18"]
        grand_totals["budget_estimate_2018_19"] += totals["budget_estimate_2018_19"]
        
        original_idx = next((i for i, s in enumerate(section3_sections, 1) if s["code"] == section["code"]), idx)
        
        summary_rows.append({
            "sr_no": original_idx,
            "section": section,
            "record_id": record.id if record else None,
            "totals": totals,
        })
    
    can_edit = check_edit_permission_for_section3(auth_role, auth_level, auth_unit, db)
    
    context = {
        "request": request,
        "summary_rows": summary_rows,
        "grand_totals": grand_totals,
        "can_edit": can_edit,
        "resource_name": "0029 महसूल जमा - अर्थसंकल्पीय जिल्हा 3",
        "auth_level": auth_level,
        "auth_role": auth_role,
        "table_sections": section3_sections,
        "current_table_section": table_section,
    }
    
    return templates.TemplateResponse(
        "schemes/s0029/subs/s0029/section3_list.html",
        context,
    )


@router.get("/section3/api/get-record")
async def api_get_record_section3(
    request: Request,
    id: int = Query(...),
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    
    if not check_dco_access(auth_level):
        return JSONResponse({"found": False}, status_code=403)
    
    record = (
        db.query(DistrictRevenue0029Section3)
        .filter(
            DistrictRevenue0029Section3.id == id,
            DistrictRevenue0029Section3.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    
    if not record:
        return JSONResponse({"found": False}, status_code=404)
    
    return JSONResponse({
        "found": True,
        "id": record.id,
        "table_section_code": record.table_section_code,
        "actual_2014_15": record.actual_2014_15 or 0,
        "actual_2015_16": record.actual_2015_16 or 0,
        "actual_2016_17": record.actual_2016_17 or 0,
        "budget_estimate_2017_18": record.budget_estimate_2017_18 or 0,
        "revised_estimate_2017_18": record.revised_estimate_2017_18 or 0,
        "budget_estimate_2018_19": record.budget_estimate_2018_19 or 0,
        "remarks": record.remarks or "",
    })


@router.get("/section3/api/get-record-by-section")
async def api_get_record_by_section_section3(
    request: Request,
    table_section: str = Query(...),
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    
    if not check_dco_access(auth_level):
        return JSONResponse({"found": False}, status_code=403)
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    
    record = (
        db.query(DistrictRevenue0029Section3)
        .filter(
            DistrictRevenue0029Section3.fiscal_year == fiscal_year,
            DistrictRevenue0029Section3.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictRevenue0029Section3.table_section_code == table_section,
        )
        .first()
    )
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True,
        "id": record.id,
        "table_section_code": record.table_section_code,
        "actual_2014_15": record.actual_2014_15 or 0,
        "actual_2015_16": record.actual_2015_16 or 0,
        "actual_2016_17": record.actual_2016_17 or 0,
        "budget_estimate_2017_18": record.budget_estimate_2017_18 or 0,
        "revised_estimate_2017_18": record.revised_estimate_2017_18 or 0,
        "budget_estimate_2018_19": record.budget_estimate_2018_19 or 0,
        "remarks": record.remarks or "",
    })


@router.post("/section3/api/update-inline")
async def api_update_inline_section3(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    Actual2014_15: int = Form(0),
    Actual2015_16: int = Form(0),
    Actual2016_17: int = Form(0),
    BudgetEstimate2017_18: int = Form(0),
    RevisedEstimate2017_18: int = Form(0),
    BudgetEstimate2018_19: int = Form(0),
    Remarks: str = Form(""),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_section3(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden - Only DCO assistant can edit"}, status_code=403)
    
    record = (
        db.query(DistrictRevenue0029Section3)
        .filter(
            DistrictRevenue0029Section3.id == id,
            DistrictRevenue0029Section3.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    old_vals = {
        "actual_2014_15": record.actual_2014_15,
        "actual_2015_16": record.actual_2015_16,
        "actual_2016_17": record.actual_2016_17,
        "budget_estimate_2017_18": record.budget_estimate_2017_18,
        "revised_estimate_2017_18": record.revised_estimate_2017_18,
        "budget_estimate_2018_19": record.budget_estimate_2018_19,
        "remarks": record.remarks,
    }
    
    record.actual_2014_15 = validate_numeric_input(Actual2014_15, "Actual2014_15")
    record.actual_2015_16 = validate_numeric_input(Actual2015_16, "Actual2015_16")
    record.actual_2016_17 = validate_numeric_input(Actual2016_17, "Actual2016_17")
    record.budget_estimate_2017_18 = validate_numeric_input(BudgetEstimate2017_18, "BudgetEstimate2017_18")
    record.revised_estimate_2017_18 = validate_numeric_input(RevisedEstimate2017_18, "RevisedEstimate2017_18")
    record.budget_estimate_2018_19 = validate_numeric_input(BudgetEstimate2018_19, "BudgetEstimate2018_19")
    record.remarks = Remarks.strip() or None
    
    db.commit()
    db.refresh(record)
    
    new_vals = {
        "actual_2014_15": record.actual_2014_15,
        "actual_2015_16": record.actual_2015_16,
        "actual_2016_17": record.actual_2016_17,
        "budget_estimate_2017_18": record.budget_estimate_2017_18,
        "revised_estimate_2017_18": record.revised_estimate_2017_18,
        "budget_estimate_2018_19": record.budget_estimate_2018_19,
        "remarks": record.remarks,
    }
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_revenue_0029_section3",
        record_id=record.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})


@router.get("/section4", response_class=HTMLResponse)
async def ui_list_section4(
    request: Request,
    db: Session = Depends(get_db),
    table_section: Optional[str] = Query(None),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    auth_role = request.cookies.get("auth_role", "")
    
    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO level required")
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded_section4(db, fiscal_year)
    
    section4_sections = get_section4_table_sections()
    
    sections_to_process = section4_sections
    if table_section:
        sections_to_process = [s for s in section4_sections if s["code"] == table_section]
        if not sections_to_process:
            sections_to_process = section4_sections
    
    summary_rows = []
    grand_totals = {
        "actual_2011_12": 0,
        "actual_2012_13": 0,
        "actual_2013_14": 0,
        "budget_estimate_2014_15": 0,
        "revised_estimate_2014_15": 0,
        "budget_estimate_2015_16": 0,
    }
    
    for idx, section in enumerate(sections_to_process, 1):
        record = (
            db.query(DistrictRevenue0029Section4)
            .filter(
                DistrictRevenue0029Section4.fiscal_year == fiscal_year,
                DistrictRevenue0029Section4.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictRevenue0029Section4.table_section_code == section["code"],
            )
            .first()
        )
        
        if not record:
            totals = {
                "actual_2011_12": 0,
                "actual_2012_13": 0,
                "actual_2013_14": 0,
                "budget_estimate_2014_15": 0,
                "revised_estimate_2014_15": 0,
                "budget_estimate_2015_16": 0,
            }
        else:
            totals = {
                "actual_2011_12": record.actual_2011_12 or 0,
                "actual_2012_13": record.actual_2012_13 or 0,
                "actual_2013_14": record.actual_2013_14 or 0,
                "budget_estimate_2014_15": record.budget_estimate_2014_15 or 0,
                "revised_estimate_2014_15": record.revised_estimate_2014_15 or 0,
                "budget_estimate_2015_16": record.budget_estimate_2015_16 or 0,
            }
        
        grand_totals["actual_2011_12"] += totals["actual_2011_12"]
        grand_totals["actual_2012_13"] += totals["actual_2012_13"]
        grand_totals["actual_2013_14"] += totals["actual_2013_14"]
        grand_totals["budget_estimate_2014_15"] += totals["budget_estimate_2014_15"]
        grand_totals["revised_estimate_2014_15"] += totals["revised_estimate_2014_15"]
        grand_totals["budget_estimate_2015_16"] += totals["budget_estimate_2015_16"]
        
        original_idx = next((i for i, s in enumerate(section4_sections, 1) if s["code"] == section["code"]), idx)
        
        summary_rows.append({
            "sr_no": original_idx,
            "section": section,
            "record_id": record.id if record else None,
            "totals": totals,
        })
    
    can_edit = check_edit_permission_for_section3(auth_role, auth_level, auth_unit, db)
    
    context = {
        "request": request,
        "summary_rows": summary_rows,
        "grand_totals": grand_totals,
        "can_edit": can_edit,
        "resource_name": "0029 महसूल जमा - अर्थसंकल्पीय जिल्हा 4",
        "auth_level": auth_level,
        "auth_role": auth_role,
        "table_sections": section4_sections,
        "current_table_section": table_section,
    }
    
    return templates.TemplateResponse(
        "schemes/s0029/subs/s0029/section4_list.html",
        context,
    )


@router.get("/section4/api/get-record")
async def api_get_record_section4(
    request: Request,
    id: int = Query(...),
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    
    if not check_dco_access(auth_level):
        return JSONResponse({"found": False}, status_code=403)
    
    record = (
        db.query(DistrictRevenue0029Section4)
        .filter(
            DistrictRevenue0029Section4.id == id,
            DistrictRevenue0029Section4.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    
    if not record:
        return JSONResponse({"found": False}, status_code=404)
    
    return JSONResponse({
        "found": True,
        "id": record.id,
        "table_section_code": record.table_section_code,
        "actual_2011_12": record.actual_2011_12 or 0,
        "actual_2012_13": record.actual_2012_13 or 0,
        "actual_2013_14": record.actual_2013_14 or 0,
        "budget_estimate_2014_15": record.budget_estimate_2014_15 or 0,
        "revised_estimate_2014_15": record.revised_estimate_2014_15 or 0,
        "budget_estimate_2015_16": record.budget_estimate_2015_16 or 0,
        "remarks": record.remarks or "",
    })


@router.get("/section4/api/get-record-by-section")
async def api_get_record_by_section_section4(
    request: Request,
    table_section: str = Query(...),
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    
    if not check_dco_access(auth_level):
        return JSONResponse({"found": False}, status_code=403)
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    
    record = (
        db.query(DistrictRevenue0029Section4)
        .filter(
            DistrictRevenue0029Section4.fiscal_year == fiscal_year,
            DistrictRevenue0029Section4.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictRevenue0029Section4.table_section_code == table_section,
        )
        .first()
    )
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True,
        "id": record.id,
        "table_section_code": record.table_section_code,
        "actual_2011_12": record.actual_2011_12 or 0,
        "actual_2012_13": record.actual_2012_13 or 0,
        "actual_2013_14": record.actual_2013_14 or 0,
        "budget_estimate_2014_15": record.budget_estimate_2014_15 or 0,
        "revised_estimate_2014_15": record.revised_estimate_2014_15 or 0,
        "budget_estimate_2015_16": record.budget_estimate_2015_16 or 0,
        "remarks": record.remarks or "",
    })


@router.post("/section4/api/update-inline")
async def api_update_inline_section4(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    Actual2011_12: int = Form(0),
    Actual2012_13: int = Form(0),
    Actual2013_14: int = Form(0),
    BudgetEstimate2014_15: int = Form(0),
    RevisedEstimate2014_15: int = Form(0),
    BudgetEstimate2015_16: int = Form(0),
    Remarks: str = Form(""),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_section3(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden - Only DCO assistant can edit"}, status_code=403)
    
    record = (
        db.query(DistrictRevenue0029Section4)
        .filter(
            DistrictRevenue0029Section4.id == id,
            DistrictRevenue0029Section4.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    old_vals = {
        "actual_2011_12": record.actual_2011_12,
        "actual_2012_13": record.actual_2012_13,
        "actual_2013_14": record.actual_2013_14,
        "budget_estimate_2014_15": record.budget_estimate_2014_15,
        "revised_estimate_2014_15": record.revised_estimate_2014_15,
        "budget_estimate_2015_16": record.budget_estimate_2015_16,
        "remarks": record.remarks,
    }
    
    record.actual_2011_12 = validate_numeric_input(Actual2011_12, "Actual2011_12")
    record.actual_2012_13 = validate_numeric_input(Actual2012_13, "Actual2012_13")
    record.actual_2013_14 = validate_numeric_input(Actual2013_14, "Actual2013_14")
    record.budget_estimate_2014_15 = validate_numeric_input(BudgetEstimate2014_15, "BudgetEstimate2014_15")
    record.revised_estimate_2014_15 = validate_numeric_input(RevisedEstimate2014_15, "RevisedEstimate2014_15")
    record.budget_estimate_2015_16 = validate_numeric_input(BudgetEstimate2015_16, "BudgetEstimate2015_16")
    record.remarks = Remarks.strip() or None
    
    db.commit()
    db.refresh(record)
    
    new_vals = {
        "actual_2011_12": record.actual_2011_12,
        "actual_2012_13": record.actual_2012_13,
        "actual_2013_14": record.actual_2013_14,
        "budget_estimate_2014_15": record.budget_estimate_2014_15,
        "revised_estimate_2014_15": record.revised_estimate_2014_15,
        "budget_estimate_2015_16": record.budget_estimate_2015_16,
        "remarks": record.remarks,
    }
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_revenue_0029_section4",
        record_id=record.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})


@router.get("/section5", response_class=HTMLResponse)
async def ui_list_section5(
    request: Request,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    auth_role = request.cookies.get("auth_role", "")
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded_jama_talmel(db, fiscal_year)
    
    sections = get_jama_talmel_table_sections()
    can_edit = check_edit_permission_for_section5(auth_role, auth_level, auth_unit, db)
    
    user_district = None
    is_dco_assistant = check_dco_access(auth_level) and auth_role == "assistant"
    if not is_dco_assistant:
        if auth_level == "district" and auth_unit in JAMA_TALMEL_DISTRICTS:
            user_district = auth_unit
        elif auth_level == "taluka" and auth_unit:
            from src.utils_district import get_district_from_taluka
            district_name = get_district_from_taluka(auth_unit)
            if district_name and district_name in JAMA_TALMEL_DISTRICTS:
                user_district = district_name
    
    summary_rows = []
    grand_totals = {
        "mumbai_city": {"deposit": 0, "reconciliation": 0},
        "mumbai_suburban": {"deposit": 0, "reconciliation": 0},
        "thane": {"deposit": 0, "reconciliation": 0},
        "raigad": {"deposit": 0, "reconciliation": 0},
        "ratnagiri": {"deposit": 0, "reconciliation": 0},
        "sindhudurg": {"deposit": 0, "reconciliation": 0},
    }
    
    for idx, section in enumerate(sections, 1):
        record = (
            db.query(DistrictRevenue0029JamaTalmel)
            .filter(
                DistrictRevenue0029JamaTalmel.fiscal_year == fiscal_year,
                DistrictRevenue0029JamaTalmel.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictRevenue0029JamaTalmel.table_section_code == section["code"],
            )
            .first()
        )
        
        if not record:
            row_data = {
                "mumbai_city": {"deposit": 0, "reconciliation": 0},
                "mumbai_suburban": {"deposit": 0, "reconciliation": 0},
                "thane": {"deposit": 0, "reconciliation": 0},
                "raigad": {"deposit": 0, "reconciliation": 0},
                "ratnagiri": {"deposit": 0, "reconciliation": 0},
                "sindhudurg": {"deposit": 0, "reconciliation": 0},
            }
        else:
            row_data = {
                "mumbai_city": {
                    "deposit": record.mumbai_city_deposit or 0,
                    "reconciliation": record.mumbai_city_reconciliation or 0,
                },
                "mumbai_suburban": {
                    "deposit": record.mumbai_suburban_deposit or 0,
                    "reconciliation": record.mumbai_suburban_reconciliation or 0,
                },
                "thane": {
                    "deposit": record.thane_deposit or 0,
                    "reconciliation": record.thane_reconciliation or 0,
                },
                "raigad": {
                    "deposit": record.raigad_deposit or 0,
                    "reconciliation": record.raigad_reconciliation or 0,
                },
                "ratnagiri": {
                    "deposit": record.ratnagiri_deposit or 0,
                    "reconciliation": record.ratnagiri_reconciliation or 0,
                },
                "sindhudurg": {
                    "deposit": record.sindhudurg_deposit or 0,
                    "reconciliation": record.sindhudurg_reconciliation or 0,
                },
            }
        
        for district_key in grand_totals:
            grand_totals[district_key]["deposit"] += row_data[district_key]["deposit"]
            grand_totals[district_key]["reconciliation"] += row_data[district_key]["reconciliation"]
        
        summary_rows.append({
            "sr_no": idx,
            "section": section,
            "record_id": record.id if record else None,
            "data": row_data,
        })
    
    context = {
        "request": request,
        "summary_rows": summary_rows,
        "grand_totals": grand_totals,
        "can_edit": can_edit,
        "user_district": user_district,
        "is_dco_assistant": is_dco_assistant,
        "districts_mr": JAMA_TALMEL_DISTRICTS_MR,
        "all_districts": JAMA_TALMEL_DISTRICTS,
        "resource_name": "0029 महसूल जमा - जमा ताळमेळ",
        "auth_level": auth_level,
        "auth_role": auth_role,
        "fiscal_year": fiscal_year,
    }
    
    return templates.TemplateResponse(
        "schemes/s0029/subs/s0029/section5_list.html",
        context,
    )


@router.get("/section5/api/get-record-by-section")
async def api_get_record_by_section_section5(
    request: Request,
    table_section: str = Query(...),
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_role = request.cookies.get("auth_role", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_section5(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"found": False}, status_code=403)
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    
    record = (
        db.query(DistrictRevenue0029JamaTalmel)
        .filter(
            DistrictRevenue0029JamaTalmel.fiscal_year == fiscal_year,
            DistrictRevenue0029JamaTalmel.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictRevenue0029JamaTalmel.table_section_code == table_section,
        )
        .first()
    )
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True,
        "id": record.id,
        "table_section_code": record.table_section_code,
        "mumbai_city_deposit": record.mumbai_city_deposit or 0,
        "mumbai_city_reconciliation": record.mumbai_city_reconciliation or 0,
        "mumbai_suburban_deposit": record.mumbai_suburban_deposit or 0,
        "mumbai_suburban_reconciliation": record.mumbai_suburban_reconciliation or 0,
        "thane_deposit": record.thane_deposit or 0,
        "thane_reconciliation": record.thane_reconciliation or 0,
        "raigad_deposit": record.raigad_deposit or 0,
        "raigad_reconciliation": record.raigad_reconciliation or 0,
        "ratnagiri_deposit": record.ratnagiri_deposit or 0,
        "ratnagiri_reconciliation": record.ratnagiri_reconciliation or 0,
        "sindhudurg_deposit": record.sindhudurg_deposit or 0,
        "sindhudurg_reconciliation": record.sindhudurg_reconciliation or 0,
        "remarks": record.remarks or "",
    })


@router.post("/section5/api/update-inline")
async def api_update_inline_section5(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    Mumbai_City_deposit: int = Form(0),
    Mumbai_City_reconciliation: int = Form(0),
    Mumbai_Suburban_deposit: int = Form(0),
    Mumbai_Suburban_reconciliation: int = Form(0),
    Thane_deposit: int = Form(0),
    Thane_reconciliation: int = Form(0),
    Raigad_deposit: int = Form(0),
    Raigad_reconciliation: int = Form(0),
    Ratnagiri_deposit: int = Form(0),
    Ratnagiri_reconciliation: int = Form(0),
    Sindhudurg_deposit: int = Form(0),
    Sindhudurg_reconciliation: int = Form(0),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_section5(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden - No edit permission"}, status_code=403)
    
    record = (
        db.query(DistrictRevenue0029JamaTalmel)
        .filter(
            DistrictRevenue0029JamaTalmel.id == id,
            DistrictRevenue0029JamaTalmel.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    is_dco_assistant = check_dco_access(auth_level) and auth_role == "assistant"
    user_district = None
    if not is_dco_assistant:
        if auth_level == "district" and auth_unit in JAMA_TALMEL_DISTRICTS:
            user_district = auth_unit
        elif auth_level == "taluka" and auth_unit:
            from src.utils_district import get_district_from_taluka
            district_name = get_district_from_taluka(auth_unit)
            if district_name and district_name in JAMA_TALMEL_DISTRICTS:
                user_district = district_name
    
    old_vals = {
        "mumbai_city_deposit": record.mumbai_city_deposit,
        "mumbai_city_reconciliation": record.mumbai_city_reconciliation,
        "mumbai_suburban_deposit": record.mumbai_suburban_deposit,
        "mumbai_suburban_reconciliation": record.mumbai_suburban_reconciliation,
        "thane_deposit": record.thane_deposit,
        "thane_reconciliation": record.thane_reconciliation,
        "raigad_deposit": record.raigad_deposit,
        "raigad_reconciliation": record.raigad_reconciliation,
        "ratnagiri_deposit": record.ratnagiri_deposit,
        "ratnagiri_reconciliation": record.ratnagiri_reconciliation,
        "sindhudurg_deposit": record.sindhudurg_deposit,
        "sindhudurg_reconciliation": record.sindhudurg_reconciliation,
    }
    
    if is_dco_assistant:
        record.mumbai_city_deposit = validate_numeric_input(Mumbai_City_deposit, "Mumbai_City_deposit")
        record.mumbai_city_reconciliation = validate_numeric_input(Mumbai_City_reconciliation, "Mumbai_City_reconciliation")
        record.mumbai_suburban_deposit = validate_numeric_input(Mumbai_Suburban_deposit, "Mumbai_Suburban_deposit")
        record.mumbai_suburban_reconciliation = validate_numeric_input(Mumbai_Suburban_reconciliation, "Mumbai_Suburban_reconciliation")
        record.thane_deposit = validate_numeric_input(Thane_deposit, "Thane_deposit")
        record.thane_reconciliation = validate_numeric_input(Thane_reconciliation, "Thane_reconciliation")
        record.raigad_deposit = validate_numeric_input(Raigad_deposit, "Raigad_deposit")
        record.raigad_reconciliation = validate_numeric_input(Raigad_reconciliation, "Raigad_reconciliation")
        record.ratnagiri_deposit = validate_numeric_input(Ratnagiri_deposit, "Ratnagiri_deposit")
        record.ratnagiri_reconciliation = validate_numeric_input(Ratnagiri_reconciliation, "Ratnagiri_reconciliation")
        record.sindhudurg_deposit = validate_numeric_input(Sindhudurg_deposit, "Sindhudurg_deposit")
        record.sindhudurg_reconciliation = validate_numeric_input(Sindhudurg_reconciliation, "Sindhudurg_reconciliation")
    elif user_district:
        district_field_map = {
            "Mumbai City": ("mumbai_city", Mumbai_City_deposit, Mumbai_City_reconciliation),
            "Mumbai Suburban": ("mumbai_suburban", Mumbai_Suburban_deposit, Mumbai_Suburban_reconciliation),
            "Thane": ("thane", Thane_deposit, Thane_reconciliation),
            "Raigad": ("raigad", Raigad_deposit, Raigad_reconciliation),
            "Ratnagiri": ("ratnagiri", Ratnagiri_deposit, Ratnagiri_reconciliation),
            "Sindhudurg": ("sindhudurg", Sindhudurg_deposit, Sindhudurg_reconciliation),
        }
        field_key, deposit_val, recon_val = district_field_map.get(user_district, (None, None, None))
        if field_key:
            setattr(record, f"{field_key}_deposit", validate_numeric_input(deposit_val, f"{field_key}_deposit"))
            setattr(record, f"{field_key}_reconciliation", validate_numeric_input(recon_val, f"{field_key}_reconciliation"))
        else:
            return JSONResponse({"success": False, "message": "Invalid district"}, status_code=400)
    
    db.commit()
    db.refresh(record)
    
    new_vals = {
        "mumbai_city_deposit": record.mumbai_city_deposit,
        "mumbai_city_reconciliation": record.mumbai_city_reconciliation,
        "mumbai_suburban_deposit": record.mumbai_suburban_deposit,
        "mumbai_suburban_reconciliation": record.mumbai_suburban_reconciliation,
        "thane_deposit": record.thane_deposit,
        "thane_reconciliation": record.thane_reconciliation,
        "raigad_deposit": record.raigad_deposit,
        "raigad_reconciliation": record.raigad_reconciliation,
        "ratnagiri_deposit": record.ratnagiri_deposit,
        "ratnagiri_reconciliation": record.ratnagiri_reconciliation,
        "sindhudurg_deposit": record.sindhudurg_deposit,
        "sindhudurg_reconciliation": record.sindhudurg_reconciliation,
    }
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_revenue_0029_jama_talmel",
        record_id=record.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})

