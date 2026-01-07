from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Dict
import logging

from src import models
from src.utils_scheme import get_scheme_base_template
from src.database import get_db
from src.core.templates import templates
from src.config import DISTRICTS, DISTRICTS_MR
from src.utils_taluka import get_possible_talukas_for_district, get_selected_talukas
from src.utils_taluka_user_management import sync_taluka_selection_with_management, get_taluka_users_for_district, update_taluka_user_credentials
from src.utils_fiscal_year import get_fiscal_year_from_request, DEFAULT_FISCAL_YEAR
from src.utils_cache import memory_cache
from src.core.registry import scheme_registry
from src.utils_auth import get_auth_unit, get_auth_user, get_auth_role, get_auth_level

logger = logging.getLogger(__name__)

def build_error_template_data(request: Request, unit: str, level: str, selected: set, error: str, db: Session) -> dict:
    all_talukas = get_possible_talukas_for_district(unit)
    taluka_user_details = get_taluka_users_for_district(db, unit)
    sorted_taluka_details = dict(sorted(taluka_user_details.items())) if taluka_user_details else {}
    
    return {
        "request": request, "resource_name": "तालुका निवड",
        "district": unit, "talukas": all_talukas, "selected": selected,
        "error": error, "auth_level": level, "taluka_user_details": sorted_taluka_details,
        "taluka_status": {}, "district_status": {}, "district_names": {},
        "base_template": get_scheme_base_template(request)
    }

router = APIRouter(prefix="/ui/s{scheme_code}/taluka-selection", tags=["UI - तालुका निवड"], include_in_schema=False)

def _resolve_parent_scheme_code(scheme_code: str) -> str:
    if scheme_code.startswith('s'):
        scheme_code = scheme_code[1:]
    if len(scheme_code) >= 4:
        return scheme_code[:4]
    return scheme_code

def get_district_completion_status(db: Session, scheme_code: str, fiscal_year: str) -> Dict[str, str]:
    parent_code = _resolve_parent_scheme_code(scheme_code)
    cache_key = f"district_status_{parent_code}_{fiscal_year}"
    cached = memory_cache.get(cache_key)
    if cached:
        return cached
    
    parent_schemes = scheme_registry.get_schemes_by_parent(parent_code)
    
    if not parent_schemes:
        result = {d: 'pending' for d in DISTRICTS}
        memory_cache.set(cache_key, result, 180)
        return result
    
    sub_scheme_codes = [code for code, config in parent_schemes.items() if config.implemented]
    
    if not sub_scheme_codes:
        result = {d: 'pending' for d in DISTRICTS}
        memory_cache.set(cache_key, result, 180)
        return result
    
    completion_data = db.query(
        models.SubSchemaCompletion.district,
        func.count(models.SubSchemaCompletion.id).label('completed_count')
    ).filter(
        and_(
            models.SubSchemaCompletion.sub_scheme_code.in_(sub_scheme_codes),
            models.SubSchemaCompletion.fiscal_year == fiscal_year,
            models.SubSchemaCompletion.is_complete == True
        )
    ).group_by(models.SubSchemaCompletion.district).all()
    
    total_subschemes = len(sub_scheme_codes)
    completion_map = {row.district: row.completed_count for row in completion_data}
    
    result = {}
    for district in DISTRICTS:
        completed = completion_map.get(district, 0)
        result[district] = 'processed' if completed == total_subschemes else 'pending'
    
    memory_cache.set(cache_key, result, 180)
    return result

