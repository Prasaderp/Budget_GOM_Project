"""Unified Excel export for scheme 2235 - Social Security and Welfare.

This module provides a single export service that:
- Uses one shared Excel template containing all 4 sub-scheme sheets
- Fetches data from all 4 sub-scheme database tables (22353195, 22350338, 22350311, 22353408)
- Ensures fiscal year consistency across all data sources
- Syncs data when downloaded from any of the 4 sub-schema UIs
"""
from .template_export_service import export_2235_workbook_async

__all__ = ["export_2235_workbook_async"]
