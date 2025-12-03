"""API routes for sub-scheme 62450017 - district-wise expenditure."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from .models import DistrictExpenditure62450017, SCHEME_CODE, SUB_SCHEME_CODE
from .schemas import (
    DistrictExpenditureCreate,
    DistrictExpenditureUpdate,
    DistrictExpenditureResponse,
)


router = APIRouter(prefix="/api/s62450017", tags=["API - 62450017 इतर कर्जे"])


@router.get("", response_model=List[DistrictExpenditureResponse])
def list_district_expenditure(
    skip: int = 0,
    limit: int = 100,
    fiscal_year: Optional[str] = None,
    db: Session = Depends(get_db),
):
    fy = validate_fiscal_year(fiscal_year, db)
    return (
        db.query(DistrictExpenditure62450017)
        .filter(
            DistrictExpenditure62450017.fiscal_year == fy,
            DistrictExpenditure62450017.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .order_by(DistrictExpenditure62450017.district)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{id}", response_model=DistrictExpenditureResponse)
def get_district_expenditure(id: int, db: Session = Depends(get_db)):
    item = (
        db.query(DistrictExpenditure62450017)
        .filter(
            DistrictExpenditure62450017.id == id,
            DistrictExpenditure62450017.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return item


@router.post("", response_model=DistrictExpenditureResponse, status_code=status.HTTP_201_CREATED)
def create_district_expenditure(
    data: DistrictExpenditureCreate, db: Session = Depends(get_db)
):
    payload = data.model_dump()
    payload["fiscal_year"] = validate_fiscal_year(payload.get("fiscal_year"), db)
    payload["scheme_code"] = SCHEME_CODE
    payload["sub_scheme_code"] = SUB_SCHEME_CODE

    existing = (
        db.query(DistrictExpenditure62450017)
        .filter(
            DistrictExpenditure62450017.fiscal_year == payload["fiscal_year"],
            DistrictExpenditure62450017.sub_scheme_code == SUB_SCHEME_CODE,
            DistrictExpenditure62450017.district == payload["district"],
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Record already exists for this district and fiscal year",
        )

    item = DistrictExpenditure62450017(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{id}", response_model=DistrictExpenditureResponse)
def update_district_expenditure(
    id: int, data: DistrictExpenditureUpdate, db: Session = Depends(get_db)
):
    item = (
        db.query(DistrictExpenditure62450017)
        .filter(
            DistrictExpenditure62450017.id == id,
            DistrictExpenditure62450017.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    update_data = data.model_dump(exclude_unset=True)
    if "fiscal_year" in update_data:
        update_data["fiscal_year"] = validate_fiscal_year(update_data["fiscal_year"], db)

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_district_expenditure(id: int, db: Session = Depends(get_db)):
    item = (
        db.query(DistrictExpenditure62450017)
        .filter(
            DistrictExpenditure62450017.id == id,
            DistrictExpenditure62450017.sub_scheme_code == SUB_SCHEME_CODE,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


