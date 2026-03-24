from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from src.config import DISTRICTS_MR
from src.database import get_db
from src.core.templates import render
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.schemes.s2245.fiscal_year_labels import FiscalYearLabels2245
from .models import DistrictExpenditure2245, SUB_SCHEME_CODE
from .config import (
    get_all_table_sections, get_table_section, EXTRA_DISTRICT_MR, KONKAN_DISTRICTS, EXTRA_DISTRICT,
    get_section3_table_sections, SECTION3_DISTRICTS, ROW_TYPE_DC, ROW_TYPE_ZP, ROW_TYPE_SUBTOTAL,
)
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    validate_access_control,
    validate_numeric_input,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
    build_section3_table_data,
    build_section3_district_key,
    parse_section3_district_key,
)
from src.utils_auth import get_auth_unit, get_auth_role, get_auth_level, get_auth_user, is_authenticated

router = APIRouter(
    prefix="/ui/s2245/section1",
    tags=["UI - 2245"],
    include_in_schema=False,
)

@router.get("", response_class=HTMLResponse)
async def ui_list_section1(
    request: Request,
    db: Session = Depends(get_db),
    table_section: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2245(relative_years)
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
            db.query(DistrictExpenditure2245)
            .filter(
                DistrictExpenditure2245.fiscal_year == fiscal_year,
                DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2245.table_section_code == section["code"],
                DistrictExpenditure2245.district.in_(allowed_districts),
            )
        )
        if district and district in allowed_districts:
            query = query.filter(DistrictExpenditure2245.district == district)
        items = query.order_by(DistrictExpenditure2245.district).all()
        if not items:
            continue
        totals = {
            "exp_prev3": sum(item.exp_prev3 or 0 for item in items),
            "exp_prev2": sum(item.exp_prev2 or 0 for item in items),
            "exp_prev1": sum(item.exp_prev1 or 0 for item in items),
            "budget_estimate_curr": sum(item.budget_estimate_curr or 0 for item in items),
            "revised_estimate_curr": sum(item.revised_estimate_curr or 0 for item in items),
            "budget_estimate_next": sum(item.budget_estimate_next or 0 for item in items),
        }
        tables_data.append({
            "section": section,
            "items": items,
            "totals": totals,
        })
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
    districts_mr = DISTRICTS_MR.copy()
    districts_mr["DCO Staff"] = EXTRA_DISTRICT_MR
    context = {
        "request": request,
        "tables_data": tables_data,
        "can_edit": can_edit,
        "resource_name": "2245",
        "districts_mr": districts_mr,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "table_sections": all_table_sections,
        "districts": districts_for_filter,
        "current_table_section": table_section,
        "current_district": district,
        "fy_labels": fy_labels,
    }
    return render(request, 
        "schemes/s2245/subs/s2245/section1_list.html",
        context,
    )

