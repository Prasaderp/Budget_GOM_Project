"""Sub-scheme 2245 - Natural Calamity Relief Section 1

Single sub-scheme with 23 table sections for district-wise expenditure.
"""
from .config import SCHEME_CONFIG
from .router_api import router as api_router
from .router_ui import router as ui_router

__all__ = [
    "SCHEME_CONFIG",
    "api_router",
    "ui_router",
]

