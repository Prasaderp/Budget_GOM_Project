"""API controller for budget post details"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from ...config import SCHEME_CONFIG, SUB_SCHEME_CODE
from ...models import BudgetPostDetails
from ..repositories.budget_post_repository import BudgetPostRepository
from ..services.budget_post_service import BudgetPostService
from ..services.pay_matrix_service import PayMatrixService
from ..services.designation_service import DesignationService
from ..dto.budget_post_dto import BudgetPostUpdateDTO
from ...shared.services.cache_service import CacheService
from ...shared.services.audit_service import AuditService
from ...shared.utils.request_utils import get_request_info
from ...helpers import check_edit_permission_for_scheme, validate_access_control
from src.utils_timing import check_data_filling_allowed
from src.schemes.common.post_levels.api_router import create_post_levels_router
from src.utils_auth import get_auth_level, get_auth_role, get_auth_unit, get_auth_user

from src.utils_auth import verify_api_auth
from src.core.taluka.write import resolve_editable_row
from src.core.taluka.consolidation import consolidate_row
from src.core.taluka.models import natural_key_columns

router = APIRouter(
    prefix="/ui/s20530028/budget-post-details",
    tags=["API - Budget Post Details"],
    include_in_schema=False,
    dependencies=[Depends(verify_api_auth)]
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
    table_name="budget_post_details_20530028",
    scheme_code=SCHEME_CONFIG.code,
    access_validator=validate_budget_post_access,
    prefix="/api/post-levels"
)
router.include_router(post_levels_router)


def get_budget_post_service(db: Session = Depends(get_db)) -> BudgetPostService:
    """Dependency to get budget post service"""
    repository = BudgetPostRepository(db)
    return BudgetPostService(repository)


def get_pay_matrix_service(db: Session = Depends(get_db)) -> PayMatrixService:
    """Dependency to get pay matrix service"""
    return PayMatrixService(db)


@router.get("/api/pay-matrix/stages", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_get_pay_matrix_stages(
    service: PayMatrixService = Depends(get_pay_matrix_service)
):
    """Get all pay matrix stages"""
    try:
        stages = service.get_stages()
        return JSONResponse({"stages": stages})
    except ConnectionError as e:
        import logging
        logging.error(f"Connection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database connection error. Please try again.")


@router.get("/api/pay-matrix/levels/{stage}", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_get_pay_matrix_levels(
    stage: str,
    service: PayMatrixService = Depends(get_pay_matrix_service)
):
    """Get pay matrix levels for a stage"""
    try:
        levels = service.get_levels(stage)
        return JSONResponse({"levels": levels})
    except ConnectionError as e:
        import logging
        logging.error(f"Connection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database connection error. Please try again.")


@router.get("/api/pay-matrix/basic-pay", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_get_pay_matrix_basic_pay(
    request: Request,
    stage: str = Query(...),
    level: int = Query(...),
    service: PayMatrixService = Depends(get_pay_matrix_service),
    db: Session = Depends(get_db)
):
    """Get basic pay for stage and level, respecting salary mode"""
    from src.utils_salary_mode import get_salary_mode
    fiscal_year = get_fiscal_year_from_request(request, db)
    salary_mode = get_salary_mode(db, fiscal_year)
    result = service.get_basic_pay(stage, level, salary_mode)
    if not result:
        return JSONResponse({"found": False, "basic_pay": 0})
    return JSONResponse(result)

@router.get("/api/da-rate", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_get_da_rate(request: Request, db: Session = Depends(get_db)):
    """Return current DA rate for the active fiscal year"""
    from src.utils_da_rate import get_da_percentage, get_da_rate
    fiscal_year = get_fiscal_year_from_request(request, db)
    da_percentage = get_da_percentage(db, fiscal_year)
    da_rate = get_da_rate(db, fiscal_year)
    return JSONResponse({
        "fiscal_year": fiscal_year,
        "da_percentage": float(da_percentage),
        "da_rate": da_rate
    })


@router.get("/api/designations", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_get_designations(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    service: BudgetPostService = Depends(get_budget_post_service)
):
    """Get distinct designations matching filters"""
    try:
        db = service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        designations = service.get_designations(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            category=category,
            class_type=cls
        )
        return JSONResponse({"designations": designations})
    except ConnectionError as e:
        import logging
        logging.error(f"Connection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database connection error. Please try again.")
    except Exception as e:
        import logging
        logging.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/api/record-data", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_get_record_data(
    request: Request,
    district: str = Query(...),
    category: str = Query(...),
    cls: str = Query(..., alias="class"),
    designation: str = Query(...),
    service: BudgetPostService = Depends(get_budget_post_service)
):
    """Get record data for a specific budget post detail"""
    try:
        db = service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        record_dto = service.get_record_data(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            category=category,
            class_type=cls,
            designation=designation
        )
        return JSONResponse(record_dto.model_dump())
    except ConnectionError as e:
        import logging
        logging.error(f"Connection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database connection error. Please try again.")
    except Exception as e:
        import logging
        logging.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/api/update-inline", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_update_inline(
    request: Request,
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
    HraRate: str = Form('X'),
    service: BudgetPostService = Depends(get_budget_post_service)
):
    """Update budget post detail inline"""
    # Permission checks
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_user = get_auth_user(request)
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, service.repository.db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    db = service.repository.session
    is_allowed, timing_msg = check_data_filling_allowed(
        db, auth_level, auth_role, SCHEME_CONFIG.code
    )
    if not is_allowed:
        return JSONResponse(
            {"success": False, "message": timing_msg or "Data filling period expired"},
            status_code=403
        )
    
    try:
        _, sub_scheme = get_scheme_from_cookies(request)
        
        # Get record for access control check
        record = resolve_editable_row(db, BudgetPostDetails, id, request)
        if record.sub_scheme_code != sub_scheme:
            return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
        
        from src.schemes.common.post_levels.repository import PostLevelRepository
        post_level_repo = PostLevelRepository(db)
        fiscal_year = get_fiscal_year_from_request(request, db)
        current_level_count = post_level_repo.get_count(
            record.id, sub_scheme, "budget_post_details_20530028", fiscal_year
        )
        if SanctionedPostsCurr < current_level_count:
            return JSONResponse({
                "success": False,
                "message": f"मंजूर पदे {SanctionedPostsCurr} पेक्षा {current_level_count} स्तर आधीच अस्तित्वात आहेत. कृपया प्रथम स्तर हटवा."
            }, status_code=400)
        
        # Create update DTO
        update_dto = BudgetPostUpdateDTO(
            id=record.id,
            sanctioned_posts_prev1=SanctionedPostsPrev1,
            sanctioned_posts_curr=SanctionedPostsCurr,
            special_pay=SpecialPay,
            basic_pay=BasicPay,
            grade_pay=GradePay,
            local_supplementary_allowance=LocalSupplemetoryAllowance,
            vehicle_allowance=VehicleAllowance,
            washing_allowance=WashingAllowance,
            cash_allowance=CashAllowance,
            footwear_allowance_other=FootWareAllowanceOther,
            hra_rate=HraRate
        )
        
        # Update record
        result = service.update_inline(update_dto, sub_scheme)
        if result.get("success"):
            db.flush()
            consolidate_row(db, BudgetPostDetails, record.district, record.fiscal_year,
                            {c: getattr(record, c) for c in natural_key_columns(BudgetPostDetails)})
            db.commit()
        
        # Invalidate cache
        CacheService.invalidate_scheme_cache(record.district)
        
        # Log audit
        req_info = get_request_info(request)
        AuditService.log_audit_async(
            "budget_post_details",
            id,
            auth_user,
            result["old_values"],
            result["new_values"],
            req_info
        )
        
        return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except ValueError as e:
        return JSONResponse({"success": False, "message": "Invalid input data"}, status_code=400)
    except ConnectionError as e:
        import logging; logging.error("update_inline_conn_err: %s", e)
        return JSONResponse({"success": False, "message": "Database error"}, status_code=500)
    except Exception as e:
        import logging; logging.error("update_inline_err: %s", e, exc_info=True)
        return JSONResponse({"success": False, "message": "An internal error occurred"}, status_code=500)