@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_section1_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2245(relative_years)
    item = (
        db.query(DistrictExpenditure2245)
        .filter(
            DistrictExpenditure2245.id == id,
            DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
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
    districts_mr["DCO Staff"] = EXTRA_DISTRICT_MR
    auth_role = get_auth_role(request)
    context = {
        "request": request,
        "item": item,
        "section": section,
        "districts": allowed_districts,
        "resource_name": "2245 edit",
        "districts_mr": districts_mr,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "fy_labels": fy_labels,
    }
    return render(request, 
        "schemes/s2245/subs/s2245/section1_form.html",
        context,
    )

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_section1(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    from src.utils_timing import check_data_filling_allowed
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
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
        db.query(DistrictExpenditure2245)
        .filter(
            DistrictExpenditure2245.id == id,
            DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
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
            db.query(DistrictExpenditure2245)
            .filter(
                DistrictExpenditure2245.fiscal_year == item.fiscal_year,
                DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2245.table_section_code == item.table_section_code,
                DistrictExpenditure2245.district == district,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Record already exists",
            )
    old_vals = {
        "table_section_code": item.table_section_code,
        "district": item.district,
        "exp_prev3": item.exp_prev3,
        "exp_prev2": item.exp_prev2,
        "exp_prev1": item.exp_prev1,
        "budget_estimate_curr": item.budget_estimate_curr,
        "revised_estimate_curr": item.revised_estimate_curr,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }
    item.district = district
    item.exp_prev3 = validate_numeric_input(form.get("ExpenditurePrev3"), "ExpenditurePrev3")
    item.exp_prev2 = validate_numeric_input(form.get("ExpenditurePrev2"), "ExpenditurePrev2")
    item.exp_prev1 = validate_numeric_input(form.get("ExpenditurePrev1"), "ExpenditurePrev1")
    item.budget_estimate_curr = validate_numeric_input(form.get("BudgetEstimateCurr"), "BudgetEstimateCurr")
    item.revised_estimate_curr = validate_numeric_input(form.get("RevisedEstimateCurr"), "RevisedEstimateCurr")
    item.budget_estimate_next = validate_numeric_input(form.get("BudgetEstimateNext"), "BudgetEstimateNext")
    item.remarks = (form.get("Remarks") or "").strip() or None
    new_vals = {
        "table_section_code": item.table_section_code,
        "district": item.district,
        "exp_prev3": item.exp_prev3,
        "exp_prev2": item.exp_prev2,
        "exp_prev1": item.exp_prev1,
        "budget_estimate_curr": item.budget_estimate_curr,
        "revised_estimate_curr": item.revised_estimate_curr,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }
    db.commit()
    db.refresh(item)
    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_2245",
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
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, table_section)
    if district not in allowed_districts:
        return JSONResponse({"found": False}, status_code=403)
    record = (
        db.query(DistrictExpenditure2245)
        .filter(
            DistrictExpenditure2245.fiscal_year == fiscal_year,
            DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure2245.table_section_code == table_section,
            DistrictExpenditure2245.district == district,
        )
        .first()
    )
    if not record:
        return JSONResponse({"found": False})
    return JSONResponse({
        "found": True,
        "id": record.id,
        "exp_prev3": record.exp_prev3 or 0,
        "exp_prev2": record.exp_prev2 or 0,
        "exp_prev1": record.exp_prev1 or 0,
        "budget_estimate_curr": record.budget_estimate_curr or 0,
        "revised_estimate_curr": record.revised_estimate_curr or 0,
        "budget_estimate_next": record.budget_estimate_next or 0,
        "remarks": record.remarks or "",
    })

@router.post("/api/update-inline")
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    ExpenditurePrev3: int = Form(0),
    ExpenditurePrev2: int = Form(0),
    ExpenditurePrev1: int = Form(0),
    BudgetEstimateCurr: int = Form(0),
    RevisedEstimateCurr: int = Form(0),
    BudgetEstimateNext: int = Form(0),
    Remarks: str = Form(""),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    from src.utils_timing import check_data_filling_allowed
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    record = (
        db.query(DistrictExpenditure2245)
        .filter(
            DistrictExpenditure2245.id == id,
            DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
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
        "exp_prev3": record.exp_prev3,
        "exp_prev2": record.exp_prev2,
        "exp_prev1": record.exp_prev1,
        "budget_estimate_curr": record.budget_estimate_curr,
        "revised_estimate_curr": record.revised_estimate_curr,
        "budget_estimate_next": record.budget_estimate_next,
        "remarks": record.remarks,
    }
    record.exp_prev3 = validate_numeric_input(ExpenditurePrev3, "ExpenditurePrev3")
    record.exp_prev2 = validate_numeric_input(ExpenditurePrev2, "ExpenditurePrev2")
    record.exp_prev1 = validate_numeric_input(ExpenditurePrev1, "ExpenditurePrev1")
    record.budget_estimate_curr = validate_numeric_input(BudgetEstimateCurr, "BudgetEstimateCurr")
    record.revised_estimate_curr = validate_numeric_input(RevisedEstimateCurr, "RevisedEstimateCurr")
    record.budget_estimate_next = validate_numeric_input(BudgetEstimateNext, "BudgetEstimateNext")
    record.remarks = Remarks.strip() or None
    db.commit()
    db.refresh(record)
    new_vals = {
        "exp_prev3": record.exp_prev3,
        "exp_prev2": record.exp_prev2,
        "exp_prev1": record.exp_prev1,
        "budget_estimate_curr": record.budget_estimate_curr,
        "revised_estimate_curr": record.revised_estimate_curr,
        "budget_estimate_next": record.budget_estimate_next,
        "remarks": record.remarks,
    }
    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_2245",
        record_id=record.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )
    return JSONResponse({"success": True, "message": "Success"})

@router.get("/section2", response_class=HTMLResponse)
async def ui_list_section2(
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2245(relative_years)
    all_table_sections = get_all_table_sections()
    summary_rows = []
    grand_totals = {
        "exp_prev3": 0,
        "exp_prev2": 0,
        "exp_prev1": 0,
        "budget_estimate_curr": 0,
        "revised_estimate_curr": 0,
        "budget_estimate_next": 0,
    }
    for idx, section in enumerate(all_table_sections, 1):
        allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, section["code"])
        if not allowed_districts:
            continue
        query = (
            db.query(DistrictExpenditure2245)
            .filter(
                DistrictExpenditure2245.fiscal_year == fiscal_year,
                DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
                DistrictExpenditure2245.table_section_code == section["code"],
                DistrictExpenditure2245.district.in_(allowed_districts),
            )
        )
        items = query.all()
        totals = {
            "exp_prev3": sum(item.exp_prev3 or 0 for item in items),
            "exp_prev2": sum(item.exp_prev2 or 0 for item in items),
            "exp_prev1": sum(item.exp_prev1 or 0 for item in items),
            "budget_estimate_curr": sum(item.budget_estimate_curr or 0 for item in items),
            "revised_estimate_curr": sum(item.revised_estimate_curr or 0 for item in items),
            "budget_estimate_next": sum(item.budget_estimate_next or 0 for item in items),
        }
        grand_totals["exp_prev3"] += totals["exp_prev3"]
        grand_totals["exp_prev2"] += totals["exp_prev2"]
        grand_totals["exp_prev1"] += totals["exp_prev1"]
        grand_totals["budget_estimate_curr"] += totals["budget_estimate_curr"]
        grand_totals["revised_estimate_curr"] += totals["revised_estimate_curr"]
        grand_totals["budget_estimate_next"] += totals["budget_estimate_next"]
        summary_rows.append({
            "sr_no": idx,
            "section": section,
            "totals": totals,
        })
    context = {
        "request": request,
        "summary_rows": summary_rows,
        "grand_totals": grand_totals,
        "resource_name": "2245 - 2",
        "auth_level": auth_level,
        "fy_labels": fy_labels,
    }
    return render(request, 
        "schemes/s2245/subs/s2245/section2_list.html",
        context,
    )

@router.get("/section3", response_class=HTMLResponse)
async def ui_list_section3(
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_role = get_auth_role(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    ensure_fiscal_year_seeded(db, fiscal_year)
    relative_years = get_relative_fiscal_years(fiscal_year)
    fy_labels = FiscalYearLabels2245(relative_years)
    section3_sections = get_section3_table_sections()
    tables_data = []
    for section in section3_sections:
        allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, section["code"])
        if not allowed_districts:
            continue
        table_data = build_section3_table_data(db, fiscal_year, section["code"], allowed_districts)
        if table_data:
            tables_data.append(table_data)
    can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
    districts_mr = DISTRICTS_MR.copy()
    districts_mr["DCO Staff"] = EXTRA_DISTRICT_MR
    context = {
        "request": request,
        "tables_data": tables_data,
        "can_edit": can_edit,
        "resource_name": "2245 - 3",
        "districts_mr": districts_mr,
        "auth_level": auth_level,
        "auth_role": auth_role,
        "section3_districts": SECTION3_DISTRICTS,
        "row_type_dc": ROW_TYPE_DC,
        "row_type_zp": ROW_TYPE_ZP,
        "row_type_subtotal": ROW_TYPE_SUBTOTAL,
        "fy_labels": fy_labels,
    }
    return render(request, 
        "schemes/s2245/subs/s2245/section3_list.html",
        context,
    )

@router.get("/section3/api/get-record")
async def api_get_record_section3(
    request: Request,
    id: int = Query(...),
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    record = (
        db.query(DistrictExpenditure2245)
        .filter(
            DistrictExpenditure2245.id == id,
            DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not record:
        return JSONResponse({"found": False}, status_code=404)
    district, row_type = parse_section3_district_key(record.district)
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, record.table_section_code)
    if district not in allowed_districts:
        return JSONResponse({"found": False}, status_code=403)
    return JSONResponse({
        "found": True,
        "id": record.id,
        "exp_prev3": record.exp_prev3 or 0,
        "exp_prev2": record.exp_prev2 or 0,
        "exp_prev1": record.exp_prev1 or 0,
        "budget_estimate_curr": record.budget_estimate_curr or 0,
        "revised_estimate_curr": record.revised_estimate_curr or 0,
        "budget_estimate_next": record.budget_estimate_next or 0,
        "remarks": record.remarks or "",
    })

@router.post("/section3/api/update-inline")
async def api_update_inline_section3(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    ExpenditurePrev3: int = Form(0),
    ExpenditurePrev2: int = Form(0),
    ExpenditurePrev1: int = Form(0),
    BudgetEstimateCurr: int = Form(0),
    RevisedEstimateCurr: int = Form(0),
    BudgetEstimateNext: int = Form(0),
    Remarks: str = Form(""),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    from src.utils_timing import check_data_filling_allowed
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    if auth_role == "assistant":
        is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SUB_SCHEME_CODE)
        if not is_allowed:
            return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    record = (
        db.query(DistrictExpenditure2245)
        .filter(
            DistrictExpenditure2245.id == id,
            DistrictExpenditure2245.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    district, row_type = parse_section3_district_key(record.district)
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, record.table_section_code)
    if district not in allowed_districts:
        return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    allowed, error_msg = validate_access_control(record.district, auth_level, auth_unit, db)
    if not allowed:
        return JSONResponse({"success": False, "message": error_msg or "Access denied"}, status_code=403)
    old_vals = {
        "exp_prev3": record.exp_prev3,
        "exp_prev2": record.exp_prev2,
        "exp_prev1": record.exp_prev1,
        "budget_estimate_curr": record.budget_estimate_curr,
        "revised_estimate_curr": record.revised_estimate_curr,
        "budget_estimate_next": record.budget_estimate_next,
        "remarks": record.remarks,
    }
    record.exp_prev3 = validate_numeric_input(ExpenditurePrev3, "ExpenditurePrev3")
    record.exp_prev2 = validate_numeric_input(ExpenditurePrev2, "ExpenditurePrev2")
    record.exp_prev1 = validate_numeric_input(ExpenditurePrev1, "ExpenditurePrev1")
    record.budget_estimate_curr = validate_numeric_input(BudgetEstimateCurr, "BudgetEstimateCurr")
    record.revised_estimate_curr = validate_numeric_input(RevisedEstimateCurr, "RevisedEstimateCurr")
    record.budget_estimate_next = validate_numeric_input(BudgetEstimateNext, "BudgetEstimateNext")
    record.remarks = Remarks.strip() or None
    db.commit()
    db.refresh(record)
    new_vals = {
        "exp_prev3": record.exp_prev3,
        "exp_prev2": record.exp_prev2,
        "exp_prev1": record.exp_prev1,
        "budget_estimate_curr": record.budget_estimate_curr,
        "revised_estimate_curr": record.revised_estimate_curr,
        "budget_estimate_next": record.budget_estimate_next,
        "remarks": record.remarks,
    }
    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_2245",
        record_id=record.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )
    return JSONResponse({"success": True, "message": "Success"})

@router.get("/export")
async def ui_export_excel(
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(401, detail="Unauthorized")
    from src.schemes.s2245_2215 import export_combined_workbook_async
    fiscal_year = get_fiscal_year_from_request(request, db)
    return await export_combined_workbook_async(db, fiscal_year)
