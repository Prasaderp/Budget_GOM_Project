"""Excel export module for sub-scheme 20530019.

This module provides production-grade Excel export functionality with:
- Template-based workbook generation
- District-specific data filtering
- Throttled concurrent exports (via ExcelExportService)
- Async audit logging
"""

from .template_export_service import (
    export_original_workbook,
    export_original_workbook_async
)

__all__ = [
    'export_original_workbook',
    'export_original_workbook_async'
]
