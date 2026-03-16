"""API controller for budget post details - sub-scheme 20450091"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.models import PayMatrix
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from src.schemes.common.post_levels.api_router import create_post_levels_router
from .models import BudgetPostDetails
from .config import (
    SCHEME_CONFIG, SUB_SCHEME_CODE, MARATHI_TO_ENGLISH_DESIGNATIONS
)
from .helpers import (
    check_edit_permission_for_scheme, invalidate_scheme_cache, log_audit_async,
    get_request_info, validate_numeric_inputs, validate_access_control
)
from src.utils_auth import get_auth_unit, get_auth_role, get_auth_level, get_auth_user, is_authenticated
from src.audit_service import AuditService

# Excel export functionality
from .excel_export import export_original_workbook_async
from fastapi.responses import StreamingResponse

router = APIRouter(
    prefix="/ui/s20450091/budget-post-details",
    tags=["API - Budget Post Details 20450091"],
    include_in_schema=False
)

# Access validator for post levels
def validate_budget_post_access(request: Request, budget_post, db: Session):
    """Validate user access to budget post based on district/taluka"""
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    return validate_access_control(budget_post.district, auth_level, auth_unit, db)

# Include post levels router for multi-level data entry
post_levels_router = create_post_levels_router(
    sub_scheme_code=SUB_SCHEME_CODE,
    budget_post_model=BudgetPostDetails,
    table_name="budget_post_details_20450091",
    scheme_code=SCHEME_CONFIG.code,
    access_validator=validate_budget_post_access,
    prefix="/api/post-levels"
)
router.include_router(post_levels_router)

_BUDGET_COLUMNS = [
    'sanctioned_posts_prev1', 'sanctioned_posts_curr', 'special_pay', 'basic_pay',
    'grade_pay', 'local_supplementary_allowance', 'vehicle_allowance',
    'washing_allowance', 'cash_allowance', 'footwear_allowance_other', 'hra_rate'
]

def _format_basic_pay(val):
    """Format basic pay value for display"""
    if val is None:
        return 0
    fval = float(val)
    if fval >= 1000:
        fval = round(round(fval / 100) / 10, 1)
    return int(fval) if fval == int(fval) else fval

def translate_marathi_designation_search(search_term: str) -> str:
    """Translate Marathi designation search to English"""
    if not search_term:
        return search_term
    search_lower = search_term.lower().strip()
    for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
        if m_term.lower() in search_lower or search_lower in m_term.lower():
            return e_desig
    for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
        m_words = m_term.lower().split()
        s_words = search_lower.split()
        for mw in m_words:
            for sw in s_words:
                if len(sw) >= 3 and (mw.startswith(sw) or sw.startswith(mw)):
                    return e_desig
    return search_term

@router.get("/api/pay-matrix/stages", response_class=JSONResponse)
async def api_get_pay_matrix_stages(request: Request, db: Session = Depends(get_db)):
    """Get all pay matrix stages"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    stages = db.query(PayMatrix.stage).distinct().order_by(PayMatrix.stage).all()
    sorted_stages = sorted([s[0] for s in stages], key=lambda x: int(x.split('-')[1]))
    return JSONResponse({"stages": sorted_stages})

@router.get("/api/pay-matrix/levels/{stage}", response_class=JSONResponse)
async def api_get_pay_matrix_levels(request: Request, stage: str, db: Session = Depends(get_db)):
    """Get pay matrix levels for a stage"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    levels = db.query(PayMatrix.level).filter(PayMatrix.stage == stage).order_by(PayMatrix.level).all()
    return JSONResponse({"levels": [l[0] for l in levels]})

@router.get("/api/pay-matrix/basic-pay", response_class=JSONResponse)
async def api_get_pay_matrix_basic_pay(request: Request, stage: str = Query(...), level: int = Query(...), db: Session = Depends(get_db)):
    """Get basic pay for stage and level, respecting salary mode"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from src.utils_salary_mode import get_salary_mode
    fiscal_year = get_fiscal_year_from_request(request, db)
    salary_mode = get_salary_mode(db, fiscal_year)
    record = db.query(PayMatrix).filter(PayMatrix.stage == stage, PayMatrix.level == level).first()
    if not record:
        return JSONResponse({"found": False, "basic_pay": 0})
    multiplier = 12 if salary_mode == 'annual' else 1
    basic_pay_full = record.basic_pay * multiplier
    basic_pay_thousands = basic_pay_full // 1000
    return JSONResponse({"found": True, "basic_pay": basic_pay_thousands, "basic_pay_full": basic_pay_full, "salary_mode": salary_mode})

