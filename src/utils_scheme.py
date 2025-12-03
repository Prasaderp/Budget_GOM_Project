"""Scheme-related utilities for session management and validation"""
import re
from fastapi import Request
from typing import Tuple, Optional
from pathlib import Path
from src.config_schemes import SUB_SCHEMES, SCHEMES, is_sub_scheme_implemented
from src.core.registry import scheme_registry

def _get_default_implemented_scheme() -> Tuple[str, str]:
    """Get first implemented scheme as default"""
    implemented = scheme_registry.get_implemented_schemes()
    if implemented:
        first_scheme = next(iter(implemented.values()))
        return first_scheme.parent_scheme, first_scheme.code
    return '2053', '20530028'

def get_scheme_from_cookies(request: Request) -> Tuple[str, str]:
    """Get selected scheme and sub_scheme from cookies, with defaults"""
    default_scheme, default_sub_scheme = _get_default_implemented_scheme()
    scheme = request.cookies.get("selected_scheme", default_scheme)
    sub_scheme = request.cookies.get("selected_sub_scheme", default_sub_scheme)
    return scheme, sub_scheme

def get_scheme_type_from_cookies(request: Request) -> str:
    """Get selected scheme type (charged/voted) from cookies"""
    return request.cookies.get("selected_scheme_type", "voted")

def validate_scheme_selection(scheme_code: str, sub_scheme_code: str, scheme_type: str) -> bool:
    """Validate that the scheme selection is valid"""
    if scheme_code not in SCHEMES:
        return False
    sub = SUB_SCHEMES.get(sub_scheme_code)
    if not sub:
        return False
    return sub.get("scheme") == scheme_code and sub.get("type") == scheme_type

def has_scheme_selected(request: Request) -> bool:
    """Check if user has selected a scheme"""
    return bool(request.cookies.get("selected_sub_scheme"))

def is_current_scheme_implemented(request: Request) -> bool:
    """Check if currently selected scheme is implemented"""
    _, sub_scheme = get_scheme_from_cookies(request)
    return is_sub_scheme_implemented(sub_scheme)

def _extract_scheme_from_url(path: str) -> Optional[str]:
    """
    Extract scheme code from URL path using multiple strategies.
    Priority:
    1. Direct scheme code in URL (e.g., /ui/s62450017/...)
    2. Registered route prefixes (e.g., /ui/budget-post-details -> 20530028)
    3. Returns None if no scheme found
    """
    if not path:
        return None
    
    # Strategy 1: Extract scheme code directly from URL patterns
    patterns = [
        r'/ui/s(\d{8})(?:/|$)',  # /ui/s62450017/... or /ui/s62450017
        r'/api/schemes/(\d{8})(?:/|$)',  # /api/schemes/62450017/... or /api/schemes/62450017
        r'/ui/schemes/(\d{8})(?:/|$)',  # /ui/schemes/62450017/... or /ui/schemes/62450017
        r'/api/s(\d{8})(?:/|$)',  # /api/s20530028/... or /api/s20530028
    ]
    
    for pattern in patterns:
        match = re.search(pattern, path)
        if match:
            scheme_code = match.group(1)
            if scheme_registry.get_scheme(scheme_code):
                return scheme_code
    
    # Strategy 2: Check registered route prefixes
    scheme_code = scheme_registry.get_scheme_from_route(path)
    if scheme_code:
        return scheme_code
    
    return None

def _get_base_template_path(sub_scheme_code: str) -> Optional[str]:
    """Get base template path for a scheme code. Returns path if exists, None otherwise."""
    if not sub_scheme_code:
        return None
    
    scheme_config = scheme_registry.get_scheme(sub_scheme_code)
    if not scheme_config:
        return None
    
    parent = scheme_config.parent_scheme
    base_template_path = f"schemes/s{parent}/subs/s{sub_scheme_code}/base.html"
    template_file = Path("templates") / base_template_path
    
    return base_template_path if template_file.exists() else None

def get_scheme_base_template(request: Request) -> str:
    """
    Get scheme base template path with proper validation.
    Priority:
    1. Extract scheme from URL path (most reliable)
    2. Fallback to cookies (for root routes)
    3. Default to base.html if no valid scheme found
    
    Returns: Template path string
    """
    url_path = str(request.url.path)
    
    scheme_code = _extract_scheme_from_url(url_path)
    
    if not scheme_code:
        scheme_code = request.cookies.get("selected_sub_scheme", "")
        if not scheme_code:
            return "base.html"
    
    base_template_path = _get_base_template_path(scheme_code)
    return base_template_path if base_template_path else "base.html"


def get_current_scheme_code(request: Request) -> Optional[str]:
    """
    Get current scheme code from URL or cookies.
    Priority: URL path > Cookies > None
    """
    url_path = str(request.url.path)
    scheme_code = _extract_scheme_from_url(url_path)
    if not scheme_code:
        scheme_code = request.cookies.get("selected_sub_scheme", "")
    return scheme_code if scheme_code else None


def get_scheme_url(request: Request, path: str) -> str:
    """
    Generate scheme-aware URL for shared routes.
    Detects if path already contains scheme code and avoids duplication.
    
    Args:
        request: FastAPI Request object
        path: Route path (e.g., '/ui/shashan-niryan', '/ui/taluka-selection', or '/ui/s62450017/district-expenditure')
    
    Returns:
        Scheme-aware URL (e.g., '/ui/s62450017/shashan-niryan')
    """
    if not path:
        return path
    
    # Check if path already contains a scheme code pattern (simple regex, no registry validation)
    scheme_pattern = r'/ui/s(\d{8})(?:/|$)'
    if re.search(scheme_pattern, path):
        # Path already has scheme code, return as-is
        return path
    
    # Get current scheme code from request
    scheme_code = get_current_scheme_code(request)
    if not scheme_code:
        return path
    
    # Build scheme-aware URL
    if path.startswith('/ui/'):
        return f"/ui/s{scheme_code}{path[3:]}"
    elif path.startswith('/timing/'):
        return f"/ui/s{scheme_code}/timing-management{path[7:]}"
    elif path.startswith('/'):
        return f"/ui/s{scheme_code}{path}"
    else:
        return f"/ui/s{scheme_code}/{path}"