@router.get("", response_class=HTMLResponse)
async def ui_get_taluka_selection(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    from src.config import DCO_STAFF_IDENTIFIER
    role = get_auth_role(request)
    level = get_auth_level(request)
    unit = get_auth_unit(request)
    username = get_auth_user(request)
    
    if not ((role == 'assistant' and level == 'district') or (role == 'assistant' and level == 'dco')):
        raise HTTPException(status_code=403, detail="Access denied: Assistant role required")
    
    if level == 'dco' and role == 'assistant' and username != 'dco_asst':
        raise HTTPException(status_code=403, detail="DCO level assistant access restricted")
    
    if level == 'district' and unit == DCO_STAFF_IDENTIFIER:
        raise HTTPException(status_code=403, detail="DCO Staff cannot have talukas")
    
    try:
        fiscal_year = get_fiscal_year_from_request(request, db)
    except Exception as e:
        logger.error(f"Failed to get fiscal year: {e}", exc_info=True)
        fiscal_year = DEFAULT_FISCAL_YEAR
    
    if level == 'district' and unit:
        row = db.query(models.DistrictTalukaSelection).filter(models.DistrictTalukaSelection.district == unit).first()
        selected = row.selected_talukas if row else get_selected_talukas(db, unit)
        all_talukas = get_possible_talukas_for_district(unit)
        taluka_user_details = get_taluka_users_for_district(db, unit)
        
        sorted_taluka_details = dict(sorted(taluka_user_details.items())) if taluka_user_details else {}
        
        template_data = {
            "request": request, "resource_name": "तालुका निवड",
            "district": unit, "talukas": all_talukas, "selected": set(selected),
            "auth_level": level, "taluka_user_details": sorted_taluka_details,
            "taluka_status": {}, "district_status": {}, "district_names": {},
            "base_template": get_scheme_base_template(request), "scheme_code": scheme_code,
            "fiscal_year": fiscal_year, "districts": DISTRICTS
        }
        
    elif level == 'dco':
        try:
            district_status = get_district_completion_status(db, scheme_code, fiscal_year)
        except Exception as e:
            logger.error(f"Failed to get district status: {e}", exc_info=True)
            district_status = {d: 'pending' for d in DISTRICTS}
        
        template_data = {
            "request": request, "resource_name": "अंदाजपत्रक सद्यस्थिती",
            "district": unit, "talukas": [], "selected": set(), "auth_level": level,
            "taluka_user_details": {}, "taluka_status": {},
            "district_status": district_status, "district_names": DISTRICTS_MR,
            "base_template": get_scheme_base_template(request), "scheme_code": scheme_code,
            "fiscal_year": fiscal_year, "districts": DISTRICTS
        }
    
    response = templates.TemplateResponse("taluka_selection.html", template_data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.post("", response_class=RedirectResponse)
async def ui_post_taluka_selection(request: Request, scheme_code: str, db: Session = Depends(get_db), talukas: Optional[List[str]] = Form(None)):
    from src.config import DCO_STAFF_IDENTIFIER
    role = get_auth_role(request)
    level = get_auth_level(request)
    unit = get_auth_unit(request)
    username = get_auth_user(request)
    
    if role != 'assistant' or level != 'district' or not unit or not username:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if unit == DCO_STAFF_IDENTIFIER:
        raise HTTPException(status_code=403, detail="DCO Staff cannot have talukas")
    
    selected = talukas or []
    valid_set = set(get_possible_talukas_for_district(unit))
    cleaned = [t for t in selected if t in valid_set]
    
    all_talukas = get_possible_talukas_for_district(unit)
    min_required = min(3, len(all_talukas)) if len(all_talukas) > 0 else 0
    
    if len(all_talukas) > 0 and len(cleaned) < min_required:
        error_msg = f"Select at least {min_required} taluka{'s' if min_required != 1 else ''} to activate."
        template_data = build_error_template_data(request, unit, level, set(cleaned), error_msg, db)
        response = templates.TemplateResponse("taluka_selection.html", template_data, status_code=400)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    if unit == 'Mumbai City':
        sync_taluka_selection_with_management(db, unit, [], username)
        return RedirectResponse(url=f"/ui/s{scheme_code}/taluka-selection", status_code=status.HTTP_303_SEE_OTHER)
    
    if len(cleaned) > 20:
        template_data = build_error_template_data(request, unit, level, set(cleaned), "You can select maximum 20 talukas only.", db)
        response = templates.TemplateResponse("taluka_selection.html", template_data, status_code=400)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    try:
        row = db.query(models.DistrictTalukaSelection).filter(models.DistrictTalukaSelection.district == unit).first()
        if row:
            row.selected_talukas = cleaned
        else:
            row = models.DistrictTalukaSelection(district=unit, selected_talukas=cleaned)
            db.add(row)
        
        sync_taluka_selection_with_management(db, unit, cleaned, username)
        
        db.commit()
        
        return RedirectResponse(url=f"/ui/s{scheme_code}/taluka-selection", status_code=status.HTTP_303_SEE_OTHER)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error in taluka selection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update taluka selection")


@router.post("/update-user", response_class=RedirectResponse)
async def ui_update_taluka_user(
    request: Request,
    scheme_code: str,
    db: Session = Depends(get_db),
    user_id: int = Form(...),
    taluka_name: str = Form(...),
    username: str = Form(...),
    password: Optional[str] = Form(None)
):
    role = get_auth_role(request)
    level = get_auth_level(request)
    unit = get_auth_unit(request)
    requester_username = get_auth_user(request)
    
    if role != 'assistant' or level != 'district' or not unit or not requester_username:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        user = db.query(models.User).filter(
            models.User.id == user_id,
            models.User.level == "taluka",
            models.User.unit == taluka_name,
            models.User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found or not active")
        
        user_district = taluka_name.split(' Taluka ')[0] if ' Taluka ' in taluka_name else taluka_name
        if user_district != unit:
            raise HTTPException(status_code=403, detail="Not authorized to modify this user")
        
        username = username.strip() if username else None
        password = password.strip() if password else None
        
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        
        if len(username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
        
        if password and len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
        success = update_taluka_user_credentials(db, user_id, username, password)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update user credentials. Username may already exist.")
        
        db.commit()
        
        return RedirectResponse(url=f"/ui/s{scheme_code}/taluka-selection", status_code=status.HTTP_303_SEE_OTHER)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating taluka user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user")

