"""API routes for sub-scheme 20530313 - District Administration (Voted)

This module provides REST API endpoints for CRUD operations.
The UI routes are in router_ui.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Type, TypeVar

from src.database import get_db
from src.utils_fiscal_year import validate_fiscal_year
from .models import BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure
from .schemas import (
    BudgetPostDetailsCreate, BudgetPostDetailsUpdate, BudgetPostDetailsResponse,
    PostStatusCreate, PostStatusUpdate, PostStatusResponse,
    PostExpensesCreate, PostExpensesUpdate, PostExpensesResponse,
    UnitExpenditureCreate, UnitExpenditureUpdate, UnitExpenditureResponse
)
from .config import SCHEME_CONFIG

router = APIRouter(prefix=f"/api/schemes/{SCHEME_CONFIG.code}", tags=[f"API - {SCHEME_CONFIG.name_mr}"])

T = TypeVar('T')

def _get_item_or_404(model: Type[T], item_id: int, db: Session) -> T:
    """Get item by ID or raise 404"""
    item = db.query(model).filter(model.id == item_id, model.sub_scheme_code == SCHEME_CONFIG.code).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    return item

def _create_crud_routes(
    model: Type[T],
    create_schema: type,
    update_schema: type,
    response_schema: type,
    route_prefix: str
):
    """Factory function to create CRUD routes for a model"""
    
    @router.get(f"/{route_prefix}", response_model=List[response_schema])
    def list_items(skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
        fy = validate_fiscal_year(fiscal_year, db)
        return db.query(model).filter(
            model.fiscal_year == fy,
            model.sub_scheme_code == SCHEME_CONFIG.code
        ).offset(skip).limit(limit).all()

    @router.get(f"/{route_prefix}/{{id}}", response_model=response_schema)
    def get_item(id: int, db: Session = Depends(get_db)):
        return _get_item_or_404(model, id, db)

    @router.post(f"/{route_prefix}", response_model=response_schema, status_code=201)
    def create_item(data: create_schema, db: Session = Depends(get_db)):
        item_data = data.model_dump()
        item_data['fiscal_year'] = validate_fiscal_year(item_data.get('fiscal_year'), db)
        item_data['scheme_code'] = SCHEME_CONFIG.parent_scheme
        item_data['sub_scheme_code'] = SCHEME_CONFIG.code
        db_item = model(**item_data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    @router.put(f"/{route_prefix}/{{id}}", response_model=response_schema)
    def update_item(id: int, data: update_schema, db: Session = Depends(get_db)):
        db_item = _get_item_or_404(model, id, db)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(db_item, key, value)
        db.commit()
        db.refresh(db_item)
        return db_item

    @router.delete(f"/{route_prefix}/{{id}}", status_code=204)
    def delete_item(id: int, db: Session = Depends(get_db)):
        db_item = _get_item_or_404(model, id, db)
        db.delete(db_item)
        db.commit()
        return Response(status_code=204)

_create_crud_routes(
    BudgetPostDetails,
    BudgetPostDetailsCreate,
    BudgetPostDetailsUpdate,
    BudgetPostDetailsResponse,
    "budget-post-details"
)

_create_crud_routes(
    PostStatus,
    PostStatusCreate,
    PostStatusUpdate,
    PostStatusResponse,
    "post-status"
)

_create_crud_routes(
    PostExpenses,
    PostExpensesCreate,
    PostExpensesUpdate,
    PostExpensesResponse,
    "post-expenses"
)

_create_crud_routes(
    UnitExpenditure,
    UnitExpenditureCreate,
    UnitExpenditureUpdate,
    UnitExpenditureResponse,
    "unit-expenditure"
)
