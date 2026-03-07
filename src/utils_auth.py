import re
from urllib.parse import unquote
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional, Dict
from functools import wraps

_ALPHA_NUM = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
_FY_PATTERN = re.compile(r'^\d{4}-\d{2}$')

_VALID_LEVELS = frozenset({'district', 'dco', 'taluka'})
_VALID_ROLES = frozenset({'assistant', 'officer1', 'officer2', 'dco', 'admin'})
_VALID_SCHEME_TYPES = frozenset({'voted', 'charged'})


def _sanitize(value: str, pattern: re.Pattern, max_len: int = 50) -> str:
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()[:max_len]
    return value if pattern.match(value) else ""


def _validate_whitelist(value: str, allowed: frozenset, default: str = "") -> str:
    return value if value in allowed else default


def get_auth_user(request: Request) -> str:
    return _sanitize(request.cookies.get("auth_user", ""), _ALPHA_NUM, 50)


def get_display_user(request: Request) -> str:
    return _sanitize(request.cookies.get("auth_user_display", ""), _ALPHA_NUM, 50)


def get_auth_level(request: Request) -> str:
    raw = request.cookies.get("auth_level", "")
    return _validate_whitelist(raw.lower(), _VALID_LEVELS, "")


def get_auth_role(request: Request) -> str:
    raw = request.cookies.get("auth_role", "")
    return _validate_whitelist(raw.lower(), _VALID_ROLES, "")


def get_auth_unit(request: Request) -> str:
    raw = request.cookies.get("auth_unit", "")
    if not raw:
        return ""
    try:
        decoded = unquote(raw)
    except Exception:
        decoded = raw
    return decoded.strip()[:100]


def get_admin_user(request: Request) -> str:
    return _sanitize(request.cookies.get("admin_user", ""), _ALPHA_NUM, 50)


def get_user_context(request: Request) -> Dict[str, str]:
    return {
        "username": get_auth_user(request),
        "level": get_auth_level(request),
        "role": get_auth_role(request),
        "unit": get_auth_unit(request)
    }


def is_authenticated(request: Request) -> bool:
    return bool(get_auth_user(request))


async def verify_api_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")


def is_admin(request: Request) -> bool:
    return bool(get_admin_user(request))


def get_scheme_type(request: Request) -> str:
    raw = request.cookies.get("selected_scheme_type", "voted")
    return _validate_whitelist(raw, _VALID_SCHEME_TYPES, "voted")


def get_scheme_code(request: Request) -> str:
    return _sanitize(request.cookies.get("selected_scheme", ""), _ALPHA_NUM, 10)


def get_sub_scheme_code(request: Request) -> str:
    raw = request.cookies.get("selected_sub_scheme", "")
    return _sanitize(raw, re.compile(r'^[a-zA-Z0-9\-]+$'), 20)


def get_fiscal_year(request: Request) -> str:
    raw = request.cookies.get("fiscal_year", "")
    return raw if _FY_PATTERN.match(raw) else ""


def require_auth(redirect_url: str = "/"):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not is_authenticated(request):
                return RedirectResponse(url=redirect_url, status_code=303)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin(redirect_url: str = "/admin/login"):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not is_admin(request):
                return RedirectResponse(url=redirect_url, status_code=303)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*allowed_roles: str):
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
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            level = get_auth_level(request)
            if level not in allowed_levels:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
