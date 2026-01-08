"""Scheme implementations package

Structure:
- src/schemes/s{code}/ - Main scheme folder
- src/schemes/s{code}/subs/ - Sub-scheme folder
- src/schemes/s{code}/subs/s{subcode}/ - Individual sub-scheme implementation
  - __init__.py - Exports config and routers
  - config.py - Scheme-specific configuration (designations, classes, etc.)
  - models.py - Model references with scheme filters
  - schemas.py - Pydantic schemas
  - router_api.py - REST API endpoints
  - router_ui.py - UI routes (or re-exports from legacy routers)
"""
from src.core.registry import scheme_registry

def init_schemes():
    """Initialize all schemes by auto-discovery"""
    scheme_registry.auto_discover_schemes("src/schemes")

# Direct imports for backward compatibility
from .s2053.subs.s20530028.config import SCHEME_CONFIG as S20530028_CONFIG

__all__ = ['init_schemes', 'scheme_registry', 'S20530028_CONFIG']

