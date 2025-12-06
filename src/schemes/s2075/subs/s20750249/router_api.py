"""API routes for sub-scheme 20750249 - sub-head expenditure."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from .models import SubHeadExpenditure20750249, SCHEME_CODE, SUB_SCHEME_CODE
from .schemas import (
    SubHeadExpenditureUpdate,
    SubHeadExpenditureResponse,
)
from .helpers import (
    check_dco_access,
    check_edit_permission_for_scheme,
    get_request_info,
    log_audit_async,
    ensure_fiscal_year_seeded,
)


router = APIRouter(prefix="/api/s20750249", tags=["API - 20750249 उपशिर्ष / गौणशिर्ष खर्च"])


@router.get("", response_model=List[SubHeadExpenditureResponse])
def list_sub_head_expenditure(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    fiscal_year: Optional[str] = None,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    
    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO only")
    
    fy = validate_fiscal_year(fiscal_year, db)
    ensure_fiscal_year_seeded(db, fy)
    query = (
        db.query(SubHeadExpenditure20750249)
        .filter(
            SubHeadExpenditure20750249.fiscal_year == fy,
            SubHeadExpenditure20750249.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .order_by(SubHeadExpenditure20750249.id)
        .offset(skip)
        .limit(limit)
    )
    return query.all()


@router.get("/{id}", response_model=SubHeadExpenditureResponse)
def get_sub_head_expenditure(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    auth_level = request.cookies.get("auth_level", "")
    
    if not check_dco_access(auth_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO only")
    
    item = (
        db.query(SubHeadExpenditure20750249)
        .filter(
            SubHeadExpenditure20750249.id == id,
            SubHeadExpenditure20750249.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    return item


@router.put("/{id}", response_model=SubHeadExpenditureResponse)
def update_sub_head_expenditure(
    request: Request,
    id: int,
    data: SubHeadExpenditureUpdate,
    db: Session = Depends(get_db),
):
    auth_role = request.cookies.get("auth_role", "")
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = request.cookies.get("auth_unit", "")
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    item = (
        db.query(SubHeadExpenditure20750249)
        .filter(
            SubHeadExpenditure20750249.id == id,
            SubHeadExpenditure20750249.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    update_data = data.model_dump(exclude_unset=True)
    
    if "sub_head" in update_data:
        del update_data["sub_head"]

    old_vals = {
        "sub_head": item.sub_head,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
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
        "sub_head": item.sub_head,
        "expenditure_2022_23": item.expenditure_2022_23,
        "expenditure_2023_24": item.expenditure_2023_24,
        "expenditure_2024_25": item.expenditure_2024_25,
        "budget_estimate": item.budget_estimate,
        "revised_estimate": item.revised_estimate,
        "budget_estimate_2026_27": item.budget_estimate_2026_27,
        "remarks": item.remarks,
    }
    
    username = request.cookies.get("username", "unknown")
    req_info = get_request_info(request)
    log_audit_async(
        table="sub_head_expenditure_20750249",
        record_id=item.id,
        username=username,
        old_vals=old_vals,
        new_vals=new_vals,
        req_info=req_info,
        action="UPDATE"
    )
    
    return item

