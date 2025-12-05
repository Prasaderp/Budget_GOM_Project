from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import get_db
from src import models
from src.config import DISTRICTS, CATEGORIES, CLASSES_SHEET1_2, CLASSES_SHEET3, STATUSES, DESIGNATIONS, PRIMARY_UNITS
from src.utils_scheme import get_scheme_models
from src.audit_service import AuditService
from src.routers.auth import verify_password
from src.notification_service import send_fiscal_year_alert
from src.utils_cache import memory_cache, invalidate_cache_pattern
from pydantic import BaseModel, validator
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)
FY_LIST_CACHE_KEY = "fiscal_years_list"
FY_CACHE_TTL = 300

def invalidate_fy_caches():
    memory_cache.delete(FY_LIST_CACHE_KEY)
    memory_cache.delete("fy_default")
    invalidate_cache_pattern("fy_valid_")

router = APIRouter(prefix="/api/fiscal-year", tags=["Fiscal Year"], include_in_schema=False)

class FiscalYearCreate(BaseModel):
    year_range: str
    
    @validator('year_range')
    def validate_year_range(cls, v):
        if not re.match(r'^\d{4}-\d{2}$', v):
            raise ValueError('Invalid format. Use YYYY-YY (e.g., 2025-26)')
        
        parts = v.split('-')
        start_year = int(parts[0])
        end_year_short = int(parts[1])
        expected_end = (start_year + 1) % 100
        
        if end_year_short != expected_end:
            raise ValueError(f'Invalid year range. After {start_year} should be {expected_end:02d}, not {end_year_short:02d}')
        
        current_year = datetime.now().year
        if start_year > current_year + 10:
            raise ValueError('Cannot create fiscal year more than 10 years in the future')
        
        if start_year < 2020:
            raise ValueError('Cannot create fiscal year before 2020')
        
        return v

class FiscalYearDelete(BaseModel):
    year_range: str
    password: str

class FiscalYearResponse(BaseModel):
    id: int
    year_range: str
    is_active: bool
    created_by: str
    created_at: str
    class Config: from_attributes = True

@router.get("/list", response_class=JSONResponse)
async def get_fiscal_years(db: Session = Depends(get_db)):
    cached = memory_cache.get(FY_LIST_CACHE_KEY)
    if cached:
        return JSONResponse(cached)
    
    years = db.query(models.FiscalYear.id, models.FiscalYear.year_range, models.FiscalYear.is_active).filter(
        models.FiscalYear.is_active == True
    ).order_by(models.FiscalYear.year_range.desc()).all()
    
    data = {"fiscal_years": [{"id": y.id, "year_range": y.year_range, "is_active": y.is_active} for y in years]}
    memory_cache.set(FY_LIST_CACHE_KEY, data, FY_CACHE_TTL)
    return JSONResponse(data)

@router.post("/create", response_class=JSONResponse)
async def create_fiscal_year(request: Request, background_tasks: BackgroundTasks, payload: FiscalYearCreate, db: Session = Depends(get_db)):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if auth_level != 'dco' or auth_role != 'assistant':
        raise HTTPException(status_code=403, detail="Only DCO assistants can create fiscal years")
    
    existing = db.query(models.FiscalYear).filter(models.FiscalYear.year_range == payload.year_range).first()
    if existing:
        raise HTTPException(status_code=400, detail="Fiscal year already exists")
    
    new_year = models.FiscalYear(year_range=payload.year_range, created_by=auth_user, is_active=True)
    db.add(new_year)
    db.flush()
    
    try:
        try:
            AuditService.log_create(db, request, new_year)
        except Exception:
            pass
        
        logger.info(f"Creating skeleton records for fiscal year {payload.year_range}")
        
        # Get all implemented 2053 sub-schemes dynamically
        from src.core.registry import scheme_registry
        sub_schemes_2053 = scheme_registry.get_schemes_by_parent('2053')
        if not sub_schemes_2053:
            logger.warning("No implemented 2053 sub-schemes found")
            sub_schemes_2053 = {}
        
        for sub_scheme_code in sub_schemes_2053.keys():
            BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure = get_scheme_models(sub_scheme_code)
            
            bpd_records = []
            ps_records = []
            pe_records = []
            ue_records = []
            
            for district in DISTRICTS:
                for category in CATEGORIES:
                    for cls in CLASSES_SHEET1_2:
                        for designation in DESIGNATIONS:
                            bpd_records.append(BudgetPostDetails(
                                district=district, category=category, class_type=cls, designation=designation,
                                fiscal_year=payload.year_range, sanctioned_posts_2024_25=0, sanctioned_posts_2025_26=0,
                                special_pay=0, basic_pay=0, grade_pay=0, local_supplementary_allowance=0,
                                vehicle_allowance=0, washing_allowance=0, cash_allowance=0, footwear_allowance_other=0
                            ))
            
            for district in DISTRICTS:
                for category in CATEGORIES:
                    for cls in CLASSES_SHEET1_2:
                        for status in STATUSES:
                            ps_records.append(PostStatus(
                                district=district, category=category, class_type=cls, status=status,
                                fiscal_year=payload.year_range, posts=0, salary=0, grade_pay=0,
                                special_pay=0, dearness_allowance=0, local_supplementary_allowance=0,
                                house_rent_allowance=0, travel_allowance=0, other=0
                            ))
            
            for district in DISTRICTS:
                for category in CATEGORIES:
                    for cls in CLASSES_SHEET3:
                        pe_records.append(PostExpenses(
                            district=district, category=category, class_type=cls,
                            fiscal_year=payload.year_range, filled_posts=0, vacant_posts=0,
                            medical_expenses=0, festival_advance=0, swagram_maharashtra_darshan=0,
                            seventh_pay_commission_difference_nps=0, nps=0,
                            seventh_pay_commission_difference=0, other=0
                        ))
            
            for district in DISTRICTS:
                for primary_unit in PRIMARY_UNITS:
                    ue_records.append(UnitExpenditure(
                        district=district, unit_account=primary_unit,
                        fiscal_year=payload.year_range, expenditure_2021_22=0,
                        expenditure_2022_23=0, expenditure_2023_24=0, budget_2024_25=0,
                        forecast_2024_25=0, budget_2025_26_estimating_officer=0,
                        budget_2025_26_controlling_officer=0, budget_2025_26_admin_dept=0,
                        budget_2025_26_finance_dept=0
                    ))
            
            BATCH_SIZE = 1000
            for i in range(0, len(bpd_records), BATCH_SIZE):
                db.bulk_save_objects(bpd_records[i:i+BATCH_SIZE])
                db.flush()
            for i in range(0, len(ps_records), BATCH_SIZE):
                db.bulk_save_objects(ps_records[i:i+BATCH_SIZE])
                db.flush()
            for i in range(0, len(pe_records), BATCH_SIZE):
                db.bulk_save_objects(pe_records[i:i+BATCH_SIZE])
                db.flush()
            for i in range(0, len(ue_records), BATCH_SIZE):
                db.bulk_save_objects(ue_records[i:i+BATCH_SIZE])
                db.flush()
        
        db.commit()
        invalidate_fy_caches()
        logger.info(f"Created fiscal year {payload.year_range}")
        
        try:
            background_tasks.add_task(send_fiscal_year_alert, None, new_year, 'created')
        except Exception as e:
            logger.error(f"Failed to queue fiscal year creation alert: {e}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create fiscal year: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create fiscal year: {str(e)}")
    
    return {"success": True, "message": "Fiscal year created successfully", "year": {"id": new_year.id, "year_range": new_year.year_range}}

