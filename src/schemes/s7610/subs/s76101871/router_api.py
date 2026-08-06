"""API routes for sub-scheme 76101871 - district-wise expenditure."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from .models import DistrictExpenditure76101871, SCHEME_CODE, SUB_SCHEME_CODE
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
from src.utils_auth import (
    get_auth_unit,
    get_auth_level,
    get_auth_role,
    get_auth_user,
    is_authenticated
)


router = APIRouter(prefix="/api/s76101871", tags=["API - 76101871 जिल्हानिहाय खर्च"])


@router.get("", response_model=List[DistrictExpenditureResponse])
def list_district_expenditure(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    fiscal_year: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if not allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    fy = validate_fiscal_year(fiscal_year, db)
    ensure_fiscal_year_seeded(db, fy)
    query = (
        db.query(DistrictExpenditure76101871)
        .filter(
            DistrictExpenditure76101871.fiscal_year == fy,
            DistrictExpenditure76101871.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure76101871.district.in_(allowed_districts),
        )
        .order_by(DistrictExpenditure76101871.district)
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
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    item = (
        db.query(DistrictExpenditure76101871)
        .filter(
            DistrictExpenditure76101871.id == id,
            DistrictExpenditure76101871.sub_scheme_code == SUB_SCHEME_CODE,
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
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    payload = data.model_dump()
    district = payload["district"]

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    payload["fiscal_year"] = validate_fiscal_year(payload.get("fiscal_year"), db)
    payload["scheme_code"] = SCHEME_CODE
    payload["sub_scheme_code"] = SUB_SCHEME_CODE

    from src.core.taluka.constants import DISTRICT_OFFICE
    from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION
    existing = (
        db.query(DistrictExpenditure76101871)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(
            DistrictExpenditure76101871.fiscal_year == payload["fiscal_year"],
            DistrictExpenditure76101871.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure76101871.district == district,
            DistrictExpenditure76101871.taluka == DISTRICT_OFFICE,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Record already exists for this district and fiscal year",
        )

    from src.core.taluka.write import create_row_family
    item = create_row_family(db, DistrictExpenditure76101871, payload, request)
    db.commit()
    db.refresh(item)

    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_76101871",
        record_id=item.id,
        username=username,
        old_vals={},
        new_vals=payload,
        req_info=req_info,
        action="CREATE",
    )

    return item


@router.put("/{id}", response_model=DistrictExpenditureResponse)
def update_district_expenditure(
    request: Request,
    id: int,
    data: DistrictExpenditureUpdate,
    db: Session = Depends(get_db),
):
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    from src.core.taluka.write import resolve_editable_row
    item = resolve_editable_row(db, DistrictExpenditure76101871, id, request)
    if item.sub_scheme_code != SUB_SCHEME_CODE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = data.model_dump(exclude_unset=True)
    if "district" in update_data:
        district = update_data["district"]
        if district not in allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        allowed, error_msg = validate_access_control(district, auth_level, auth_unit, db)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")
        if district != item.district:
            from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION
            existing = (
                db.query(DistrictExpenditure76101871)
                .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
                .filter(
                    DistrictExpenditure76101871.fiscal_year == item.fiscal_year,
                    DistrictExpenditure76101871.sub_scheme_code == SUB_SCHEME_CODE,
                    DistrictExpenditure76101871.district == district,
                    DistrictExpenditure76101871.taluka == item.taluka,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Record already exists for this district and fiscal year",
                )

    old_vals = {
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }

    if "fiscal_year" in update_data:
        update_data["fiscal_year"] = validate_fiscal_year(update_data["fiscal_year"], db)

    for key, value in update_data.items():
        setattr(item, key, value)

    from src.core.taluka.consolidation import consolidate_row
    from src.core.taluka.models import natural_key_columns
    db.flush()
    key_cols = natural_key_columns(DistrictExpenditure76101871)
    consolidate_row(db, DistrictExpenditure76101871, item.district, item.fiscal_year,
                     {c: getattr(item, c) for c in key_cols})
    db.commit()
    db.refresh(item)

    new_vals = {
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }

    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_76101871",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE",
    )

    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_district_expenditure(
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
        db.query(DistrictExpenditure76101871)
        .filter(
            DistrictExpenditure76101871.id == id,
            DistrictExpenditure76101871.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    old_vals = {
        "district": item.district,
        "expenditure_prev3": item.expenditure_prev3,
        "expenditure_prev2": item.expenditure_prev2,
        "expenditure_prev1": item.expenditure_prev1,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_next": item.budget_estimate_next,
        "remarks": item.remarks,
    }

    username = get_auth_user(request) or "unknown"
    req_info = get_request_info(request)
    log_audit_async(
        table="district_expenditure_76101871",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals={},
        req_info=req_info,
        action="DELETE",
    )

    from src.core.taluka.write import delete_row_family
    delete_row_family(db, DistrictExpenditure76101871, id, request)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



