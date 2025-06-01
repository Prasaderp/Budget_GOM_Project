from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import models
from database import SessionLocal, get_db

router = APIRouter(
    prefix="/api/post_status",
    tags=["API - Post Status"]
)

class PostStatusBase(BaseModel):
    District: Optional[str] = None
    Category: Optional[str] = None
    Class: Optional[str] = None
    Status: Optional[str] = None
    Posts: Optional[int] = None
    Salary: Optional[int] = None
    GradePay: Optional[int] = None
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
def get_post_statuses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.PostStatus).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=PostStatusResponse)
def get_post_status(id: int, db: Session = Depends(get_db)):
    status_obj = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not status_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post Status not found")
    return status_obj

@router.post("/", response_model=PostStatusResponse, status_code=status.HTTP_201_CREATED)
def create_post_status(status_data: PostStatusCreate, db: Session = Depends(get_db)):
    db_status = models.PostStatus(**status_data.model_dump())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.put("/{id}", response_model=PostStatusResponse)
def update_post_status(id: int, status_data: PostStatusUpdate, db: Session = Depends(get_db)):
    db_status = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not db_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post Status not found")
    update_data = status_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_status, key, value)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post_status(id: int, db: Session = Depends(get_db)):
    db_status = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not db_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post Status not found")
    db.delete(db_status)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)