"""Unified Excel export for combined 2245-2215 schemes.

This module provides a single export service that:
- Uses one shared Excel template containing sheets for both schemes
- Fetches data from both s2245 and s2215 database tables
- Ensures fiscal year consistency across both data sources
"""
from .excel_export import export_combined_workbook_async

__all__ = ["export_combined_workbook_async"]
