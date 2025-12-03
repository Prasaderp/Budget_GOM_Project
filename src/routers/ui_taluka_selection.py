from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import logging

from src import models, schemas
from src.database import get_db
from src.core.templates import templates
from src.config import DISTRICTS
from src.utils_taluka import get_possible_talukas_for_district, get_selected_talukas
from src.utils_taluka_user_management import sync_taluka_selection_with_management, get_taluka_users_for_district, update_taluka_user_credentials
from src.utils_scheme import get_scheme_base_template

logger = logging.getLogger(__name__)

DISTRICT_NAMES_MR = {
    'Mumbai City': 'मुंबई शहर',
    'Mumbai Suburban': 'मुंबई उपनगर',
    'Thane': 'ठाणे',
    'Raigad': 'रायगड',
    'Palghar': 'पालघर',
    'Ratnagiri': 'रत्नागिरी',
    'Sindhudurg': 'सिंधुदुर्ग'
}

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

def get_taluka_data_status(db: Session, taluka_name: str) -> str:
    from sqlalchemy import exists
    district = taluka_name.split(' Taluka ')[0] if ' Taluka ' in taluka_name else taluka_name
    
    has_bpd = db.query(exists().where(models.BudgetPostDetails.district == district)).scalar()
    has_ps = db.query(exists().where(models.PostStatus.district == district)).scalar()
    
    return 'processed' if (has_bpd or has_ps) else 'pending'


def get_district_data_status(db: Session, district: str) -> str:
    from sqlalchemy import exists
    
    has_bpd = db.query(exists().where(models.BudgetPostDetails.district == district)).scalar()
    has_ps = db.query(exists().where(models.PostStatus.district == district)).scalar()
    has_pe = db.query(exists().where(models.PostExpenses.district == district)).scalar()
    has_ue = db.query(exists().where(models.UnitExpenditure.district == district)).scalar()
    
    return 'processed' if (has_bpd or has_ps or has_pe or has_ue) else 'pending'

@router.get("", response_class=HTMLResponse)
async def ui_get_taluka_selection(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    from src.config import DCO_STAFF_IDENTIFIER
    role = request.cookies.get('auth_role') or ''
    level = request.cookies.get('auth_level') or ''
    unit = request.cookies.get('auth_unit') or ''
    if role != 'assistant' or level not in ('district', 'dco'):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if level == 'district' and unit == DCO_STAFF_IDENTIFIER:
        raise HTTPException(status_code=403, detail="DCO Staff cannot have talukas")
    
    if level == 'district' and unit:
        row = db.query(models.DistrictTalukaSelection).filter(models.DistrictTalukaSelection.district == unit).first()
        selected = row.selected_talukas if row else get_selected_talukas(db, unit)
        all_talukas = get_possible_talukas_for_district(unit)
        taluka_user_details = get_taluka_users_for_district(db, unit)
        
        sorted_taluka_details = dict(sorted(taluka_user_details.items())) if taluka_user_details else {}
        taluka_status = {key: get_taluka_data_status(db, key) for key in sorted_taluka_details}
        
        template_data = {
            "request": request, "resource_name": "तालुका निवड",
            "district": unit, "talukas": all_talukas, "selected": set(selected),
            "auth_level": level, "taluka_user_details": sorted_taluka_details,
            "taluka_status": taluka_status, "district_status": {}, "district_names": {},
            "base_template": get_scheme_base_template(request), "scheme_code": scheme_code
        }
        
    elif level == 'dco':
        district_status = {district: get_district_data_status(db, district) for district in DISTRICTS}
        
        template_data = {
            "request": request, "resource_name": "अंदाजपत्रक सद्यस्थिती",
            "district": unit, "talukas": [], "selected": set(), "auth_level": level,
            "taluka_user_details": {}, "taluka_status": {},
            "district_status": district_status, "district_names": DISTRICT_NAMES_MR,
            "base_template": get_scheme_base_template(request), "scheme_code": scheme_code
        }
    
    response = templates.TemplateResponse("taluka_selection.html", template_data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.post("", response_class=RedirectResponse)
async def ui_post_taluka_selection(request: Request, scheme_code: str, db: Session = Depends(get_db), talukas: Optional[List[str]] = Form(None)):
    from src.config import DCO_STAFF_IDENTIFIER
    role = request.cookies.get('auth_role') or ''
    level = request.cookies.get('auth_level') or ''
    unit = request.cookies.get('auth_unit') or ''
    username = request.cookies.get('auth_user') or ''
    
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
        
        return RedirectResponse(url=router.url_path_for("ui_get_taluka_selection"), status_code=status.HTTP_303_SEE_OTHER)
    
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
    role = request.cookies.get('auth_role') or ''
    level = request.cookies.get('auth_level') or ''
    unit = request.cookies.get('auth_unit') or ''
    requester_username = request.cookies.get('auth_user') or ''
    
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
        
        return RedirectResponse(url=router.url_path_for("ui_get_taluka_selection"), status_code=status.HTTP_303_SEE_OTHER)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating taluka user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user")

