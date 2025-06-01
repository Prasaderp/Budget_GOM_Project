from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from models import BudgetPostDetails
from database import SessionLocal, get_db

router = APIRouter(
    prefix="/api/budget_post_details",
    tags=["API - Budget Post Details"]
)

class BudgetPostDetailsBase(BaseModel):
    District: Optional[str] = None
    Category: Optional[str] = None
    Class: Optional[str] = None
    Designation: Optional[str] = None
    SanctionedPosts202425: Optional[int] = None
    SanctionedPosts202526: Optional[int] = None
    SpecialPay: Optional[int] = None
    BasicPay: Optional[int] = None
    GradePay: Optional[int] = None
    DearnessAllowance64: Optional[int] = None
    LocalSupplemetoryAllowance: Optional[int] = None
    LocalHRA: Optional[int] = None
    VehicleAllowance: Optional[int] = None
    WashingAllowance: Optional[int] = None
    CashAllowance: Optional[int] = None
    FootWareAllowanceOther: Optional[int] = None

class BudgetPostDetailsCreate(BudgetPostDetailsBase):
    District: str
    Category: str
    Class: str
    Designation: str

class BudgetPostDetailsUpdate(BudgetPostDetailsBase):
     pass

class BudgetPostDetailsResponse(BudgetPostDetailsBase):
    id: int
    class Config: from_attributes = True

@router.get("/", response_model=List[BudgetPostDetailsResponse])
def get_budget_post_details(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(BudgetPostDetails).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=BudgetPostDetailsResponse)
def get_budget_post_detail(id: int, db: Session = Depends(get_db)):
    detail = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id).first()
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget Post Detail not found")
    return detail

@router.post("/", response_model=BudgetPostDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_budget_post_detail(detail: BudgetPostDetailsCreate, db: Session = Depends(get_db)):
    db_detail = BudgetPostDetails(**detail.model_dump())
    db.add(db_detail)
    db.commit()
    db.refresh(db_detail)
    return db_detail

@router.put("/{id}", response_model=BudgetPostDetailsResponse)
def update_budget_post_detail(id: int, detail: BudgetPostDetailsUpdate, db: Session = Depends(get_db)):
    db_detail = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id).first()
    if not db_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget Post Detail not found")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget Post Detail not found")
    db.delete(db_detail)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)