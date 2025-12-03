"""API routes for sub-scheme 20530028 - District Administration (Voted)

This module provides REST API endpoints for CRUD operations.
The UI routes are in router_ui.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from src.models import BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure
from .schemas import (
    BudgetPostDetailsCreate, BudgetPostDetailsUpdate, BudgetPostDetailsResponse,
    PostStatusCreate, PostStatusUpdate, PostStatusResponse,
    PostExpensesCreate, PostExpensesUpdate, PostExpensesResponse,
    UnitExpenditureCreate, UnitExpenditureUpdate, UnitExpenditureResponse
)
from .models import SCHEME_CODE, SUB_SCHEME_CODE

router = APIRouter(prefix="/api/s20530028", tags=["API - 20530028 जिल्हा प्रशासन"])

# Budget Post Details endpoints
@router.get("/budget-post-details", response_model=List[BudgetPostDetailsResponse])
def list_budget_post_details(skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    fy = validate_fiscal_year(fiscal_year, db)
    return db.query(BudgetPostDetails).filter(
        BudgetPostDetails.fiscal_year == fy,
        BudgetPostDetails.sub_scheme_code == SUB_SCHEME_CODE
    ).offset(skip).limit(limit).all()

@router.get("/budget-post-details/{id}", response_model=BudgetPostDetailsResponse)
def get_budget_post_detail(id: int, db: Session = Depends(get_db)):
    item = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == SUB_SCHEME_CODE
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    return item

@router.post("/budget-post-details", response_model=BudgetPostDetailsResponse, status_code=201)
def create_budget_post_detail(data: BudgetPostDetailsCreate, db: Session = Depends(get_db)):
    item_data = data.model_dump()
    item_data['fiscal_year'] = validate_fiscal_year(item_data.get('fiscal_year'), db)
    item_data['scheme_code'] = SCHEME_CODE
    item_data['sub_scheme_code'] = SUB_SCHEME_CODE
    db_item = BudgetPostDetails(**item_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/budget-post-details/{id}", response_model=BudgetPostDetailsResponse)
def update_budget_post_detail(id: int, data: BudgetPostDetailsUpdate, db: Session = Depends(get_db)):
    db_item = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == SUB_SCHEME_CODE
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/budget-post-details/{id}", status_code=204)
def delete_budget_post_detail(id: int, db: Session = Depends(get_db)):
    db_item = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == SUB_SCHEME_CODE
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(db_item)
    db.commit()
    return Response(status_code=204)

# Post Status endpoints
@router.get("/post-status", response_model=List[PostStatusResponse])
def list_post_status(skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    fy = validate_fiscal_year(fiscal_year, db)
    return db.query(PostStatus).filter(
        PostStatus.fiscal_year == fy,
        PostStatus.sub_scheme_code == SUB_SCHEME_CODE
    ).offset(skip).limit(limit).all()

@router.get("/post-status/{id}", response_model=PostStatusResponse)
def get_post_status(id: int, db: Session = Depends(get_db)):
    item = db.query(PostStatus).filter(PostStatus.id == id, PostStatus.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    return item

@router.post("/post-status", response_model=PostStatusResponse, status_code=201)
def create_post_status(data: PostStatusCreate, db: Session = Depends(get_db)):
    item_data = data.model_dump()
    item_data['fiscal_year'] = validate_fiscal_year(item_data.get('fiscal_year'), db)
    item_data['scheme_code'] = SCHEME_CODE
    item_data['sub_scheme_code'] = SUB_SCHEME_CODE
    db_item = PostStatus(**item_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/post-status/{id}", response_model=PostStatusResponse)
def update_post_status(id: int, data: PostStatusUpdate, db: Session = Depends(get_db)):
    db_item = db.query(PostStatus).filter(PostStatus.id == id, PostStatus.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/post-status/{id}", status_code=204)
def delete_post_status(id: int, db: Session = Depends(get_db)):
    db_item = db.query(PostStatus).filter(PostStatus.id == id, PostStatus.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(db_item)
    db.commit()
    return Response(status_code=204)

# Post Expenses endpoints
@router.get("/post-expenses", response_model=List[PostExpensesResponse])
def list_post_expenses(skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    fy = validate_fiscal_year(fiscal_year, db)
    return db.query(PostExpenses).filter(
        PostExpenses.fiscal_year == fy,
        PostExpenses.sub_scheme_code == SUB_SCHEME_CODE
    ).offset(skip).limit(limit).all()

@router.get("/post-expenses/{id}", response_model=PostExpensesResponse)
def get_post_expense(id: int, db: Session = Depends(get_db)):
    item = db.query(PostExpenses).filter(PostExpenses.id == id, PostExpenses.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    return item

@router.post("/post-expenses", response_model=PostExpensesResponse, status_code=201)
def create_post_expense(data: PostExpensesCreate, db: Session = Depends(get_db)):
    item_data = data.model_dump()
    item_data['fiscal_year'] = validate_fiscal_year(item_data.get('fiscal_year'), db)
    item_data['scheme_code'] = SCHEME_CODE
    item_data['sub_scheme_code'] = SUB_SCHEME_CODE
    db_item = PostExpenses(**item_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/post-expenses/{id}", response_model=PostExpensesResponse)
def update_post_expense(id: int, data: PostExpensesUpdate, db: Session = Depends(get_db)):
    db_item = db.query(PostExpenses).filter(PostExpenses.id == id, PostExpenses.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/post-expenses/{id}", status_code=204)
def delete_post_expense(id: int, db: Session = Depends(get_db)):
    db_item = db.query(PostExpenses).filter(PostExpenses.id == id, PostExpenses.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(db_item)
    db.commit()
    return Response(status_code=204)

# Unit Expenditure endpoints
@router.get("/unit-expenditure", response_model=List[UnitExpenditureResponse])
def list_unit_expenditure(skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    fy = validate_fiscal_year(fiscal_year, db)
    return db.query(UnitExpenditure).filter(
        UnitExpenditure.fiscal_year == fy,
        UnitExpenditure.sub_scheme_code == SUB_SCHEME_CODE
    ).offset(skip).limit(limit).all()

@router.get("/unit-expenditure/{id}", response_model=UnitExpenditureResponse)
def get_unit_expenditure(id: int, db: Session = Depends(get_db)):
    item = db.query(UnitExpenditure).filter(UnitExpenditure.id == id, UnitExpenditure.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    return item

@router.post("/unit-expenditure", response_model=UnitExpenditureResponse, status_code=201)
def create_unit_expenditure(data: UnitExpenditureCreate, db: Session = Depends(get_db)):
    item_data = data.model_dump()
    item_data['fiscal_year'] = validate_fiscal_year(item_data.get('fiscal_year'), db)
    item_data['scheme_code'] = SCHEME_CODE
    item_data['sub_scheme_code'] = SUB_SCHEME_CODE
    db_item = UnitExpenditure(**item_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/unit-expenditure/{id}", response_model=UnitExpenditureResponse)
def update_unit_expenditure(id: int, data: UnitExpenditureUpdate, db: Session = Depends(get_db)):
    db_item = db.query(UnitExpenditure).filter(UnitExpenditure.id == id, UnitExpenditure.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/unit-expenditure/{id}", status_code=204)
def delete_unit_expenditure(id: int, db: Session = Depends(get_db)):
    db_item = db.query(UnitExpenditure).filter(UnitExpenditure.id == id, UnitExpenditure.sub_scheme_code == SUB_SCHEME_CODE).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(db_item)
    db.commit()
    return Response(status_code=204)

