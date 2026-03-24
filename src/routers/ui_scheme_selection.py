"""Scheme selection UI router - Clean and optimized"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.templates import render
from src.config_schemes import (
    SCHEMES, SCHEME_TYPES,
    get_schemes_by_type, get_sub_schemes_by_scheme_and_type, 
    is_sub_scheme_implemented, get_scheme_display_info
)
from src.utils_scheme import validate_scheme_selection
from src.utils_auth import get_user_context, is_authenticated, get_scheme_code, get_sub_scheme_code

router = APIRouter(prefix="/ui/scheme-selection", tags=["UI - Scheme Selection"], include_in_schema=False)


def _sanitize_scheme_input(value: str, max_len: int = 20) -> str:
    """Sanitize scheme-related input - alphanumeric and hyphen only"""
    if not value or not isinstance(value, str):
        return ""
    import re
    value = value.strip()[:max_len]
    return value if re.match(r'^[a-zA-Z0-9\-]+$', value) else ""


@router.get("", response_class=HTMLResponse)
async def ui_scheme_selection(request: Request, db: Session = Depends(get_db)):
    """Render scheme selection page - always starts fresh"""
    if not is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    
    user = get_user_context(request)
    
    response = render(request, "scheme_selection.html", {
        "user": user,
        "scheme_types": SCHEME_TYPES,
        "schemes_voted": get_schemes_by_type("voted"),
        "schemes_charged": get_schemes_by_type("charged"),
        "all_schemes": SCHEMES,
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@router.get("/sub-schemes", response_class=HTMLResponse)
async def get_sub_schemes_partial(request: Request, scheme_type: str = "", scheme_code: str = ""):
    """AJAX endpoint - returns sub-schemes HTML for given scheme and type"""
    scheme_type = _sanitize_scheme_input(scheme_type, 10)
    scheme_code = _sanitize_scheme_input(scheme_code, 20)
    
    if not scheme_type or not scheme_code:
        return HTMLResponse("")
    
    if scheme_type not in ("voted", "charged") or scheme_code not in SCHEMES:
        return HTMLResponse("")
    
    sub_schemes = get_sub_schemes_by_scheme_and_type(scheme_code, scheme_type)
    
    if not sub_schemes:
        # Special handling for unified schemes without sub-schemes (2245, 0029, 2075)
        if scheme_code in ("2245", "0029", "2075"):
            impl = is_sub_scheme_implemented(scheme_code)
            cls = "" if impl else " disabled"
            disabled = "" if impl else " disabled"
            badge = '<span class="badge-active">सक्रिय</span>' if impl else '<span class="badge-coming">लवकरच</span>'
            return HTMLResponse(f'<label class="sub-scheme-card{cls}"><input type="radio" name="sub_scheme_code" value="{scheme_code}"{disabled}><span class="sub-code">{scheme_code}</span>{badge}</label>')
        return HTMLResponse('<p class="no-data">या योजनेसाठी उप-योजना उपलब्ध नाहीत</p>')
    
    # Build HTML
    html = []
    for code in sorted(sub_schemes.keys()):
        impl = is_sub_scheme_implemented(code)
        cls = "" if impl else " disabled"
        disabled = "" if impl else " disabled"
        badge = '<span class="badge-active">सक्रिय</span>' if impl else '<span class="badge-coming">लवकरच</span>'
        html.append(f'<label class="sub-scheme-card{cls}"><input type="radio" name="sub_scheme_code" value="{code}"{disabled}><span class="sub-code">{code}</span>{badge}</label>')
    
    return HTMLResponse("".join(html))


@router.post("", response_class=RedirectResponse)
async def post_scheme_selection(
    request: Request,
    scheme_type: str = Form(...),
    scheme_code: str = Form(...),
    sub_scheme_code: str = Form(...)
):
    """Handle form submission - validate and set cookies"""
    if not is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    
    # Sanitize inputs
    scheme_type = _sanitize_scheme_input(scheme_type, 10)
    scheme_code = _sanitize_scheme_input(scheme_code, 20)
    sub_scheme_code = _sanitize_scheme_input(sub_scheme_code, 20)
    
    # Validate
    if scheme_type not in ("voted", "charged"):
        raise HTTPException(status_code=400, detail="Invalid scheme type")
    
    if not validate_scheme_selection(scheme_code, sub_scheme_code, scheme_type):
        raise HTTPException(status_code=400, detail="Invalid scheme selection")
    
    # Get redirect URL
    if is_sub_scheme_implemented(sub_scheme_code):
        from src.core.registry import scheme_registry
        redirect_url = scheme_registry.get_entry_point(sub_scheme_code) or "/ui/budget-post-details?view=edit"
    else:
        redirect_url = "/ui/scheme-placeholder"
    
    response = RedirectResponse(url=redirect_url, status_code=303)
    
    # Set cookies
    opts = {"httponly": False, "samesite": "lax", "max_age": 2592000}
    response.set_cookie("selected_scheme_type", scheme_type, **opts)
    response.set_cookie("selected_scheme", scheme_code, **opts)
    response.set_cookie("selected_sub_scheme", sub_scheme_code, **opts)
    
    return response


@router.get("/clear", response_class=RedirectResponse)
async def clear_scheme_selection(request: Request):
    """Clear scheme selection cookies and redirect"""
    response = RedirectResponse(url="/ui/scheme-selection", status_code=303)
    for c in ("selected_scheme_type", "selected_scheme", "selected_sub_scheme"):
        response.delete_cookie(c)
    return response


# Placeholder router
placeholder_router = APIRouter(prefix="/ui", tags=["UI - Scheme Placeholder"], include_in_schema=False)

@placeholder_router.get("/scheme-placeholder", response_class=HTMLResponse)
async def scheme_placeholder_page(request: Request):
    """Show placeholder for unimplemented schemes"""
    scheme = get_scheme_code(request)
    sub_scheme = get_sub_scheme_code(request)
    scheme_name, _, type_mr = get_scheme_display_info(scheme, sub_scheme)
    
    return render(request, "scheme_placeholder.html", {
        "scheme_code": scheme,
        "sub_scheme_code": sub_scheme,
        "scheme_name": scheme_name,
        "scheme_type_mr": type_mr
    })
