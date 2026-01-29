"""Shared district expenditure infrastructure for s2045 sub-schemes.

This module provides reusable components for simple district-wise expenditure tables:
- 20450182: Stamp duty collection recovery (7 Konkan districts)
- 20450251: Grants under Education Cess Act (5 districts, no Mumbai)
- 20450262: Collection recovery & Employment Cess (7 Konkan districts)

All 3 sub-schemes share the SAME Excel file (Sheet 1) with tables at different rows.
Use the unified export function to download data for all sub-schemes together.
"""
from .base_models import create_district_expenditure_model
from .base_schemas import create_district_expenditure_schemas
from .base_helpers import DistrictExpenditureHelper
from .base_router import create_district_expenditure_routers
from .unified_excel_export import export_unified_workbook_async, export_unified_workbook

__all__ = [
    'create_district_expenditure_model',
    'create_district_expenditure_schemas',
    'DistrictExpenditureHelper',
    'create_district_expenditure_routers',
    'export_unified_workbook_async',
    'export_unified_workbook',
]
