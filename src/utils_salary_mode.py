"""Salary mode utilities for monthly/annual toggle functionality"""
from sqlalchemy.orm import Session
from typing import Optional
from src.utils_cache import memory_cache

SALARY_MODE_MONTHLY = 'monthly'
SALARY_MODE_ANNUAL = 'annual'
SALARY_MODE_CACHE_PREFIX = "salary_mode_"
SALARY_MODE_CACHE_TTL = 300

ANNUAL_MULTIPLIER = 12


def get_salary_mode(db: Session, fiscal_year: str) -> str:
    """Get salary mode for fiscal year (cached)"""
    if not fiscal_year:
        return SALARY_MODE_MONTHLY
    
    cache_key = f"{SALARY_MODE_CACHE_PREFIX}{fiscal_year}"
    cached = memory_cache.get(cache_key)
    if cached:
        return cached
    
    from src import models
    fy = db.query(models.FiscalYear.salary_mode).filter(
        models.FiscalYear.year_range == fiscal_year
    ).first()
    
    mode = fy[0] if fy and fy[0] else SALARY_MODE_MONTHLY
    memory_cache.set(cache_key, mode, SALARY_MODE_CACHE_TTL)
    return mode


def update_salary_mode(db: Session, fiscal_year: str, mode: str) -> bool:
    """Update salary mode for fiscal year"""
    if mode not in (SALARY_MODE_MONTHLY, SALARY_MODE_ANNUAL):
        return False
    
    from src import models
    fy = db.query(models.FiscalYear).filter(
        models.FiscalYear.year_range == fiscal_year
    ).first()
    
    if not fy:
        return False
    
    fy.salary_mode = mode
    db.commit()
    
    cache_key = f"{SALARY_MODE_CACHE_PREFIX}{fiscal_year}"
    memory_cache.delete(cache_key)
    return True


def is_annual_mode(db: Session, fiscal_year: str) -> bool:
    """Check if annual mode is active for fiscal year"""
    return get_salary_mode(db, fiscal_year) == SALARY_MODE_ANNUAL


def get_multiplier(mode: str) -> int:
    """Get multiplier based on mode"""
    return ANNUAL_MULTIPLIER if mode == SALARY_MODE_ANNUAL else 1

