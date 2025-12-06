"""Sub-scheme 20750294 - Sub-Head Expenditure

Isolated implementation for sub-head expenditure table (DCO only, no districts).
"""
from .config import SCHEME_CONFIG
from .router_api import router as api_router
from .router_ui import router as ui_router

__all__ = [
    "SCHEME_CONFIG",
    "api_router",
    "ui_router",
]

