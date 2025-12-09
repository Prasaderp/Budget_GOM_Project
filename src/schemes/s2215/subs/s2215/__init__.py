"""Sub-scheme 2215 - Water Scarcity

Single sub-scheme with account heads (e.g., 2215A195, 2215A201) for district-wise expenditure.
"""
from .config import SCHEME_CONFIG
from .router_api import router as api_router
from .router_ui import router as ui_router

__all__ = [
    "SCHEME_CONFIG",
    "api_router",
    "ui_router",
]

