"""Scheme-related utilities for session management and validation"""
from fastapi import Request
from typing import Tuple, Optional
from src.config_schemes import SUB_SCHEMES, SCHEMES, is_sub_scheme_implemented

DEFAULT_SCHEME = '2053'
DEFAULT_SUB_SCHEME = '20530028'

def get_scheme_from_cookies(request: Request) -> Tuple[str, str]:
    """Get selected scheme and sub_scheme from cookies, with defaults"""
    scheme = request.cookies.get("selected_scheme", DEFAULT_SCHEME)
    sub_scheme = request.cookies.get("selected_sub_scheme", DEFAULT_SUB_SCHEME)
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

