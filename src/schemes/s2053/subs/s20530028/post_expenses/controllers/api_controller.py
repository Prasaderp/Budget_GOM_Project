"""API controller for post expenses"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from ...config import SCHEME_CONFIG
from ..repositories.post_expenses_repository import PostExpensesRepository
from ..services.post_expenses_service import PostExpensesService
from ..dto.post_expenses_dto import PostExpensesUpdateDTO
from ...shared.services.cache_service import CacheService
from ...shared.services.audit_service import AuditService
from ...shared.utils.request_utils import get_request_info
from ...helpers import check_edit_permission_for_scheme
from src.utils_timing import check_data_filling_allowed
from src.utils_auth import (
    get_auth_level,
    get_auth_role,
    get_auth_unit,
    get_auth_user,
    verify_api_auth,
)
from src.core.taluka.write import resolve_editable_row, writable_scope
from src.core.taluka.consolidation import consolidate_row
from src.core.taluka.models import natural_key_columns
from ...models import PostExpenses
from ...derivation import acquire_derivation_locks, derive_for_row

router = APIRouter(
    prefix="/ui/s20530028/post-expenses",
    tags=["API - Post Expenses"],
    include_in_schema=False,
    dependencies=[Depends(verify_api_auth)],
)


def get_post_expenses_service(db: Session = Depends(get_db)) -> PostExpensesService:
    """Dependency to get post expenses service"""
    repository = PostExpensesRepository(db)
    return PostExpensesService(repository)


@router.get(
    "/api/classes", response_class=JSONResponse, dependencies=[Depends(verify_api_auth)]
)
async def api_get_classes(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    service: PostExpensesService = Depends(get_post_expenses_service),
):
    """Get distinct classes matching filters"""
    try:
        db = service.repository.session
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        classes = service.get_classes(
            fiscal_year=fiscal_year,
            sub_scheme_code=sub_scheme,
            district=district,
            category=category,
        )
        return JSONResponse({"classes": classes})
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
    category: str = Query(...),
    cls: str = Query(..., alias="class"),
    service: PostExpensesService = Depends(get_post_expenses_service),
):
    """Get record data for a specific post expense"""
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
    FilledPosts: int = Form(0),
    VacantPosts: int = Form(0),
    MedicalExpenses: int = Form(0),
    FestivalAdvance: int = Form(0),
    SwagramMaharashtraDarshan: int = Form(0),
    NPSUnified: int = Form(0),
    Other: int = Form(0),
    service: PostExpensesService = Depends(get_post_expenses_service),
):
    """Update post expense inline"""
    # Permission checks
    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_user = get_auth_user(request)

    db = service.repository.session
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)

    is_allowed, timing_msg = check_data_filling_allowed(
        db, auth_level, auth_role, SCHEME_CONFIG.code
    )
    if not is_allowed:
        return JSONResponse(
            {"success": False, "message": timing_msg or "Data filling period expired"},
            status_code=403,
        )

    try:
        _, sub_scheme = get_scheme_from_cookies(request)

        # Get record for access control check
        record = resolve_editable_row(db, PostExpenses, id, request)
        if record.sub_scheme_code != sub_scheme:
            return JSONResponse(
                {"success": False, "message": "Record not found"}, status_code=404
            )
        acquire_derivation_locks(
            db, record.district, record.fiscal_year, record.category
        )

        # Create update DTO
        update_dto = PostExpensesUpdateDTO(
            id=record.id,
            filled_posts=FilledPosts,
            vacant_posts=VacantPosts,
            medical_expenses=MedicalExpenses,
            festival_advance=FestivalAdvance,
            swagram_maharashtra_darshan=SwagramMaharashtraDarshan,
            nps_unified=float(NPSUnified),
            other=Other,
        )

        # Update record. writable_scope() pins the read filter to the
        # resolved row's own taluka so the service's internal re-query by id
        # finds it (C2). update_inline() raises on any failure, so reaching
        # this point always means success -- there is no "success" key to
        # gate on (it never returns one), so consolidation must run
        # unconditionally or it silently never runs (matches the C4 class of
        # defect: the district total goes stale after every inline edit).
        with writable_scope(record):
            result = service.update_inline(update_dto, sub_scheme)
        db.flush()
        consolidate_row(
            db,
            PostExpenses,
            record.district,
            record.fiscal_year,
            {c: getattr(record, c) for c in natural_key_columns(PostExpenses)},
        )
        derive_for_row(db, record, request)
        db.commit()

        # Invalidate cache
        CacheService.invalidate_scheme_cache(record.district)

        # Log audit
        req_info = get_request_info(request)
        AuditService.log_audit_async(
            "post_expenses",
            id,
            auth_user,
            result["old_values"],
            result["new_values"],
            req_info,
        )

        return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})
    except HTTPException as e:
        db.rollback()
        return JSONResponse(
            {"success": False, "message": e.detail}, status_code=e.status_code
        )
    except ValueError as e:
        db.rollback()
        return JSONResponse(
            {"success": False, "message": str(e)}, status_code=400
        )
    except ConnectionError as e:
        import logging

        db.rollback()
        logging.error("update_inline_conn_err: %s", e)
        return JSONResponse(
            {"success": False, "message": "Database error"}, status_code=500
        )
    except Exception as e:
        import logging

        db.rollback()
        logging.error("update_inline_err: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "message": "An internal error occurred"}, status_code=500
        )
