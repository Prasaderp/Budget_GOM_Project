"""API routes for sub-scheme 2215 - Water Scarcity district-wise expenditure."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from .models import DistrictExpenditure2215, SCHEME_CODE, SUB_SCHEME_CODE
from .schemas import (
    DistrictExpenditureCreate,
    DistrictExpenditureUpdate,
    DistrictExpenditureResponse,
)
from .helpers import (
    get_allowed_districts_for_user,
    check_edit_permission_for_scheme,
    ensure_fiscal_year_seeded,
    log_audit,
)
from src.utils_auth import get_auth_unit, get_auth_role, get_auth_level, is_authenticated


router = APIRouter(prefix="/api/s2215", tags=["API - 2215 पाणी टंचाई"])


@router.get("", response_model=List[DistrictExpenditureResponse])
def list_district_expenditure(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    fiscal_year: Optional[str] = None,
    account_head_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List district expenditure records with optional filters."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, account_head_code)
    if not allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    fy = validate_fiscal_year(fiscal_year, db)
    ensure_fiscal_year_seeded(db, fy)
    query = (
        db.query(DistrictExpenditure2215)
        .filter(
            DistrictExpenditure2215.fiscal_year == fy,
            DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure2215.district.in_(allowed_districts),
        )
    )
    if account_head_code:
        query = query.filter(DistrictExpenditure2215.account_head_code == account_head_code)
    query = query.order_by(
        DistrictExpenditure2215.account_head_code,
        DistrictExpenditure2215.district
    ).offset(skip).limit(limit)
    return query.all()


@router.get("/{id}", response_model=DistrictExpenditureResponse)
def get_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    """Get a specific district expenditure record by ID."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    item = (
        db.query(DistrictExpenditure2215)
        .filter(
            DistrictExpenditure2215.id == id,
            DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, item.account_head_code)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return item


@router.post("", response_model=DistrictExpenditureResponse, status_code=status.HTTP_201_CREATED)
def create_district_expenditure(
    request: Request,
    data: DistrictExpenditureCreate,
    db: Session = Depends(get_db),
):
    """Create a new district expenditure record."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    payload = data.model_dump()
    district = payload["district"]
    account_head_code = payload["account_head_code"]

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, account_head_code)
    if district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    payload["fiscal_year"] = validate_fiscal_year(payload.get("fiscal_year"), db)
    payload["scheme_code"] = SCHEME_CODE
    payload["sub_scheme_code"] = SUB_SCHEME_CODE

    existing = (
        db.query(DistrictExpenditure2215)
        .filter(
            DistrictExpenditure2215.fiscal_year == payload["fiscal_year"],
            DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure2215.account_head_code == account_head_code,
            DistrictExpenditure2215.district == district,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Record already exists for this account head, district and fiscal year",
        )

    item = DistrictExpenditure2215(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)

    log_audit(
        db=db,
        request=request,
        table="district_expenditure_2215",
        record_id=item.id,
        old_vals={},
        new_vals=payload,
    )

    return item


@router.put("/{id}", response_model=DistrictExpenditureResponse)
def update_district_expenditure(
    request: Request,
    id: int,
    data: DistrictExpenditureUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing district expenditure record."""
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
            DistrictExpenditure2215.id == id,
            DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, item.account_head_code)
    if item.district not in allowed_districts:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = data.model_dump(exclude_unset=True)
    account_head_code = update_data.get("account_head_code", item.account_head_code)

    if "district" in update_data or "account_head_code" in update_data:
        district = update_data.get("district", item.district)
        new_allowed_districts = get_allowed_districts_for_user(auth_level, auth_unit, account_head_code)
        if district not in new_allowed_districts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if district != item.district or account_head_code != item.account_head_code:
            existing = (
                db.query(DistrictExpenditure2215)
                .filter(
                    DistrictExpenditure2215.fiscal_year == item.fiscal_year,
                    DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE,
                    DistrictExpenditure2215.account_head_code == account_head_code,
                    DistrictExpenditure2215.district == district,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Record already exists for this account head, district and fiscal year",
                )

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

    if "fiscal_year" in update_data:
        update_data["fiscal_year"] = validate_fiscal_year(update_data["fiscal_year"], db)

    for key, value in update_data.items():
        setattr(item, key, value)

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

    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_district_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    """Delete a district expenditure record."""
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
            DistrictExpenditure2215.id == id,
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

    log_audit(
        db=db,
        request=request,
        table="district_expenditure_2215",
        record_id=item.id,
        old_vals=old_vals,
        new_vals={},
    )

    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

