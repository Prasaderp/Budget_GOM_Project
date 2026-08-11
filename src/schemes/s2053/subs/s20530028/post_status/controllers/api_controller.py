"""API routes for Post Status - sub-scheme 20530028"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from ..services.post_status_service import PostStatusService
from ..dto.post_status_dto import PostStatusUpdateDTO
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
from ...models import PostStatus

router = APIRouter(
    prefix="/ui/s20530028/post-status",
    tags=["API - Post Status"],
    include_in_schema=False,
    dependencies=[Depends(verify_api_auth)],
)


def get_post_status_service(db: Session = Depends(get_db)) -> PostStatusService:
    """Dependency to get PostStatusService"""
    return PostStatusService(db)


@router.get(
    "/api/statuses",
    response_class=JSONResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def api_get_statuses(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    service: PostStatusService = Depends(get_post_status_service),
):
    """Get distinct statuses matching filters"""
    db = service.db
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)

    statuses = service.get_statuses(fiscal_year, sub_scheme, district, category, cls)
    return JSONResponse({"statuses": statuses})


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
    status: str = Query(...),
    service: PostStatusService = Depends(get_post_status_service),
):
    """Get record data by natural key"""
    db = service.db
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)

    record_dto = service.get_record_data(
        fiscal_year, sub_scheme, district, category, cls, status
    )
    return JSONResponse(record_dto.model_dump())


@router.post(
    "/api/update-inline",
    response_class=JSONResponse,
    dependencies=[Depends(verify_api_auth)],
)
async def api_update_inline(
    request: Request,
    id: int = Form(...),
    Posts: int = Form(0),
    Salary: int = Form(0),
    GradePay: int = Form(0),
    SpecialPay: int = Form(0),
    DearnessAllowance: int = Form(0),
    LocalSupplemetoryAllowance: int = Form(0),
    HouseRentAllowance: int = Form(0),
    TravelAllowance: int = Form(0),
    Other: int = Form(0),
    service: PostStatusService = Depends(get_post_status_service),
):
    """Update post status record inline"""
    db = service.db
    _, sub_scheme = get_scheme_from_cookies(request)

    auth_role = get_auth_role(request)
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)
    auth_user = get_auth_user(request)
    try:
        record = resolve_editable_row(db, PostStatus, id, request)
    except HTTPException as e:
        return JSONResponse(
            {"success": False, "message": e.detail}, status_code=e.status_code
        )
    if record.sub_scheme_code != sub_scheme:
        return JSONResponse(
            {"success": False, "message": "Record not found"}, status_code=404
        )

    update_dto = PostStatusUpdateDTO(
        posts=Posts,
        salary=Salary,
        grade_pay=GradePay,
        special_pay=SpecialPay,
        dearness_allowance=DearnessAllowance,
        local_supplementary_allowance=LocalSupplemetoryAllowance,
        house_rent_allowance=HouseRentAllowance,
        travel_allowance=TravelAllowance,
        other=Other,
    )

    # writable_scope() pins the read filter to the resolved row's own
    # taluka so the service's internal re-query by id finds it (C2).
    with writable_scope(record):
        result = service.update_inline(
            record.id,
            sub_scheme,
            update_dto,
            auth_role,
            auth_level,
            auth_unit,
            auth_user,
            request,
        )

    if not result.get("success"):
        status_code = 403 if result.get("message") == "Forbidden" else 400
        return JSONResponse(result, status_code=status_code)
    try:
        db.flush()
        consolidate_row(
            db,
            PostStatus,
            record.district,
            record.fiscal_year,
            {c: getattr(record, c) for c in natural_key_columns(PostStatus)},
        )
        db.commit()
    except HTTPException as e:
        db.rollback()
        return JSONResponse(
            {"success": False, "message": e.detail}, status_code=e.status_code
        )

    return JSONResponse(result)
