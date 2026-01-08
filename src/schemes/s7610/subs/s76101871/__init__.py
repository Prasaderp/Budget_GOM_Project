"""Sub-scheme 76101871 - District Expenditure

Isolated implementation for district-wise expenditure table.
"""
from .config import SCHEME_CONFIG
from .router_api import router as api_router
from .router_ui import router as ui_router

__all__ = [
    "SCHEME_CONFIG",
    "api_router",
    "ui_router",
]



