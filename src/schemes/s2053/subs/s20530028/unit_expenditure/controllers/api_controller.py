"""API controller for unit expenditure"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from src.utils_cache import memory_cache

from src.database import get_db
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from ...config import SCHEME_CONFIG
from ..repositories.unit_expenditure_repository import UnitExpenditureRepository
from ..services.unit_expenditure_service import UnitExpenditureService
from ..dto.unit_expenditure_dto import UnitExpenditureInlineUpdateDTO
from src.utils_auth import get_auth_level, get_auth_role, get_auth_unit, get_auth_user

from src.utils_auth import verify_api_auth

router = APIRouter(
    prefix="/ui/s20530028/unit-expenditure",
    tags=["API - Unit Expenditure"],
    include_in_schema=False,
    dependencies=[Depends(verify_api_auth)]
)

_CACHE_TTL = 300


def _make_cache_key(prefix: str, *args) -> str:
    """Generate cache key"""
    return f"{prefix}|{'|'.join(str(a) for a in args)}"


def get_unit_expenditure_service(db: Session = Depends(get_db)) -> UnitExpenditureService:
    """Dependency to get unit expenditure service"""
    repository = UnitExpenditureRepository(db)
    return UnitExpenditureService(repository)


@router.get("/api/primary-units", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)])
async def api_get_primary_units(
    request: Request,
    district: Optional[str] = Query(None),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service)
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
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district
        )
        result = {"units": units}
        memory_cache.set(cache_key, result, _CACHE_TTL)
        return JSONResponse(result)
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
    primary_unit: str = Query(...),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service)
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
            primary_unit=primary_unit
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
    Expenditure202122: int = Form(0),
    Expenditure202223: int = Form(0),
    Expenditure202324: int = Form(0),
    Budget202425: int = Form(0),
    Forecast202425: int = Form(0),
    Budget202526EstimatingOfficer: int = Form(0),
    Budget202526ControllingOfficer: int = Form(0),
    Budget202526AdminDept: int = Form(0),
    Budget202526FinanceDept: int = Form(0),
    service: UnitExpenditureService = Depends(get_unit_expenditure_service)
):
    """Update unit expenditure inline"""
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_user = get_auth_user(request)
    
    try:
        _, sub_scheme = get_scheme_from_cookies(request)
        
        # Create update DTO
        update_dto = UnitExpenditureInlineUpdateDTO(
            id=id,
            expenditure_2021_22=Expenditure202122,
            expenditure_2022_23=Expenditure202223,
            expenditure_2023_24=Expenditure202324,
            budget_2024_25=Budget202425,
            forecast_2024_25=Forecast202425,
            budget_2025_26_estimating_officer=Budget202526EstimatingOfficer,
            budget_2025_26_controlling_officer=Budget202526ControllingOfficer,
            budget_2025_26_admin_dept=Budget202526AdminDept,
            budget_2025_26_finance_dept=Budget202526FinanceDept
        )
        
        # Update record
        result = service.update_inline(
            request=request,
            update_dto=update_dto,
            sub_scheme_code=sub_scheme,
            auth_role=auth_role,
            auth_level=auth_level,
            auth_unit=auth_unit,
            auth_user=auth_user
        )
        
        return JSONResponse(result)
    except ValueError as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=400)
    except ConnectionError as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

