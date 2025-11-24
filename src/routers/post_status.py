from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from src import models
from src.database import SessionLocal, get_db

router = APIRouter(
    prefix="/api/post_status",
    tags=["API - प्रपत्र क"]
)

class PostStatusBase(BaseModel):
    fiscal_year: Optional[str] = '2025-26'
    District: Optional[str] = None
    Category: Optional[str] = None
    Class: Optional[str] = None
    Status: Optional[str] = None
    Posts: Optional[int] = None
    Salary: Optional[int] = None
    GradePay: Optional[int] = None
    SpecialPay: Optional[int] = None
    DearnessAllowance: Optional[int] = None
    LocalSupplemetoryAllowance: Optional[int] = None
    HouseRentAllowance: Optional[int] = None
    TravelAllowance: Optional[int] = None
    Other: Optional[int] = None

class PostStatusCreate(PostStatusBase):
    District: str
    Category: str
    Class: str
    Status: str

class PostStatusUpdate(PostStatusBase):
    pass

class PostStatusResponse(PostStatusBase):
    id: int
    class Config: from_attributes = True

@router.get("/", response_model=List[PostStatusResponse])
def get_post_statuses(skip: int = 0, limit: int = 100, fiscal_year: str = '2025-26', db: Session = Depends(get_db)):
    return db.query(models.PostStatus).filter(models.PostStatus.fiscal_year == fiscal_year).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=PostStatusResponse)
def get_post_status(id: int, fiscal_year: str = '2025-26', db: Session = Depends(get_db)):
    status_obj = db.query(models.PostStatus).filter(models.PostStatus.id == id, models.PostStatus.fiscal_year == fiscal_year).first()
    if not status_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र क तपशील सापडला नाही")
    return status_obj

@router.post("/", response_model=PostStatusResponse, status_code=status.HTTP_201_CREATED)
def create_post_status(status_data: PostStatusCreate, db: Session = Depends(get_db)):
    payload = status_data.model_dump()
    mapped = {
        "fiscal_year": payload.get("fiscal_year", '2025-26'),
        "district": payload.get("District"),
        "category": payload.get("Category"),
        "class_type": payload.get("Class"),
        "status": payload.get("Status"),
        "posts": payload.get("Posts", 0),
        "salary": payload.get("Salary", 0),
        "grade_pay": payload.get("GradePay", 0),
        "special_pay": payload.get("SpecialPay", 0),
        "dearness_allowance": payload.get("DearnessAllowance", 0),
        "local_supplementary_allowance": payload.get("LocalSupplemetoryAllowance", 0),
        "house_rent_allowance": payload.get("HouseRentAllowance", 0),
        "travel_allowance": payload.get("TravelAllowance", 0),
        "other": payload.get("Other", 0),
    }
    db_status = models.PostStatus(**mapped)
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.put("/{id}", response_model=PostStatusResponse)
def update_post_status(id: int, status_data: PostStatusUpdate, db: Session = Depends(get_db)):
    db_status = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not db_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र क तपशील सापडला नाही")
    payload = status_data.model_dump(exclude_unset=True)
    mapped = {
        "district": payload.get("District"),
        "category": payload.get("Category"),
        "class_type": payload.get("Class"),
        "status": payload.get("Status"),
        "posts": payload.get("Posts"),
        "salary": payload.get("Salary"),
        "grade_pay": payload.get("GradePay"),
        "special_pay": payload.get("SpecialPay"),
        "dearness_allowance": payload.get("DearnessAllowance"),
        "local_supplementary_allowance": payload.get("LocalSupplemetoryAllowance"),
        "house_rent_allowance": payload.get("HouseRentAllowance"),
        "travel_allowance": payload.get("TravelAllowance"),
        "other": payload.get("Other"),
    }
    for key, value in mapped.items():
        if value is not None:
            setattr(db_status, key, value)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post_status(id: int, db: Session = Depends(get_db)):
    db_status = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not db_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र क तपशील सापडला नाही")
    db.delete(db_status)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)