@router.get("/api/designations", response_class=JSONResponse)
async def api_get_designations(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    db: Session = Depends(get_db)
):
    """Get distinct designations matching filters"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(BudgetPostDetails.designation).distinct().filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(BudgetPostDetails.district == district)
    if category:
        query = query.filter(BudgetPostDetails.category == category)
    if cls:
        query = query.filter(BudgetPostDetails.class_type == cls)
    designations = [row[0] for row in query.order_by(BudgetPostDetails.designation).all()]
    return JSONResponse({"designations": designations})

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(
    request: Request,
    district: str = Query(...),
    category: str = Query(...),
    cls: str = Query(..., alias="class"),
    designation: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get record data for a specific budget post detail"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == sub_scheme,
        BudgetPostDetails.district == district,
        BudgetPostDetails.category == category,
        BudgetPostDetails.class_type == cls,
        BudgetPostDetails.designation == designation
    ).first()
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True, "id": record.id,
        "sanctioned_posts_prev1": record.sanctioned_posts_prev1 or 0,
        "sanctioned_posts_curr": record.sanctioned_posts_curr or 0,
        "special_pay": record.special_pay or 0,
        "basic_pay": _format_basic_pay(record.basic_pay),
        "grade_pay": record.grade_pay or 0,
        "local_supplementary_allowance": record.local_supplementary_allowance or 0,
        "vehicle_allowance": record.vehicle_allowance or 0,
        "washing_allowance": record.washing_allowance or 0,
        "cash_allowance": record.cash_allowance or 0,
        "footwear_allowance_other": record.footwear_allowance_other or 0,
        "hra_rate": record.hra_rate or 'X'
    })

@router.post("/api/update-inline", response_class=JSONResponse)
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    SanctionedPostsPrev1: int = Form(0),
    SanctionedPostsCurr: int = Form(0),
    SpecialPay: int = Form(0),
    BasicPay: float = Form(0),
    GradePay: int = Form(0),
    LocalSupplemetoryAllowance: int = Form(0),
    VehicleAllowance: int = Form(0),
    WashingAllowance: int = Form(0),
    CashAllowance: int = Form(0),
    FootWareAllowanceOther: int = Form(0),
    HraRate: str = Form('X')
):
    """Update budget post detail inline"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_user = get_auth_user(request)
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    ).first()
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    allowed, error_msg = validate_access_control(record.district, auth_level, auth_unit, db)
    if not allowed:
        return JSONResponse({"success": False, "message": error_msg}, status_code=403)
    
    vals_int = [
        SanctionedPostsPrev1, SanctionedPostsCurr, SpecialPay, GradePay,
        LocalSupplemetoryAllowance, VehicleAllowance, WashingAllowance,
        CashAllowance, FootWareAllowanceOther
    ]
    is_valid, error_msg = validate_numeric_inputs(*vals_int, BasicPay)
    if not is_valid:
        return JSONResponse({"success": False, "message": error_msg}, status_code=400)
    
    if HraRate not in ('X', 'Y', 'Z'):
        HraRate = 'X'
    
    # ---- NEW: Validate sanctioned_posts_curr reduction ----
    from src.schemes.common.post_levels.repository import PostLevelRepository
    post_level_repo = PostLevelRepository(db)
    fiscal_year = get_fiscal_year_from_request(request, db)
    current_level_count = post_level_repo.get_count(
        record.id, sub_scheme, "budget_post_details_20450091", fiscal_year
    )
    if SanctionedPostsCurr < current_level_count:
        return JSONResponse({
            "success": False,
            "message": f"मंजूर पदे {SanctionedPostsCurr} पेक्षा {current_level_count} स्तर आधीच अस्तित्वात आहेत. कृपया प्रथम स्तर हटवा."
        }, status_code=400)
    # ---- END NEW ----
    
    old_values = {k: getattr(record, k) for k in _BUDGET_COLUMNS}
    
    record.sanctioned_posts_prev1 = SanctionedPostsPrev1
    record.sanctioned_posts_curr = SanctionedPostsCurr
    record.special_pay = SpecialPay
    record.basic_pay = BasicPay
    record.grade_pay = GradePay
    record.local_supplementary_allowance = LocalSupplemetoryAllowance
    record.vehicle_allowance = VehicleAllowance
    record.washing_allowance = WashingAllowance
    record.cash_allowance = CashAllowance
    record.footwear_allowance_other = FootWareAllowanceOther
    record.hra_rate = HraRate
    
    AuditService.log_action(
        db=db,
        request=request,
        action='UPDATE',
        table_name=SCHEME_CONFIG.forms['budget_post_details'].table_name,
        record_id=id,
        old_values=old_values,
        new_values={k: getattr(record, k) for k in _BUDGET_COLUMNS}
    )
    db.commit()
    
    invalidate_scheme_cache(record.district)
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})


@router.get("/api/da-rate", response_class=JSONResponse)
async def api_get_da_rate(request: Request, db: Session = Depends(get_db)):
    """Get current DA (Dearness Allowance) rate for fiscal year
    
    Used by inline edit forms and post levels forms to fetch current DA percentage
    
    Returns:
        {
            "fiscal_year": relative_years.fy_curr.full if relative_years else "Curr Year",
            "da_percentage": 64.00,
            "da_rate": 0.64
        }
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from src.utils_da_rate import get_da_percentage, get_da_rate
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    da_percentage = get_da_percentage(db, fiscal_year)
    da_rate = get_da_rate(db, fiscal_year)
    
    return JSONResponse({
        "fiscal_year": fiscal_year,
        "da_percentage": float(da_percentage),
        "da_rate": da_rate
    })


@router.get("/export-original", response_class=StreamingResponse)
async def export_budget_details_original(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Export original Excel workbook with production-grade throttling.
    
    Features:
    - Concurrency limit (max 10 simultaneous exports)
    - 60-second timeout protection
    - 503 response when server is overloaded
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return await export_original_workbook_async(
        db, user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year
    )


@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_budget_details_sheet_only(
    request: Request,
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Export only budget post details sheet with throttling.
    
    More memory-efficient than full workbook export.
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    fiscal_year = get_fiscal_year_from_request(request, db)
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    _, sub_scheme = get_scheme_from_cookies(request)
    return await export_original_workbook_async(
        db,
        only_sheet="budget_post_details",
        user_district=user_district,
        sub_scheme_code=sub_scheme,
        fiscal_year=fiscal_year
    )
