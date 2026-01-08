from fastapi import Request
from sqlalchemy.orm import Session
from typing import Optional
from src import models
from src.utils_cache import memory_cache

DEFAULT_FISCAL_YEAR = '2025-26'
FY_DEFAULT_CACHE_KEY = "fy_default"
FY_VALID_CACHE_PREFIX = "fy_valid_"

def get_default_fiscal_year(db: Session) -> str:
    cached = memory_cache.get(FY_DEFAULT_CACHE_KEY)
    if cached:
        return cached
    
    fiscal_year = db.query(models.FiscalYear.year_range).filter(
        models.FiscalYear.is_active == True
    ).order_by(models.FiscalYear.year_range.desc()).first()
    
    result = fiscal_year[0] if fiscal_year else DEFAULT_FISCAL_YEAR
    memory_cache.set(FY_DEFAULT_CACHE_KEY, result, 300)
    return result

def validate_fiscal_year(fiscal_year: Optional[str], db: Session) -> str:
    if not fiscal_year:
        return get_default_fiscal_year(db)
    
    cache_key = f"{FY_VALID_CACHE_PREFIX}{fiscal_year}"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return fiscal_year if cached else get_default_fiscal_year(db)
    
    exists = db.query(models.FiscalYear.id).filter(
        models.FiscalYear.year_range == fiscal_year,
        models.FiscalYear.is_active == True
    ).first()
    
    memory_cache.set(cache_key, exists is not None, 300)
    return fiscal_year if exists else get_default_fiscal_year(db)

async def get_validated_fiscal_year(request: Request, db: Session) -> str:
    cookie_fy = request.cookies.get('fiscal_year')
    return validate_fiscal_year(cookie_fy, db)

def get_fiscal_year_from_request(request: Request, db: Session) -> str:
    cookie_fy = request.cookies.get('fiscal_year')
    return validate_fiscal_year(cookie_fy, db)

