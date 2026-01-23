"""Unified Excel export for scheme 7610 - Government Employee Loans.

This module provides a single export service that:
- Uses one shared Excel template containing all 4 sub-scheme tables in a single sheet
- Fetches data from all 4 sub-scheme database tables (76100149, 76100158, 76100167, 76101871)
- Ensures fiscal year consistency across all data sources
- Syncs data when downloaded from any of the 4 sub-schema UIs
"""
from .template_export_service import export_7610_workbook_async

__all__ = ["export_7610_workbook_async"]
