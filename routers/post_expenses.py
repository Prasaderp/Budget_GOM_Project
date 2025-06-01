from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import models
from database import SessionLocal, get_db

router = APIRouter(
    prefix="/api/post_expenses",
    tags=["API - Post Expenses"]
)

class PostExpensesBase(BaseModel):
    Class: Optional[str] = None
    Category: Optional[str] = None
    FilledPosts: Optional[int] = None
    VacantPosts: Optional[int] = None
    District: Optional[str] = None
    MedicalExpenses: Optional[int] = None
    FestivalAdvance: Optional[int] = None
    SwagramMaharashtraDarshan: Optional[int] = None
    SeventhPayCommissionDifferenceNPS: Optional[float] = None
    NPS: Optional[float] = None
    SeventhPayCommissionDifference: Optional[float] = None
    Other: Optional[int] = None

class PostExpensesCreate(PostExpensesBase):
    Class: str
    Category: str
    District: str

class PostExpensesUpdate(PostExpensesBase):
    pass

class PostExpensesResponse(PostExpensesBase):
    id: int
    class Config: from_attributes = True

@router.get("/", response_model=List[PostExpensesResponse])
def get_post_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.PostExpenses).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=PostExpensesResponse)
def get_post_expense(id: int, db: Session = Depends(get_db)):
    expense = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post Expense not found")
    return expense

@router.post("/", response_model=PostExpensesResponse, status_code=status.HTTP_201_CREATED)
def create_post_expense(expense: PostExpensesCreate, db: Session = Depends(get_db)):
    db_expense = models.PostExpenses(**expense.model_dump())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.put("/{id}", response_model=PostExpensesResponse)
def update_post_expense(id: int, expense: PostExpensesUpdate, db: Session = Depends(get_db)):
    db_expense = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post Expense not found")
    update_data = expense.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_expense, key, value)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post_expense(id: int, db: Session = Depends(get_db)):
    db_expense = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post Expense not found")
    db.delete(db_expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)