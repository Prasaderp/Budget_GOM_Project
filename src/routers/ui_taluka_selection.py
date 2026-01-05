from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, union_all
from typing import List, Optional, Dict
import logging

from src import models
from src.utils_scheme import get_scheme_models, get_scheme_base_template
from src.database import get_db
from src.core.templates import templates
from src.core.registry import scheme_registry
from src.config import DISTRICTS, DISTRICTS_MR
from src.utils_taluka import get_possible_talukas_for_district, get_selected_talukas
from src.utils_taluka_user_management import sync_taluka_selection_with_management, get_taluka_users_for_district, update_taluka_user_credentials
from src.utils_fiscal_year import get_fiscal_year_from_request, DEFAULT_FISCAL_YEAR
from src.utils_cache import memory_cache

logger = logging.getLogger(__name__)

def _resolve_parent_scheme_code(scheme_code: str) -> str:
    """Resolve sub-scheme code to its parent scheme code for status queries."""
    scheme_config = scheme_registry.get_scheme(scheme_code)
    return scheme_config.parent_scheme if scheme_config else scheme_code

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

def get_taluka_data_status(db: Session, taluka_name: str, scheme_code: str, fiscal_year: str) -> str:
    from sqlalchemy import exists
    district = taluka_name.split(' Taluka ')[0] if ' Taluka ' in taluka_name else taluka_name
    
    parent_schemes = scheme_registry.get_schemes_by_parent(_resolve_parent_scheme_code(scheme_code))
    if not parent_schemes:
        return 'pending'
    
    has_bpd = False
    has_ps = False
    for sub_scheme_code in parent_schemes.keys():
        BudgetPostDetails, PostStatus, _, _ = get_scheme_models(sub_scheme_code)
        if BudgetPostDetails and not has_bpd:
            has_bpd = db.query(exists().where(
                BudgetPostDetails.district == district,
                BudgetPostDetails.fiscal_year == fiscal_year
            )).scalar()
        if PostStatus and not has_ps:
            has_ps = db.query(exists().where(
                PostStatus.district == district,
                PostStatus.fiscal_year == fiscal_year
            )).scalar()
        if has_bpd and has_ps:
            break
    
    return 'processed' if (has_bpd or has_ps) else 'pending'

def get_all_talukas_status_batch(db: Session, taluka_names: List[str], scheme_code: str, fiscal_year: str) -> Dict[str, str]:
    if not taluka_names:
        return {}
    
    cache_key = f"taluka_status_{scheme_code}_{fiscal_year}_{hash(tuple(sorted(taluka_names)))}"
    cached = memory_cache.get(cache_key)
    if cached:
        return cached
    
    parent_schemes = scheme_registry.get_schemes_by_parent(_resolve_parent_scheme_code(scheme_code))
    if not parent_schemes:
        result = {t: 'pending' for t in taluka_names}
        memory_cache.set(cache_key, result, 180)
        return result
    
    district_map = {}
    for taluka_name in taluka_names:
        district = taluka_name.split(' Taluka ')[0] if ' Taluka ' in taluka_name else taluka_name
        if district not in district_map:
            district_map[district] = []
        district_map[district].append(taluka_name)
    
    union_queries = []
    for sub_scheme_code in parent_schemes.keys():
        BudgetPostDetails, PostStatus, _, _ = get_scheme_models(sub_scheme_code)
        if BudgetPostDetails:
            union_queries.append(
                select(BudgetPostDetails.district).where(
                    BudgetPostDetails.district.in_(list(district_map.keys())),
                    BudgetPostDetails.fiscal_year == fiscal_year
                ).distinct()
            )
        if PostStatus:
            union_queries.append(
                select(PostStatus.district).where(
                    PostStatus.district.in_(list(district_map.keys())),
                    PostStatus.fiscal_year == fiscal_year
                ).distinct()
            )
    
    if not union_queries:
        result = {t: 'pending' for t in taluka_names}
        memory_cache.set(cache_key, result, 180)
        return result
    
    try:
        combined = union_all(*union_queries)
        districts_with_data = {row[0] for row in db.execute(combined)}
        result = {}
        for taluka_name in taluka_names:
            district = taluka_name.split(' Taluka ')[0] if ' Taluka ' in taluka_name else taluka_name
            result[taluka_name] = 'processed' if district in districts_with_data else 'pending'
    except Exception as e:
        logger.error(f"Failed to get taluka status batch: {e}", exc_info=True)
        result = {t: 'pending' for t in taluka_names}
    
    memory_cache.set(cache_key, result, 180)
    return result


