"""Centralized authentication utilities - Secure cookie reading and validation

This module provides a single source of truth for extracting and validating
user authentication from cookies. All routers should use these functions
instead of directly reading cookies.
"""
import re
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional, Dict
from functools import wraps

# Validation patterns
_ALPHA_NUM = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
_FY_PATTERN = re.compile(r'^\d{4}-\d{2}$')

# Allowed values (whitelist)
_VALID_LEVELS = frozenset({'district', 'dco', 'taluka'})
_VALID_ROLES = frozenset({'assistant', 'officer1', 'officer2', 'dco', 'admin'})
_VALID_SCHEME_TYPES = frozenset({'voted', 'charged'})


def _sanitize(value: str, pattern: re.Pattern, max_len: int = 50) -> str:
    """Sanitize a cookie value against a pattern"""
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()[:max_len]
    return value if pattern.match(value) else ""


def _validate_whitelist(value: str, allowed: frozenset, default: str = "") -> str:
    """Validate value against a whitelist"""
    return value if value in allowed else default


def get_auth_user(request: Request) -> str:
    """Get authenticated username from httponly cookie (secure)"""
    return _sanitize(request.cookies.get("auth_user", ""), _ALPHA_NUM, 50)


def get_display_user(request: Request) -> str:
    """Get display username (may be same as auth_user)"""
    return _sanitize(request.cookies.get("auth_user_display", ""), _ALPHA_NUM, 50)


def get_auth_level(request: Request) -> str:
    """Get user level with validation"""
    raw = request.cookies.get("auth_level", "")
    return _validate_whitelist(raw.lower(), _VALID_LEVELS, "")


def get_auth_role(request: Request) -> str:
    """Get user role with validation"""
    raw = request.cookies.get("auth_role", "")
    return _validate_whitelist(raw.lower(), _VALID_ROLES, "")


def get_auth_unit(request: Request) -> str:
    """Get user unit with sanitization"""
    raw = request.cookies.get("auth_unit", "")
    if not raw:
        return ""
    # Units can have spaces (e.g., "Mumbai City"), so allow alphanumeric + space
    clean = re.sub(r'[^\w\s\-]', '', raw)[:100]
    return clean.strip()


def get_admin_user(request: Request) -> str:
    """Get admin username from httponly cookie"""
    return _sanitize(request.cookies.get("admin_user", ""), _ALPHA_NUM, 50)


def get_user_context(request: Request) -> Dict[str, str]:
    """Get complete user context - replaces _get_user_context patterns"""
    return {
        "username": get_auth_user(request),
        "level": get_auth_level(request),
        "role": get_auth_role(request),
        "unit": get_auth_unit(request)
    }


def is_authenticated(request: Request) -> bool:
    """Check if user has valid auth cookie"""
    return bool(get_auth_user(request))


def is_admin(request: Request) -> bool:
    """Check if user is authenticated admin"""
    return bool(get_admin_user(request))


def get_scheme_type(request: Request) -> str:
    """Get selected scheme type with validation"""
    raw = request.cookies.get("selected_scheme_type", "voted")
    return _validate_whitelist(raw, _VALID_SCHEME_TYPES, "voted")


def get_scheme_code(request: Request) -> str:
    """Get selected scheme code with sanitization"""
    return _sanitize(request.cookies.get("selected_scheme", ""), _ALPHA_NUM, 10)


def get_sub_scheme_code(request: Request) -> str:
    """Get selected sub-scheme code with sanitization"""
    # Sub-scheme codes can have hyphens (e.g., "22451761-31")
    raw = request.cookies.get("selected_sub_scheme", "")
    return _sanitize(raw, re.compile(r'^[a-zA-Z0-9\-]+$'), 20)


def get_fiscal_year(request: Request) -> str:
    """Get fiscal year with format validation"""
    raw = request.cookies.get("fiscal_year", "")
    return raw if _FY_PATTERN.match(raw) else ""


def require_auth(redirect_url: str = "/"):
    """Decorator to require authentication on route handlers"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not is_authenticated(request):
                return RedirectResponse(url=redirect_url, status_code=303)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin(redirect_url: str = "/admin/login"):
    """Decorator to require admin authentication"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not is_admin(request):
                return RedirectResponse(url=redirect_url, status_code=303)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*allowed_roles: str):
    """Decorator to require specific role(s)"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            role = get_auth_role(request)
            if role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_level(*allowed_levels: str):
    """Decorator to require specific level(s)"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            level = get_auth_level(request)
            if level not in allowed_levels:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
