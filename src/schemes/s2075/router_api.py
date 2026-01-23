"""API routes for scheme 2075 - Miscellaneous General Services.

Secured with authentication, authorization, and audit logging via create_secure_crud_routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.core.secure_crud import create_secure_crud_routes
from src.utils_fiscal_year import validate_fiscal_year
from src.utils_auth import get_auth_unit
from .models import SubHeadExpenditure2075, DistrictExpenditure2075
from .schemas import (
    SubHeadExpenditureCreate, SubHeadExpenditureUpdate, SubHeadExpenditureResponse,
    DistrictExpenditureCreate, DistrictExpenditureUpdate, DistrictExpenditureResponse
)
from .config import SCHEME_CONFIG
from .helpers import check_dco_access, get_allowed_districts

router = APIRouter(prefix="/api/s2075", tags=[f"API - {SCHEME_CONFIG.name_mr}"])


# ============================================================================
# CUSTOM ENDPOINTS (Non-standard CRUD operations)
# ============================================================================

@router.get("/sub-head", response_model=List[SubHeadExpenditureResponse])
def list_sub_head_expenditure(
    request: Request, 
    fiscal_year: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """List sub-head expenditure records (DCO only)."""
    if not check_dco_access(request.cookies.get("auth_level", "")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO only")
    
    fy = validate_fiscal_year(fiscal_year, db)
    
    query = db.query(SubHeadExpenditure2075).filter(
        SubHeadExpenditure2075.fiscal_year == fy,
        SubHeadExpenditure2075.sub_scheme_code == "20750249",
    ).order_by(SubHeadExpenditure2075.id).offset(skip).limit(limit)
    
    return query.all()


@router.get("/sub-head/{id}", response_model=SubHeadExpenditureResponse)
def get_sub_head_expenditure(request: Request, id: int, db: Session = Depends(get_db)):
    """Get single sub-head expenditure record (DCO only)."""
    if not check_dco_access(request.cookies.get("auth_level", "")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - DCO only")
    
    item = db.query(SubHeadExpenditure2075).filter(
        SubHeadExpenditure2075.id == id,
        SubHeadExpenditure2075.sub_scheme_code == "20750249",
    ).first()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return item


@router.get("/district", response_model=List[DistrictExpenditureResponse])
def list_district_expenditure(
    request: Request, 
    fiscal_year: Optional[str] = None, 
    district: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """List district expenditure records (filtered by access)."""
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)
    
    allowed = get_allowed_districts(auth_level, auth_unit)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    if district and district not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid district")
    
    fy = validate_fiscal_year(fiscal_year, db)
    
    query = db.query(DistrictExpenditure2075).filter(
        DistrictExpenditure2075.fiscal_year == fy,
        DistrictExpenditure2075.sub_scheme_code == "20750294",
    )
    
    if district:
        query = query.filter(DistrictExpenditure2075.district == district)
    else:
        query = query.filter(DistrictExpenditure2075.district.in_(allowed))
    
    return query.order_by(DistrictExpenditure2075.district).offset(skip).limit(limit).all()


@router.get("/district/{id}", response_model=DistrictExpenditureResponse)
def get_district_expenditure(request: Request, id: int, db: Session = Depends(get_db)):
    """Get single district expenditure record (with access check)."""
    auth_level = request.cookies.get("auth_level", "")
    auth_unit = get_auth_unit(request)
    
    allowed = get_allowed_districts(auth_level, auth_unit)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    item = db.query(DistrictExpenditure2075).filter(
        DistrictExpenditure2075.id == id,
        DistrictExpenditure2075.sub_scheme_code == "20750294",
    ).first()
    
    if not item or item.district not in allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    return item
