"""DA (Dearness Allowance) rate utilities for configurable percentage per fiscal year

This module provides utilities to manage and retrieve DA percentage configuration
from the fiscal_years table, replacing the hardcoded 64% value throughout the system.

Pattern follows: utils_salary_mode.py
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from typing import Optional
from src.utils_cache import memory_cache

DEFAULT_DA_PERCENTAGE = Decimal('64.00')
DA_PERCENTAGE_CACHE_PREFIX = "da_percentage_"
DA_RATE_CACHE_PREFIX = "da_rate_"
DA_CACHE_TTL = 300


def get_da_percentage(db: Session, fiscal_year: Optional[str]) -> Decimal:
    """Get DA percentage for fiscal year (cached)
    
    Args:
        db: Database session
        fiscal_year: Fiscal year in format 'YYYY-YY' (e.g., '2025-26')
    
    Returns:
        Decimal: DA percentage (e.g., Decimal('64.00') for 64%)
        
    Note:
        Returns default 64.00 if fiscal_year is None or not found
    """
    if not fiscal_year:
        return DEFAULT_DA_PERCENTAGE
    
    cache_key = f"{DA_PERCENTAGE_CACHE_PREFIX}{fiscal_year}"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return Decimal(str(cached))
    
    from src import models
    result = db.query(models.FiscalYear.da_percentage).filter(
        models.FiscalYear.year_range == fiscal_year
    ).first()
    
    percentage = Decimal(str(result[0])) if result and result[0] is not None else DEFAULT_DA_PERCENTAGE
    memory_cache.set(cache_key, float(percentage), DA_CACHE_TTL)
    return percentage


def get_da_rate(db: Session, fiscal_year: Optional[str]) -> float:
    """Get DA rate as decimal multiplier for calculations
    
    Args:
        db: Database session
        fiscal_year: Fiscal year in format 'YYYY-YY'
    
    Returns:
        float: DA rate as decimal (e.g., 0.64 for 64%, 0.70 for 70%)
        
    Usage:
        da_rate = get_da_rate(db, '2025-26')
        da_amount = base_pay * da_rate  # Calculate DA amount
    """
    if not fiscal_year:
        return float(DEFAULT_DA_PERCENTAGE) / 100.0
    
    cache_key = f"{DA_RATE_CACHE_PREFIX}{fiscal_year}"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return float(cached)
    
    percentage = get_da_percentage(db, fiscal_year)
    rate = float(percentage) / 100.0
    
    memory_cache.set(cache_key, rate, DA_CACHE_TTL)
    return rate


def update_da_percentage(db: Session, fiscal_year: str, percentage: float) -> bool:
    """Update DA percentage for fiscal year and invalidate cache
    
    Args:
        db: Database session
        fiscal_year: Fiscal year in format 'YYYY-YY'
        percentage: New DA percentage (0-100)
    
    Returns:
        bool: True if update successful, False otherwise
        
    Security:
        Should only be called after validating DCO assistant authorization
    """
    if not fiscal_year:
        return False
    
    if percentage < 0 or percentage > 100:
        return False
    
    from src import models
    fy = db.query(models.FiscalYear).filter(
        models.FiscalYear.year_range == fiscal_year
    ).first()
    
    if not fy:
        return False
    
    fy.da_percentage = Decimal(str(percentage))
    db.commit()
    
    _invalidate_cache(fiscal_year)
    return True


def _invalidate_cache(fiscal_year: str) -> None:
    """Invalidate both percentage and rate caches for fiscal year"""
    memory_cache.delete(f"{DA_PERCENTAGE_CACHE_PREFIX}{fiscal_year}")
    memory_cache.delete(f"{DA_RATE_CACHE_PREFIX}{fiscal_year}")


def validate_da_percentage(percentage: float) -> tuple[bool, Optional[str]]:
    """Validate DA percentage value
    
    Args:
        percentage: DA percentage to validate
    
    Returns:
        tuple: (is_valid: bool, error_message: Optional[str])
    """
    if percentage is None:
        return False, "DA percentage cannot be None"
    
    try:
        numeric_value = float(percentage)
    except (ValueError, TypeError):
        return False, "DA percentage must be a valid number"
    
    if numeric_value < 0:
        return False, "DA percentage cannot be negative"
    
    if numeric_value > 100:
        return False, "DA percentage cannot exceed 100"
    
    return True, None