@router.post("/delete", response_class=JSONResponse)
async def delete_fiscal_year(request: Request, background_tasks: BackgroundTasks, payload: FiscalYearDelete, db: Session = Depends(get_db)):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if auth_level != 'dco' or auth_role != 'assistant':
        raise HTTPException(status_code=403, detail="Only DCO assistants can delete fiscal years")
    
    user = db.query(models.User).filter(models.User.username == auth_user).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    fiscal_year = db.query(models.FiscalYear).filter(models.FiscalYear.year_range == payload.year_range).first()
    if not fiscal_year:
        raise HTTPException(status_code=404, detail="Fiscal year not found")
    
    active_count = db.query(func.count(models.FiscalYear.id)).filter(models.FiscalYear.is_active == True).scalar()
    if active_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only active fiscal year")
    
    try:
        logger.info(f"Deleting fiscal year {payload.year_range}")
        fy = payload.year_range
        
        # Get all implemented 2053 sub-schemes dynamically
        from src.core.registry import scheme_registry
        sub_schemes_2053 = scheme_registry.get_schemes_by_parent('2053')
        if not sub_schemes_2053:
            logger.warning("No implemented 2053 sub-schemes found")
            sub_schemes_2053 = {}
        
        for sub_scheme_code in sub_schemes_2053.keys():
            BudgetPostDetails, PostStatus, PostExpenses, UnitExpenditure = get_scheme_models(sub_scheme_code)
            db.query(BudgetPostDetails).filter(BudgetPostDetails.fiscal_year == fy).delete(synchronize_session=False)
            db.query(PostStatus).filter(PostStatus.fiscal_year == fy).delete(synchronize_session=False)
            db.query(PostExpenses).filter(PostExpenses.fiscal_year == fy).delete(synchronize_session=False)
            db.query(UnitExpenditure).filter(UnitExpenditure.fiscal_year == fy).delete(synchronize_session=False)
        
        year_range = fiscal_year.year_range
        is_active = fiscal_year.is_active
        
        try:
            AuditService.log_delete(db, request, fiscal_year)
        except Exception:
            pass
        
        db.delete(fiscal_year)
        db.commit()
        invalidate_fy_caches()
        
        try:
            fiscal_year_copy = models.FiscalYear(year_range=year_range, is_active=is_active)
            background_tasks.add_task(send_fiscal_year_alert, None, fiscal_year_copy, 'deleted')
        except Exception as e:
            logger.error(f"Failed to queue fiscal year deletion alert: {e}")
        
        logger.info(f"Deleted fiscal year {payload.year_range}")
        return {"success": True, "message": f"Fiscal year {payload.year_range} deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete fiscal year: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete fiscal year: {str(e)}")

@router.get("/current", response_class=JSONResponse)
async def get_current_fiscal_year(request: Request, db: Session = Depends(get_db)):
    from src.utils_fiscal_year import get_fiscal_year_from_request
    fiscal_year = get_fiscal_year_from_request(request, db)
    return {"fiscal_year": fiscal_year}

@router.post("/set", response_class=JSONResponse)
async def set_fiscal_year(request: Request, year_range: str = Query(...), db: Session = Depends(get_db)):
    from src.utils_fiscal_year import validate_fiscal_year
    validated_year = validate_fiscal_year(year_range, db)
    
    if validated_year != year_range:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal year. Using: {validated_year}")
    
    resp = JSONResponse({"success": True, "fiscal_year": validated_year})
    resp.set_cookie("fiscal_year", validated_year, httponly=False, samesite="lax", max_age=2592000)
    return resp
