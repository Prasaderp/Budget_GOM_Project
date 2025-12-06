"""Scheme 0029 - Land Revenue Receipts Section 1

Single scheme with multiple table sections for district-wise revenue.
"""
from .config import SCHEME_CONFIG
from .router_api import router as api_router
from .router_ui import router as ui_router

__all__ = [
    "SCHEME_CONFIG",
    "api_router",
    "ui_router",
]

