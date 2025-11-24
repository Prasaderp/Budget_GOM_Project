from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from src import models
from src.database import SessionLocal, get_db

router = APIRouter(
    prefix="/api/post_expenses",
    tags=["API - प्रपत्र ब"]
)

class PostExpensesBase(BaseModel):
    fiscal_year: Optional[str] = '2025-26'
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
def get_post_expenses(skip: int = 0, limit: int = 100, fiscal_year: str = '2025-26', db: Session = Depends(get_db)):
    return db.query(models.PostExpenses).filter(models.PostExpenses.fiscal_year == fiscal_year).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=PostExpensesResponse)
def get_post_expense(id: int, fiscal_year: str = '2025-26', db: Session = Depends(get_db)):
    expense = db.query(models.PostExpenses).filter(models.PostExpenses.id == id, models.PostExpenses.fiscal_year == fiscal_year).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र ब तपशील सापडला नाही")
    return expense

@router.post("/", response_model=PostExpensesResponse, status_code=status.HTTP_201_CREATED)
def create_post_expense(expense: PostExpensesCreate, db: Session = Depends(get_db)):
    payload = expense.model_dump()
    district = payload.get("District")
    seven_keys = [
        "MedicalExpenses",
        "FestivalAdvance",
        "SwagramMaharashtraDarshan",
        "SeventhPayCommissionDifferenceNPS",
        "NPS",
        "SeventhPayCommissionDifference",
        "Other",
    ]
    mapping = {
        "MedicalExpenses": "medical_expenses",
        "FestivalAdvance": "festival_advance",
        "SwagramMaharashtraDarshan": "swagram_maharashtra_darshan",
        "SeventhPayCommissionDifferenceNPS": "seventh_pay_commission_difference_nps",
        "NPS": "nps",
        "SeventhPayCommissionDifference": "seventh_pay_commission_difference",
        "Other": "other",
    }
    if district:
        existing = (
            db.query(models.PostExpenses)
            .filter(models.PostExpenses.district == district)
            .first()
        )
        if existing:
            for k in seven_keys:
                if payload.get(k) is None:
                    payload[k] = getattr(existing, mapping[k])
    snake_payload = {
        "fiscal_year": payload.get("fiscal_year", '2025-26'),
        "class_type": payload.get("Class"),
        "category": payload.get("Category"),
        "district": payload.get("District"),
        "filled_posts": payload.get("FilledPosts"),
        "vacant_posts": payload.get("VacantPosts"),
        "medical_expenses": payload.get("MedicalExpenses"),
        "festival_advance": payload.get("FestivalAdvance"),
        "swagram_maharashtra_darshan": payload.get("SwagramMaharashtraDarshan"),
        "seventh_pay_commission_difference_nps": payload.get("SeventhPayCommissionDifferenceNPS"),
        "nps": payload.get("NPS"),
        "seventh_pay_commission_difference": payload.get("SeventhPayCommissionDifference"),
        "other": payload.get("Other"),
    }
    db_expense = models.PostExpenses(**snake_payload)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.put("/{id}", response_model=PostExpensesResponse)
def update_post_expense(id: int, expense: PostExpensesUpdate, db: Session = Depends(get_db)):
    db_expense = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र ब तपशील सापडला नाही")
    payload = expense.model_dump(exclude_unset=True)
    mapping = {
        "Class": "class_type",
        "Category": "category",
        "District": "district",
        "FilledPosts": "filled_posts",
        "VacantPosts": "vacant_posts",
        "MedicalExpenses": "medical_expenses",
        "FestivalAdvance": "festival_advance",
        "SwagramMaharashtraDarshan": "swagram_maharashtra_darshan",
        "SeventhPayCommissionDifferenceNPS": "seventh_pay_commission_difference_nps",
        "NPS": "nps",
        "SeventhPayCommissionDifference": "seventh_pay_commission_difference",
        "Other": "other",
    }
    for key, value in payload.items():
        attr = mapping.get(key)
        if attr:
            setattr(db_expense, attr, value)
    seven_attrs = [
        "medical_expenses",
        "festival_advance",
        "swagram_maharashtra_darshan",
        "seventh_pay_commission_difference_nps",
        "nps",
        "seventh_pay_commission_difference",
        "other",
    ]
    district = payload.get("District", db_expense.district)
    sync_update = {}
    for p_key, attr in mapping.items():
        if attr in seven_attrs and p_key in payload and payload[p_key] is not None:
            sync_update[attr] = payload[p_key]
    if sync_update and district:
        db.query(models.PostExpenses).filter(models.PostExpenses.district == district).update(sync_update, synchronize_session=False)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post_expense(id: int, db: Session = Depends(get_db)):
    db_expense = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र ब तपशील सापडला नाही")
    db.delete(db_expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)