"""Post Expenses module for sub-scheme 20530028"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from .repositories.post_expenses_repository import PostExpensesRepository
from .services.summary_service import PostExpensesSummaryService
from .services.charts_service import PostExpensesChartsService


# Backward-compatible function wrappers for external callers
def get_post_expenses_summary_data(
    db: Session,
    fiscal_year: str = '2025-26',
    district: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Backward-compatible wrapper for summary data"""
    repository = PostExpensesRepository(db)
    service = PostExpensesSummaryService(repository)
    return service.get_summary_data(fiscal_year, district)


def get_district_post_expenses_summary_data(
    db: Session,
    district: str,
    fiscal_year: str
) -> Optional[Dict[str, Any]]:
    """Backward-compatible wrapper for district summary data"""
    return get_post_expenses_summary_data(db, fiscal_year, district=district)


def get_post_expenses_charts_data(
    db: Session,
    fiscal_year: str = '2025-26',
    district: Optional[str] = None
) -> Dict[str, Any]:
    """Backward-compatible wrapper for charts data"""
    repository = PostExpensesRepository(db)
    service = PostExpensesChartsService(repository)
    return service.get_charts_data(fiscal_year, district)


def get_district_post_expenses_charts_data(
    db: Session,
    district: str,
    fiscal_year: str
) -> Dict[str, Any]:
    """Backward-compatible wrapper for district charts data"""
    return get_post_expenses_charts_data(db, fiscal_year, district=district)


__all__ = [
    'get_post_expenses_summary_data',
    'get_district_post_expenses_summary_data',
    'get_post_expenses_charts_data',
    'get_district_post_expenses_charts_data'
]

