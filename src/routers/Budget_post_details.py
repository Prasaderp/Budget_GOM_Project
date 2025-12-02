from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from src.models import BudgetPostDetails
from src.database import SessionLocal, get_db
from src.utils_fiscal_year import validate_fiscal_year, DEFAULT_FISCAL_YEAR

router = APIRouter(
    prefix="/api/budget_post_details",
    tags=["API - प्रपत्र ड"]
)

class BudgetPostDetailsBase(BaseModel):
    fiscal_year: Optional[str] = None
    district: Optional[str] = None
    category: Optional[str] = None
    class_type: Optional[str] = None
    designation: Optional[str] = None
    sanctioned_posts_2024_25: Optional[int] = None
    sanctioned_posts_2025_26: Optional[int] = None
    special_pay: Optional[int] = None
    basic_pay: Optional[float] = None
    grade_pay: Optional[int] = None
    local_supplementary_allowance: Optional[int] = None
    vehicle_allowance: Optional[int] = None
    washing_allowance: Optional[int] = None
    cash_allowance: Optional[int] = None
    footwear_allowance_other: Optional[int] = None

class BudgetPostDetailsCreate(BudgetPostDetailsBase):
    district: str
    category: str
    class_type: str
    designation: str

class BudgetPostDetailsUpdate(BudgetPostDetailsBase):
     pass

class BudgetPostDetailsResponse(BudgetPostDetailsBase):
    id: int
    class Config: from_attributes = True

@router.get("/", response_model=List[BudgetPostDetailsResponse])
def get_budget_post_details(skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    validated_fy = validate_fiscal_year(fiscal_year, db)
    return db.query(BudgetPostDetails).filter(BudgetPostDetails.fiscal_year == validated_fy).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=BudgetPostDetailsResponse)
def get_budget_post_detail(id: int, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    validated_fy = validate_fiscal_year(fiscal_year, db)
    detail = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id, BudgetPostDetails.fiscal_year == validated_fy).first()
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र ड तपशील सापडला नाही")
    return detail

@router.post("/", response_model=BudgetPostDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_budget_post_detail(detail: BudgetPostDetailsCreate, db: Session = Depends(get_db)):
    detail_data = detail.model_dump()
    detail_data['fiscal_year'] = validate_fiscal_year(detail_data.get('fiscal_year'), db)
    db_detail = BudgetPostDetails(**detail_data)
    db.add(db_detail)
    db.commit()
    db.refresh(db_detail)
    return db_detail

@router.put("/{id}", response_model=BudgetPostDetailsResponse)
def update_budget_post_detail(id: int, detail: BudgetPostDetailsUpdate, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    validated_fy = validate_fiscal_year(fiscal_year, db)
    db_detail = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id, BudgetPostDetails.fiscal_year == validated_fy).first()
    if not db_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र ड तपशील सापडला नाही")
    update_data = detail.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_detail, key, value)
    db.commit()
    db.refresh(db_detail)
    return db_detail

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_post_detail(id: int, db: Session = Depends(get_db)):
    db_detail = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id).first()
    if not db_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र ड तपशील सापडला नाही")
    db.delete(db_detail)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)