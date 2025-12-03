"""Scheme selection UI router"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.templates import templates
from src.config_schemes import (
    SCHEMES, SUB_SCHEMES, SCHEME_TYPES,
    get_schemes_by_type, get_sub_schemes_by_scheme_and_type, 
    is_sub_scheme_implemented, get_scheme_display_info
)
from src.utils_scheme import validate_scheme_selection
router = APIRouter(prefix="/ui/scheme-selection", tags=["UI - Scheme Selection"], include_in_schema=False)

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
    user = _get_user_context(request)
    if not user["username"]:
        return RedirectResponse(url="/", status_code=303)
    
    # Get currently selected values (if any)
    selected_type = request.cookies.get("selected_scheme_type", "")
    selected_scheme = request.cookies.get("selected_scheme", "")
    selected_sub = request.cookies.get("selected_sub_scheme", "")
    
    # Build data for template
    schemes_voted = get_schemes_by_type("voted")
    schemes_charged = get_schemes_by_type("charged")
    
    sub_schemes_data = {}
    if selected_type and selected_scheme:
        sub_schemes_data = get_sub_schemes_by_scheme_and_type(selected_scheme, selected_type)
    
    template_data = {
        "request": request,
        "user": user,
        "scheme_types": SCHEME_TYPES,
        "schemes_voted": schemes_voted,
        "schemes_charged": schemes_charged,
        "all_schemes": SCHEMES,
        "sub_schemes_data": sub_schemes_data,
        "selected_type": selected_type,
        "selected_scheme": selected_scheme,
        "selected_sub": selected_sub
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
    """HTMX endpoint to get sub-schemes for a given scheme and type"""
    if not scheme_type or not scheme_code:
        return HTMLResponse("")
    
    sub_schemes = get_sub_schemes_by_scheme_and_type(scheme_code, scheme_type)
    
    html_parts = []
    for code, info in sorted(sub_schemes.items()):
        implemented = is_sub_scheme_implemented(code)
        badge = '<span class="badge-active">सक्रिय</span>' if implemented else '<span class="badge-coming">लवकरच</span>'
        disabled_class = "" if implemented else " disabled"
        html_parts.append(
            f'<label class="sub-scheme-card{disabled_class}">'
            f'<input type="radio" name="sub_scheme_code" value="{code}" {"" if implemented else "disabled"}>'
            f'<span class="sub-code">{code}</span>'
            f'{badge}'
            f'</label>'
        )
    
    return HTMLResponse("".join(html_parts) if html_parts else '<p class="no-data">या योजनेसाठी उप-योजना उपलब्ध नाहीत</p>')

@router.post("", response_class=RedirectResponse)
async def post_scheme_selection(
    request: Request,
    scheme_type: str = Form(...),
    scheme_code: str = Form(...),
    sub_scheme_code: str = Form(...)
):
    user = _get_user_context(request)
    if not user["username"]:
        return RedirectResponse(url="/", status_code=303)
    
    # Validate selection
    if not validate_scheme_selection(scheme_code, sub_scheme_code, scheme_type):
        raise HTTPException(status_code=400, detail="Invalid scheme selection")
    
    # Check if implemented and get entry point
    implemented = is_sub_scheme_implemented(sub_scheme_code)
    if implemented:
        from src.core.registry import scheme_registry
        redirect_url = scheme_registry.get_entry_point(sub_scheme_code) or "/ui/budget-post-details?view=edit"
    else:
        redirect_url = "/ui/scheme-placeholder"
    
    response = RedirectResponse(url=redirect_url, status_code=303)
    
    # Set cookies (30 days expiry)
    cookie_params = {"httponly": False, "samesite": "lax", "max_age": 2592000}
    response.set_cookie("selected_scheme_type", scheme_type, **cookie_params)
    response.set_cookie("selected_scheme", scheme_code, **cookie_params)
    response.set_cookie("selected_sub_scheme", sub_scheme_code, **cookie_params)
    
    return response

@router.get("/clear", response_class=RedirectResponse)
async def clear_scheme_selection(request: Request):
    """Clear scheme selection and redirect to selection page"""
    response = RedirectResponse(url="/ui/scheme-selection", status_code=303)
    response.delete_cookie("selected_scheme_type")
    response.delete_cookie("selected_scheme")
    response.delete_cookie("selected_sub_scheme")
    return response


# Placeholder route is outside the prefix
from fastapi import APIRouter as PlaceholderRouter
placeholder_router = APIRouter(prefix="/ui", tags=["UI - Scheme Placeholder"], include_in_schema=False)

@placeholder_router.get("/scheme-placeholder", response_class=HTMLResponse)
async def scheme_placeholder_page(request: Request):
    """Show placeholder page for unimplemented schemes"""
    scheme_code = request.cookies.get("selected_scheme", "")
    sub_scheme_code = request.cookies.get("selected_sub_scheme", "")
    scheme_type = request.cookies.get("selected_scheme_type", "voted")
    
    scheme_name, _, type_mr = get_scheme_display_info(scheme_code, sub_scheme_code)
    
    return templates.TemplateResponse("scheme_placeholder.html", {
        "request": request,
        "scheme_code": scheme_code,
        "sub_scheme_code": sub_scheme_code,
        "scheme_name": scheme_name,
        "scheme_type_mr": type_mr
    })

