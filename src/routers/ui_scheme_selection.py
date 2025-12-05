"""Scheme selection UI router - Clean and optimized"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import re

from src.database import get_db
from src.core.templates import templates
from src.config_schemes import (
    SCHEMES, SCHEME_TYPES,
    get_schemes_by_type, get_sub_schemes_by_scheme_and_type, 
    is_sub_scheme_implemented, get_scheme_display_info
)
from src.utils_scheme import validate_scheme_selection

router = APIRouter(prefix="/ui/scheme-selection", tags=["UI - Scheme Selection"], include_in_schema=False)

# Input validation pattern - alphanumeric and hyphen only
SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9\-]+$')

def _sanitize(value: str, max_len: int = 20) -> str:
    """Sanitize input - alphanumeric and hyphen only, max length"""
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()[:max_len]
    return value if SAFE_PATTERN.match(value) else ""

def _get_user_context(request: Request) -> dict:
    """Extract user context from cookies"""
    return {
        "username": request.cookies.get("auth_user", ""),
        "level": request.cookies.get("auth_level", ""),
        "role": request.cookies.get("auth_role", ""),
        "unit": request.cookies.get("auth_unit", "")
    }

@router.get("", response_class=HTMLResponse)
async def ui_scheme_selection(request: Request, db: Session = Depends(get_db)):
    """Render scheme selection page - always starts fresh"""
    user = _get_user_context(request)
    if not user["username"]:
        return RedirectResponse(url="/", status_code=303)
    
    # Get schemes by type for filtering
    schemes_voted = get_schemes_by_type("voted")
    schemes_charged = get_schemes_by_type("charged")
    
    template_data = {
        "request": request,
        "user": user,
        "scheme_types": SCHEME_TYPES,
        "schemes_voted": schemes_voted,
        "schemes_charged": schemes_charged,
        "all_schemes": SCHEMES,
    }
    
    response = templates.TemplateResponse("scheme_selection.html", template_data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@router.get("/sub-schemes", response_class=HTMLResponse)
async def get_sub_schemes_partial(
    request: Request, 
    scheme_type: str = "", 
    scheme_code: str = ""
):
    """AJAX endpoint - returns sub-schemes HTML for given scheme and type"""
    # Sanitize inputs
    scheme_type = _sanitize(scheme_type, 10)
    scheme_code = _sanitize(scheme_code, 20)
    
    if not scheme_type or not scheme_code:
        return HTMLResponse("")
    
    # Validate type
    if scheme_type not in ("voted", "charged"):
        return HTMLResponse("")
    
    # Validate scheme exists
    if scheme_code not in SCHEMES:
        return HTMLResponse("")
    
    sub_schemes = get_sub_schemes_by_scheme_and_type(scheme_code, scheme_type)
    
    if not sub_schemes:
        return HTMLResponse('<p class="no-data">या योजनेसाठी उप-योजना उपलब्ध नाहीत</p>')
    
    # Build HTML
    html_parts = []
    for code in sorted(sub_schemes.keys()):
        info = sub_schemes[code]
        implemented = is_sub_scheme_implemented(code)
        
        if implemented:
            html_parts.append(
                f'<label class="sub-scheme-card">'
                f'<input type="radio" name="sub_scheme_code" value="{code}">'
                f'<span class="sub-code">{code}</span>'
                f'<span class="badge-active">सक्रिय</span>'
                f'</label>'
            )
        else:
            html_parts.append(
                f'<label class="sub-scheme-card disabled">'
                f'<input type="radio" name="sub_scheme_code" value="{code}" disabled>'
                f'<span class="sub-code">{code}</span>'
                f'<span class="badge-coming">लवकरच</span>'
                f'</label>'
            )
    
    return HTMLResponse("".join(html_parts))

@router.post("", response_class=RedirectResponse)
async def post_scheme_selection(
    request: Request,
    scheme_type: str = Form(...),
    scheme_code: str = Form(...),
    sub_scheme_code: str = Form(...)
):
    """Handle form submission - validate and set cookies"""
    user = _get_user_context(request)
    if not user["username"]:
        return RedirectResponse(url="/", status_code=303)
    
    # Sanitize all inputs
    scheme_type = _sanitize(scheme_type, 10)
    scheme_code = _sanitize(scheme_code, 20)
    sub_scheme_code = _sanitize(sub_scheme_code, 20)
    
    # Validate type
    if scheme_type not in ("voted", "charged"):
        raise HTTPException(status_code=400, detail="Invalid scheme type")
    
    # Validate scheme selection
    if not validate_scheme_selection(scheme_code, sub_scheme_code, scheme_type):
        raise HTTPException(status_code=400, detail="Invalid scheme selection")
    
    # Check implementation and get redirect URL
    if is_sub_scheme_implemented(sub_scheme_code):
        from src.core.registry import scheme_registry
        redirect_url = scheme_registry.get_entry_point(sub_scheme_code) or "/ui/budget-post-details?view=edit"
    else:
        redirect_url = "/ui/scheme-placeholder"
    
    response = RedirectResponse(url=redirect_url, status_code=303)
    
    # Set cookies with security settings
    cookie_opts = {
        "httponly": False,  # Allow JS access for display purposes
        "samesite": "lax",
        "max_age": 2592000,  # 30 days
        "secure": False  # Set True in production with HTTPS
    }
    response.set_cookie("selected_scheme_type", scheme_type, **cookie_opts)
    response.set_cookie("selected_scheme", scheme_code, **cookie_opts)
    response.set_cookie("selected_sub_scheme", sub_scheme_code, **cookie_opts)
    
    return response

@router.get("/clear", response_class=RedirectResponse)
async def clear_scheme_selection(request: Request):
    """Clear scheme selection cookies and redirect"""
    response = RedirectResponse(url="/ui/scheme-selection", status_code=303)
    for cookie in ("selected_scheme_type", "selected_scheme", "selected_sub_scheme"):
        response.delete_cookie(cookie)
    return response


# Placeholder router (separate prefix)
placeholder_router = APIRouter(prefix="/ui", tags=["UI - Scheme Placeholder"], include_in_schema=False)

@placeholder_router.get("/scheme-placeholder", response_class=HTMLResponse)
async def scheme_placeholder_page(request: Request):
    """Show placeholder for unimplemented schemes"""
    scheme_code = _sanitize(request.cookies.get("selected_scheme", ""), 20)
    sub_scheme_code = _sanitize(request.cookies.get("selected_sub_scheme", ""), 20)
    
    scheme_name, _, type_mr = get_scheme_display_info(scheme_code, sub_scheme_code)
    
    return templates.TemplateResponse("scheme_placeholder.html", {
        "request": request,
        "scheme_code": scheme_code,
        "sub_scheme_code": sub_scheme_code,
        "scheme_name": scheme_name,
        "scheme_type_mr": type_mr
    })
