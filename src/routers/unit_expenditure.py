from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from src import models
from src.database import SessionLocal, get_db
from src.utils_fiscal_year import validate_fiscal_year

router = APIRouter(
    prefix="/api/unit_expenditure",
    tags=["API - प्रपत्र अ"]
)

class UnitExpenditureBase(BaseModel):
    fiscal_year: Optional[str] = None
    PrimaryAndSecondaryUnitsOfAccount: Optional[str] = None
    District: Optional[str] = None
    ActualAmountExpenditure20212022: Optional[int] = None
    ActualAmountExpenditure20222023: Optional[int] = None
    ActualAmountExpenditure20232024: Optional[int] = None
    BudgetaryEstimates20242025: Optional[int] = None
    ImprovedForecast20242025: Optional[int] = None
    BudgetaryEstimates20252026EstimatingOfficer: Optional[int] = None
    BudgetaryEstimates20252026ControllingOfficer: Optional[int] = None
    BudgetaryEstimates20252026AdministrativeDepartment: Optional[int] = None
    BudgetaryEstimates20252026FinanceDepartment: Optional[int] = None

class UnitExpenditureCreate(UnitExpenditureBase):
    PrimaryAndSecondaryUnitsOfAccount: str
    District: str

class UnitExpenditureUpdate(UnitExpenditureBase):
    pass

class UnitExpenditureResponse(UnitExpenditureBase):
    id: int
    class Config: from_attributes = True

@router.get("/", response_model=List[UnitExpenditureResponse])
def get_unit_expenditures(skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    validated_fy = validate_fiscal_year(fiscal_year, db)
    return db.query(models.UnitExpenditure).filter(models.UnitExpenditure.fiscal_year == validated_fy).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=UnitExpenditureResponse)
def get_unit_expenditure(id: int, fiscal_year: Optional[str] = None, db: Session = Depends(get_db)):
    validated_fy = validate_fiscal_year(fiscal_year, db)
    expenditure = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id, models.UnitExpenditure.fiscal_year == validated_fy).first()
    if not expenditure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र अ तपशील सापडला नाही")
    return expenditure

@router.post("/", response_model=UnitExpenditureResponse, status_code=status.HTTP_201_CREATED)
def create_unit_expenditure(expenditure: UnitExpenditureCreate, db: Session = Depends(get_db)):
    exp_data = expenditure.model_dump()
    exp_data['fiscal_year'] = validate_fiscal_year(exp_data.get('fiscal_year'), db)
    db_expenditure = models.UnitExpenditure(**exp_data)
    db.add(db_expenditure)
    db.commit()
    db.refresh(db_expenditure)
    return db_expenditure

@router.put("/{id}", response_model=UnitExpenditureResponse)
def update_unit_expenditure(id: int, expenditure: UnitExpenditureUpdate, db: Session = Depends(get_db)):
    db_expenditure = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id, models.UnitExpenditure.fiscal_year == expenditure.fiscal_year).first()
    if not db_expenditure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र अ तपशील सापडला नाही")
    update_data = expenditure.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_expenditure, key, value)
    db.commit()
    db.refresh(db_expenditure)
    return db_expenditure

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit_expenditure(id: int, db: Session = Depends(get_db)):
    db_expenditure = db.query(models.UnitExpenditure).filter(models.UnitExpenditure.id == id).first()
    if not db_expenditure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="प्रपत्र अ तपशील सापडला नाही")
    db.delete(db_expenditure)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)