def get_all_districts_status_batch(db: Session, scheme_code: str, fiscal_year: str) -> Dict[str, str]:
    """Batch query all districts' status in single DB round-trip with fiscal year filtering."""
    cache_key = f"district_status_{scheme_code}_{fiscal_year}"
    cached = memory_cache.get(cache_key)
    if cached:
        return cached
    
    parent_schemes = scheme_registry.get_schemes_by_parent(_resolve_parent_scheme_code(scheme_code))
    if not parent_schemes:
        result = {d: 'pending' for d in DISTRICTS}
        memory_cache.set(cache_key, result, 180)
        return result
    
    union_queries = []
    for sub_scheme_code in parent_schemes.keys():
        BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure = get_scheme_models(sub_scheme_code)
        if BudgetPostDetails:
            union_queries.append(
                select(BudgetPostDetails.district).where(
                    BudgetPostDetails.fiscal_year == fiscal_year
                ).distinct()
            )
        if PostStatus:
            union_queries.append(
                select(PostStatus.district).where(
                    PostStatus.fiscal_year == fiscal_year
                ).distinct()
            )
        if PostExpenses:
            union_queries.append(
                select(PostExpenses.district).where(
                    PostExpenses.fiscal_year == fiscal_year
                ).distinct()
            )
        if UnitExpenditure:
            union_queries.append(
                select(UnitExpenditure.district).where(
                    UnitExpenditure.fiscal_year == fiscal_year
                ).distinct()
            )
    
    if not union_queries:
        result = {d: 'pending' for d in DISTRICTS}
        memory_cache.set(cache_key, result, 180)
        return result
    
    try:
        combined = union_all(*union_queries)
        districts_with_data = {row[0] for row in db.execute(combined)}
        result = {d: ('processed' if d in districts_with_data else 'pending') for d in DISTRICTS}
    except Exception as e:
        logger.error(f"Failed to get district status batch: {e}", exc_info=True)
        result = {d: 'pending' for d in DISTRICTS}
    
    memory_cache.set(cache_key, result, 180)
    return result

def invalidate_district_status_cache(scheme_code: str, fiscal_year: str) -> None:
    """Invalidate district status cache after data modifications."""
    cache_key = f"district_status_{scheme_code}_{fiscal_year}"
    memory_cache.delete(cache_key)

@router.get("", response_class=HTMLResponse)
async def ui_get_taluka_selection(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    from src.config import DCO_STAFF_IDENTIFIER
    role = request.cookies.get('auth_role') or ''
    level = request.cookies.get('auth_level') or ''
    unit = request.cookies.get('auth_unit') or ''
    username = request.cookies.get('auth_user') or ''
    
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
        taluka_status = get_all_talukas_status_batch(db, list(sorted_taluka_details.keys()), scheme_code, fiscal_year)
        
        template_data = {
            "request": request, "resource_name": "तालुका निवड",
            "district": unit, "talukas": all_talukas, "selected": set(selected),
            "auth_level": level, "taluka_user_details": sorted_taluka_details,
            "taluka_status": taluka_status, "district_status": {}, "district_names": {},
            "base_template": get_scheme_base_template(request), "scheme_code": scheme_code,
            "fiscal_year": fiscal_year, "districts": DISTRICTS
        }
        
    elif level == 'dco':
        try:
            district_status = get_all_districts_status_batch(db, scheme_code, fiscal_year)
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
        
        return RedirectResponse(url=f"/ui/s{scheme_code}/taluka-selection", status_code=status.HTTP_303_SEE_OTHER)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating taluka user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user")

