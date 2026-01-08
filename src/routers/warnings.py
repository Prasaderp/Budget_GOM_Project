from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.templates import templates
from src.utils_timing import get_timing_warning_message
from src.utils_scheme import get_scheme_base_template

router = APIRouter(prefix="/ui/s{scheme_code}/warnings", tags=["Warnings"], include_in_schema=False)


@router.get("", response_class=HTMLResponse)
async def warnings_page(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    auth_level = request.cookies.get('auth_level', '')
    auth_role = request.cookies.get('auth_role', '')
    
    warnings = []
    
    if auth_level in ['district', 'taluka'] and auth_role == 'assistant':
        timing_msg = get_timing_warning_message(db, auth_level, scheme_code)
        if timing_msg:
            warnings.append({
                "type": "timing",
                "message": timing_msg,
                "severity": "high" if "ended" in timing_msg or "disabled" in timing_msg else "medium"
            })
    
    return templates.TemplateResponse("warnings.html", {
        "request": request,
        "warnings": warnings,
        "auth_level": auth_level,
        "base_template": get_scheme_base_template(request),
        "scheme_code": scheme_code
    })


@router.get("/api/banner", response_class=JSONResponse)
async def get_banner_warnings(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    auth_level = request.cookies.get('auth_level', '')
    auth_role = request.cookies.get('auth_role', '')
    
    if auth_level not in ['district', 'taluka'] or auth_role != 'assistant':
        return JSONResponse({"message": None})
    
    timing_msg = get_timing_warning_message(db, auth_level, scheme_code)
    
    return JSONResponse({
        "message": timing_msg,
        "severity": "high" if timing_msg and ("ended" in timing_msg or "disabled" in timing_msg) else "medium" if timing_msg else None
    })

