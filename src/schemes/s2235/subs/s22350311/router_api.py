"""API routes for sub-scheme 22350311 - district-wise expenditure."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from .models import DistrictExpenditure22350311, SCHEME_CODE, SUB_SCHEME_CODE
from .schemas import (
    DistrictExpenditureCreate,
    DistrictExpenditureUpdate,
    DistrictExpenditureResponse,
)
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    validate_access_control,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)


router = APIRouter(prefix="/api/s22350311", tags=["API - 22350311 सामाजिक सुरक्षा व कल्याण"])


@router.get("", response_model=List[DistrictExpenditureResponse])
def list_district_expenditure(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    fiscal_year: Optional[str] = None,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if not allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    fy = validate_fiscal_year(fiscal_year, db)
    ensure_fiscal_year_seeded(db, fy)
    query = (
        db.query(DistrictExpenditure22350311)
        .filter(
            DistrictExpenditure22350311.fiscal_year == fy,
            DistrictExpenditure22350311.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure22350311.district.in_(allowed_districts),
        )
        .order_by(DistrictExpenditure22350311.district)
        .offset(skip)
        .limit(limit)
    )
    return query.all()


@router.get("/{id}", response_model=DistrictExpenditureResponse)
def get_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    item = (
        db.query(DistrictExpenditure22350311)
        .filter(
            DistrictExpenditure22350311.id == id,
            DistrictExpenditure22350311.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
    
    return item


@router.post("", response_model=DistrictExpenditureResponse, status_code=status.HTTP_201_CREATED)
def create_district_expenditure(
    request: Request,
    data: DistrictExpenditureCreate,
    db: Session = Depends(get_db),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    payload = data.model_dump()
    district = payload["district"]
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
    
    payload["fiscal_year"] = validate_fiscal_year(payload.get("fiscal_year"), db)
    payload["scheme_code"] = SCHEME_CODE
    payload["sub_scheme_code"] = SUB_SCHEME_CODE

    existing = (
        db.query(DistrictExpenditure22350311)
        .filter(
            DistrictExpenditure22350311.fiscal_year == payload["fiscal_year"],
            DistrictExpenditure22350311.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure22350311.district == district,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Record already exists for this district and fiscal year",
        )

    item = DistrictExpenditure22350311(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_22350311",
        record_id=item.id,
        username=username,
        old_vals={},
        new_vals=payload,
        req_info=req_info,
        action="CREATE"
    )
    
    return item


@router.put("/{id}", response_model=DistrictExpenditureResponse)
def update_district_expenditure(
    request: Request,
    id: int,
    data: DistrictExpenditureUpdate,
    db: Session = Depends(get_db),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    item = (
        db.query(DistrictExpenditure22350311)
        .filter(
            DistrictExpenditure22350311.id == id,
            DistrictExpenditure22350311.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
    
    update_data = data.model_dump(exclude_unset=True)
    if "district" in update_data:
        district = update_data["district"]
        if district not in allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    old_vals = {
        "district": item.district,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "budget_grant_2024_25": item.budget_grant_2024_25,
        "revised_grant_2025_26": item.revised_grant_2025_26,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }

    if "fiscal_year" in update_data:
        update_data["fiscal_year"] = validate_fiscal_year(update_data["fiscal_year"], db)

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    
    new_vals = {
        "district": item.district,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "budget_grant_2024_25": item.budget_grant_2024_25,
        "revised_grant_2025_26": item.revised_grant_2025_26,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_22350311",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE"
    )
    
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    item = (
        db.query(DistrictExpenditure22350311)
        .filter(
            DistrictExpenditure22350311.id == id,
            DistrictExpenditure22350311.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    allowed, error_msg = validate_access_control(item.district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
    
    old_vals = {
        "district": item.district,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "budget_grant_2024_25": item.budget_grant_2024_25,
        "revised_grant_2025_26": item.revised_grant_2025_26,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_22350311",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals={},
        req_info=req_info,
        action="DELETE"
    )

    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
