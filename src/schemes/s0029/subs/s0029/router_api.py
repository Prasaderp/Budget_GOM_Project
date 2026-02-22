"""API routes for scheme 0029 - Section 1 district-wise revenue."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from .models import DistrictRevenue0029, SCHEME_CODE, SUB_SCHEME_CODE
from .schemas import (
    DistrictRevenueCreate,
    DistrictRevenueUpdate,
    DistrictRevenueResponse,
)
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    validate_access_control,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)
from .config import get_table_section
from src.utils_auth import (
    get_auth_unit,
    get_auth_level,
    get_auth_role,
    get_auth_user,
    is_authenticated
)


router = APIRouter(prefix="/api/s0029", tags=["API - 0029 महसूल जमा - अर्थसंकल्पीय जिल्हा"])


@router.get("", response_model=List[DistrictRevenueResponse])
def list_district_revenue(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    fiscal_year: Optional[str] = None,
    table_section_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, table_section_code)
    if not allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    fy = validate_fiscal_year(fiscal_year, db)
    ensure_fiscal_year_seeded(db, fy)
    query = (
        db.query(DistrictRevenue0029)
        .filter(
            DistrictRevenue0029.fiscal_year == fy,
            DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictRevenue0029.district.in_(allowed_districts),
        )
    )
    if table_section_code:
        query = query.filter(DistrictRevenue0029.table_section_code == table_section_code)
    query = query.order_by(
        DistrictRevenue0029.table_section_code,
        DistrictRevenue0029.district
    ).offset(skip).limit(limit)
    return query.all()


@router.get("/{id}", response_model=DistrictRevenueResponse)
def get_district_revenue(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_level = get_auth_level(request)
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

    return item


@router.post("", response_model=DistrictRevenueResponse, status_code=status.HTTP_201_CREATED)
def create_district_revenue(
    request: Request,
    data: DistrictRevenueCreate,
    db: Session = Depends(get_db),
):
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    payload = data.model_dump()
    district = payload["district"]
    table_section_code = payload["table_section_code"]

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, table_section_code)
    if district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")

    payload["fiscal_year"] = validate_fiscal_year(payload.get("fiscal_year"), db)
    payload["scheme_code"] = SCHEME_CODE
    payload["sub_scheme_code"] = SUB_SCHEME_CODE

    existing = (
        db.query(DistrictRevenue0029)
        .filter(
            DistrictRevenue0029.fiscal_year == payload["fiscal_year"],
            DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictRevenue0029.table_section_code == table_section_code,
            DistrictRevenue0029.district == district,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Record already exists for this table section, district and fiscal year",
        )

    item = DistrictRevenue0029(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)

    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_revenue_0029",
        record_id=item.id,
        username=username,
        old_vals={},
        new_vals=payload,
        req_info=req_info,
        action="CREATE",
    )

    return item


@router.put("/{id}", response_model=DistrictRevenueResponse)
def update_district_revenue(
    request: Request,
    id: int,
    data: DistrictRevenueUpdate,
    db: Session = Depends(get_db),
):
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

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

    update_data = data.model_dump(exclude_unset=True)
    if "table_section_code" in update_data:
        if not get_table_section(update_data["table_section_code"]):
            raise HTTPException(status_code=400, detail="Invalid table section code")
            
    table_section_code = update_data.get("table_section_code", item.table_section_code)

    if "district" in update_data or "table_section_code" in update_data:
        district = update_data.get("district", item.district)
        new_allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, table_section_code)
        if district not in new_allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
        if district != item.district or table_section_code != item.table_section_code:
            existing = (
                db.query(DistrictRevenue0029)
                .filter(
                    DistrictRevenue0029.fiscal_year == item.fiscal_year,
                    DistrictRevenue0029.sub_scheme_code == SUB_SCHEME_CODE,
                    DistrictRevenue0029.table_section_code == table_section_code,
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

    if "fiscal_year" in update_data:
        update_data["fiscal_year"] = validate_fiscal_year(update_data["fiscal_year"], db)

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

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

    username = get_auth_user(request) or "unknown"
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

    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_district_revenue(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

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

    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_revenue_0029",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals={},
        req_info=req_info,
        action="DELETE",
    )

    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

