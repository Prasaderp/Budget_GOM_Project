from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict
from datetime import datetime

from src.database import get_db
from src import models
from src.config import DISTRICTS
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.core.registry import scheme_registry
from src.utils_cache import memory_cache
from urllib.parse import quote, unquote

router = APIRouter(prefix="/api/completion-status", tags=["Completion Status"])

def _get_cache_key(sub_scheme_code: str, fiscal_year: str, district: str = None) -> str:
    if district:
        return f"completion:{sub_scheme_code}:{fiscal_year}:{district}"
    return f"completion:{sub_scheme_code}:{fiscal_year}:all"

def _invalidate_cache(sub_scheme_code: str, fiscal_year: str, district: str = None):
    parent_code = sub_scheme_code[:4] if len(sub_scheme_code) >= 4 else sub_scheme_code
    if district:
        memory_cache.delete(_get_cache_key(sub_scheme_code, fiscal_year, district))
    memory_cache.delete(_get_cache_key(sub_scheme_code, fiscal_year))
    memory_cache.delete(f"district_status_{parent_code}_{fiscal_year}")

@router.get("/{sub_scheme_code}")
async def get_completion_status(
    sub_scheme_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    
    if auth_level != 'district':
        raise HTTPException(status_code=403, detail="District level access required")
    
    decoded_auth_unit = unquote(auth_unit) if auth_unit else None
    if not decoded_auth_unit:
        raise HTTPException(status_code=400, detail="Invalid auth unit")
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    cache_key = _get_cache_key(sub_scheme_code, fiscal_year, decoded_auth_unit)
    cached = memory_cache.get(cache_key)
    if cached:
        return cached
    
    record = db.query(models.SubSchemaCompletion).filter(
        and_(
            models.SubSchemaCompletion.district == decoded_auth_unit,
            models.SubSchemaCompletion.sub_scheme_code == sub_scheme_code,
            models.SubSchemaCompletion.fiscal_year == fiscal_year
        )
    ).first()
    
    result = {
        "is_complete": record.is_complete if record else False,
        "completed_by": record.completed_by if record else None,
        "completed_at": record.completed_at.isoformat() if record and record.completed_at else None
    }
    
    memory_cache.set(cache_key, result, 180)
    return result

@router.post("/{sub_scheme_code}/toggle")
async def toggle_completion_status(
    sub_scheme_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if auth_role != 'assistant' or auth_level != 'district':
        raise HTTPException(status_code=403, detail="District assistant access required")
    
    decoded_auth_unit = unquote(auth_unit) if auth_unit else None
    if not decoded_auth_unit:
        raise HTTPException(status_code=400, detail="Invalid auth unit")
    
    scheme_config = scheme_registry.get_scheme(sub_scheme_code)
    if not scheme_config or not scheme_config.completion_enabled:
        raise HTTPException(status_code=400, detail="Completion feature not enabled for this scheme")

    fiscal_year = get_fiscal_year_from_request(request, db)
    
    record = db.query(models.SubSchemaCompletion).filter(
        and_(
            models.SubSchemaCompletion.district == decoded_auth_unit,
            models.SubSchemaCompletion.sub_scheme_code == sub_scheme_code,
            models.SubSchemaCompletion.fiscal_year == fiscal_year
        )
    ).with_for_update().first()
    
    now = datetime.utcnow()
    
    if record:
        new_state = not record.is_complete
        record.is_complete = new_state
        record.completed_by = auth_user
        record.completed_at = now
    else:
        record = models.SubSchemaCompletion(
            district=decoded_auth_unit,
            sub_scheme_code=sub_scheme_code,
            fiscal_year=fiscal_year,
            is_complete=True,
            completed_by=auth_user,
            completed_at=now
        )
        db.add(record)
        new_state = True
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    _invalidate_cache(sub_scheme_code, fiscal_year, decoded_auth_unit)
    
    return {
        "success": True,
        "is_complete": new_state,
        "message": "पूर्ण चिन्हांकित" if new_state else "प्रतीक्षेत चिन्हांकित"
    }

@router.get("/district/{district}")
async def get_district_subscheme_breakdown(
    district: str,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_level = request.cookies.get('auth_level', '')
    auth_role = request.cookies.get('auth_role', '')
    
    if auth_level != 'dco' or auth_role != 'assistant':
        raise HTTPException(status_code=403, detail="DCO assistant access required")
    
    if district not in DISTRICTS:
        raise HTTPException(status_code=400, detail="Invalid district")
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    scheme_code = request.cookies.get('selected_scheme', '')
    
    if not scheme_code:
        raise HTTPException(status_code=400, detail="No scheme selected")
    
    parent_schemes = scheme_registry.get_schemes_by_parent(scheme_code if not scheme_code.startswith('s') else scheme_code[1:])
    
    implemented_schemes = {
        code: config for code, config in parent_schemes.items() 
        if config.implemented
    }
    
    if not implemented_schemes:
        return {"district": district, "fiscal_year": fiscal_year, "subschemes": []}
    
    encoded_district = quote(district, safe='')
    completion_records = db.query(models.SubSchemaCompletion).filter(
        and_(
            models.SubSchemaCompletion.sub_scheme_code.in_(implemented_schemes.keys()),
            models.SubSchemaCompletion.fiscal_year == fiscal_year,
            or_(
                models.SubSchemaCompletion.district == district,
                models.SubSchemaCompletion.district == encoded_district
            )
        )
    ).all()
    
    completion_map = {rec.sub_scheme_code: rec for rec in completion_records}
    
    subscheme_statuses = []
    for sub_code, config in implemented_schemes.items():
        record = completion_map.get(sub_code)
        subscheme_statuses.append({
            "sub_scheme_code": sub_code,
            "name_mr": config.name_mr,
            "name_en": config.name_en,
            "is_complete": record.is_complete if record else False,
            "completed_by": record.completed_by if record else None,
            "completed_at": record.completed_at.isoformat() if record and record.completed_at else None
        })
    
    return {
        "district": district,
        "fiscal_year": fiscal_year,
        "subschemes": subscheme_statuses
    }
