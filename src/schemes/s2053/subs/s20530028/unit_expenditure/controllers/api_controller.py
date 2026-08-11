"""API controller for unit expenditure"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from src.utils_cache import memory_cache

from src.database import get_db
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from ..repositories.unit_expenditure_repository import UnitExpenditureRepository
from ..services.unit_expenditure_service import UnitExpenditureService
from ..dto.unit_expenditure_dto import UnitExpenditureInlineUpdateDTO
from src.utils_auth import get_auth_level, get_auth_role, get_auth_unit, get_auth_user

from src.utils_auth import verify_api_auth
from src.core.taluka.write import resolve_editable_row, writable_scope
from src.core.taluka.consolidation import consolidate_row
from src.core.taluka.models import natural_key_columns
from ..utils.formatters import get_internal_data_keys
from ...helpers import invalidate_scheme_cache, log_audit_async, get_request_info
from ...models import UnitExpenditure

router = APIRouter(
    prefix="/ui/s20530028/unit-expenditure",
    tags=["API - Unit Expenditure"],
    include_in_schema=False,
    dependencies=[Depends(verify_api_auth)],
)

_CACHE_TTL = 300


def _make_cache_key(prefix: str, *args) -> str:
    """Generate cache key"""
    return f"{prefix}|{'|'.join(str(a) for a in args)}"


def get_unit_expenditure_service(
    db: Session = Depends(get_db),
) -> UnitExpenditureService:
    """Dependency to get unit expenditure service"""
    repository = UnitExpenditureRepository(db)
    return UnitExpenditureService(repository)


@router.get(
    "/api/primary-units",
    response_class=JSONResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def api_get_primary_units(
    request: Request,
    district: Optional[str] = Query(None),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service),
):
    """Get distinct primary units matching filters"""
    try:
        db = service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)

        cache_key = _make_cache_key("primary_units", district or "all", fiscal_year)
        cached = memory_cache.get(cache_key)
        if cached:
            return JSONResponse(cached)

        units = service.get_primary_units(
            fiscal_year=fiscal_year, sub_scheme_code=sub_scheme, district=district
        )
        result = {"units": units}
        memory_cache.set(cache_key, result, _CACHE_TTL)
        return JSONResponse(result)
    except ConnectionError as e:
        import logging

        logging.error(f"Connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Database connection error. Please try again."
        )
    except Exception as e:
        import logging

        logging.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.get(
    "/api/record-data",
    response_class=JSONResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def api_get_record_data(
    request: Request,
    district: str = Query(...),
    primary_unit: str = Query(...),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service),
):
    """Get record data for a specific unit expenditure"""
    try:
        db = service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        record_dto = service.get_record_data(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            primary_unit=primary_unit,
        )
        return JSONResponse(record_dto.model_dump())
    except ConnectionError as e:
        import logging

        logging.error(f"Connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Database connection error. Please try again."
        )
    except Exception as e:
        import logging

        logging.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@router.post(
    "/api/update-inline",
    response_class=JSONResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def api_update_inline(
    request: Request,
    id: int = Form(...),
    ExpenditurePrev4: int = Form(0),
    ExpenditurePrev3: int = Form(0),
    ExpenditurePrev2: int = Form(0),
    BudgetPrev1: int = Form(0),
    ForecastPrev1: int = Form(0),
    BudgetCurrEstimatingOfficer: int = Form(0),
    BudgetCurrControllingOfficer: int = Form(0),
    BudgetCurrAdminDept: int = Form(0),
    BudgetCurrFinanceDept: int = Form(0),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service),
):
    """Update unit expenditure inline"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_user = get_auth_user(request)

    try:
        _, sub_scheme = get_scheme_from_cookies(request)
        db = service.repository.session
        record = resolve_editable_row(db, UnitExpenditure, id, request)
        if record.sub_scheme_code != sub_scheme:
            return JSONResponse(
                {"success": False, "message": "Record not found"}, status_code=404
            )

        # Create update DTO
        update_dto = UnitExpenditureInlineUpdateDTO(
            id=record.id,
            expenditure_prev4=ExpenditurePrev4,
            expenditure_prev3=ExpenditurePrev3,
            expenditure_prev2=ExpenditurePrev2,
            budget_prev1=BudgetPrev1,
            forecast_prev1=ForecastPrev1,
            budget_curr_estimating_officer=BudgetCurrEstimatingOfficer,
            budget_curr_controlling_officer=BudgetCurrControllingOfficer,
            budget_curr_admin_dept=BudgetCurrAdminDept,
            budget_curr_finance_dept=BudgetCurrFinanceDept,
        )
        audit_keys = get_internal_data_keys()
        old_values = {key: getattr(record, key) for key in audit_keys}

        # Update record. writable_scope() pins the read filter to the
        # resolved row's own taluka so the service's internal re-query by id
        # finds it (C2).
        with writable_scope(record):
            result = service.update_inline(
                update_dto=update_dto,
                sub_scheme_code=sub_scheme,
                auth_role=auth_role,
                auth_level=auth_level,
                auth_unit=auth_unit,
            )
        if result.get("success"):
            db.flush()
            consolidate_row(
                db,
                UnitExpenditure,
                record.district,
                record.fiscal_year,
                {c: getattr(record, c) for c in natural_key_columns(UnitExpenditure)},
            )
            db.commit()
            invalidate_scheme_cache(
                record.district, patterns=["unit_exp_summary", "unit_exp_charts"]
            )
            log_audit_async(
                "unit_expenditure",
                id,
                auth_user,
                old_values,
                {key: getattr(record, key) for key in audit_keys},
                get_request_info(request),
            )

        response_status = result.pop("status_code", 200)
        return JSONResponse(result, status_code=response_status)
    except HTTPException as e:
        return JSONResponse(
            {"success": False, "message": e.detail}, status_code=e.status_code
        )
    except ValueError:
        return JSONResponse(
            {"success": False, "message": "Invalid input data"}, status_code=400
        )
    except ConnectionError as e:
        import logging

        logging.error("update_inline_conn_err: %s", e)
        return JSONResponse(
            {"success": False, "message": "Database error"}, status_code=500
        )
    except Exception as e:
        import logging

        logging.error("update_inline_err: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "message": "An internal error occurred"}, status_code=500
        )
