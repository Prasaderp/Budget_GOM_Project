from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from src import models

DEFAULT_FISCAL_YEAR = '2025-26'

def get_default_fiscal_year(db: Session) -> str:
    """Get the latest active fiscal year from database"""
    fiscal_year = db.query(models.FiscalYear).filter(
        models.FiscalYear.is_active == True
    ).order_by(models.FiscalYear.year_range.desc()).first()
    return fiscal_year.year_range if fiscal_year else DEFAULT_FISCAL_YEAR

def validate_fiscal_year(fiscal_year: Optional[str], db: Session) -> str:
    """Validate fiscal year exists and is active, return default if invalid"""
    if not fiscal_year:
        return get_default_fiscal_year(db)
    
    exists = db.query(models.FiscalYear).filter(
        models.FiscalYear.year_range == fiscal_year,
        models.FiscalYear.is_active == True
    ).first()
    
    if exists:
        return fiscal_year
    
    return get_default_fiscal_year(db)

async def get_validated_fiscal_year(request: Request, db: Session) -> str:
    """FastAPI dependency to get validated fiscal year from cookie"""
    cookie_fy = request.cookies.get('fiscal_year')
    return validate_fiscal_year(cookie_fy, db)

def get_fiscal_year_from_request(request: Request, db: Session) -> str:
    """Get validated fiscal year from request (for non-dependency use)"""
    cookie_fy = request.cookies.get('fiscal_year')
    return validate_fiscal_year(cookie_fy, db)

