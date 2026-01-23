"""Scheme 2075 - Miscellaneous General Services (विविध सामान्य सेवा).

This module provides:
- API routes for sub-head and district expenditure management
- UI routes for data entry and viewing
- Excel export functionality for both sub-schemes (20750249, 20750294)
"""
from .config import SCHEME_CONFIG, SCHEME_CODE
from .router_api import router as api_router
from .router_ui import router as ui_router
from .excel_export import export_2075_workbook_async

SCHEME_INFO = {
    "code": SCHEME_CONFIG.code,
    "name_en": SCHEME_CONFIG.name_en,
    "name_mr": SCHEME_CONFIG.name_mr,
    "entry_point": SCHEME_CONFIG.entry_point,
    "implemented": SCHEME_CONFIG.implemented,
}

__all__ = [
    "SCHEME_INFO",
    "SCHEME_CONFIG",
    "SCHEME_CODE",
    "api_router",
    "ui_router",
    "export_2075_workbook_async",
]
