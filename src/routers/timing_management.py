from fastapi import APIRouter, Depends, HTTPException, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

_IST = ZoneInfo("Asia/Kolkata")


def _now_ist() -> datetime:
    """Return current time as IST-naive datetime (matches TIMESTAMP WITHOUT TIME ZONE columns)."""
    return datetime.now(_IST).replace(tzinfo=None)

from src.database import get_db
from src import models
from src.core.templates import render
from src.core.registry import scheme_registry
from src.utils_timing import invalidate_timing_cache
from src.utils_scheme import get_scheme_base_template
from src.utils_auth import get_auth_level, get_auth_role, get_auth_user
import re

router = APIRouter(prefix="/ui/s{scheme_code}/timing-management", tags=["Timing Management"], include_in_schema=False)

logger = logging.getLogger(__name__)

_SCHEME_CODE_RE = re.compile(r'^[0-9]{4,8}$')


def _require_dco_assistant(request: Request) -> None:
    if get_auth_level(request) != 'dco' or get_auth_role(request) != 'assistant':
        raise HTTPException(status_code=403, detail="Access denied")


def _validate_scheme(scheme_code: str) -> None:
    if not _SCHEME_CODE_RE.match(scheme_code):
        raise HTTPException(status_code=400, detail="Invalid scheme code")
    if not scheme_registry.get_scheme(scheme_code):
        raise HTTPException(status_code=404, detail="Scheme not found")


@router.get("", response_class=HTMLResponse)
async def timing_management_page(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    _require_dco_assistant(request)
    _validate_scheme(scheme_code)

    periods = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.is_active == True,
        models.DataFillingPeriod.sub_scheme_code == scheme_code
    ).order_by(models.DataFillingPeriod.created_at.desc()).all()

    return render(request, "timing_management.html", {
        "periods": periods,
        "auth_level": "dco",
        "auth_role": "assistant",
        "resource_name": "डेटा भरण कालावधी व्यवस्थापन",
        "base_template": get_scheme_base_template(request),
        "scheme_code": scheme_code
    })


@router.post("/set", response_class=JSONResponse)
async def set_timing(
    request: Request,
    scheme_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    level: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...)
):
    _require_dco_assistant(request)
    _validate_scheme(scheme_code)

    auth_user = get_auth_user(request)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    now = _now_ist()
    if start_dt < now:
        raise HTTPException(status_code=400, detail="Start date cannot be before current time")

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    if level not in ('district', 'taluka', 'both'):
        raise HTTPException(status_code=400, detail="Invalid level")

    try:
        db.query(models.DataFillingPeriod).filter(
            models.DataFillingPeriod.level == level,
            models.DataFillingPeriod.sub_scheme_code == scheme_code,
            models.DataFillingPeriod.is_active == True
        ).update({"is_active": False})

        new_period = models.DataFillingPeriod(
            sub_scheme_code=scheme_code,
            level=level,
            start_date=start_dt,
            end_date=end_dt,
            is_active=True,
            created_by=auth_user
        )
        db.add(new_period)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("timing_set_failed scheme=%s user=%s level=%s", scheme_code, auth_user, level, exc_info=True)
        raise HTTPException(status_code=500, detail="डेटाबेस त्रुटी")

    logger.info("timing_set scheme=%s user=%s level=%s period_id=%s", scheme_code, auth_user, level, new_period.id)
    invalidate_timing_cache(scheme_code)

    try:
        from src.notification_service import send_data_filling_period_alert
        background_tasks.add_task(send_data_filling_period_alert, None, new_period, 'created')
    except Exception as e:
        logger.error("timing_alert_queue_failed scheme=%s: %s", scheme_code, e, exc_info=True)

    return JSONResponse({
        "success": True,
        "message": "Timing set successfully",
        "period_id": new_period.id
    })


@router.post("/update/{period_id}", response_class=JSONResponse)
async def update_timing(
    request: Request,
    scheme_code: str,
    background_tasks: BackgroundTasks,
    period_id: int,
    db: Session = Depends(get_db),
    start_date: str = Form(...),
    end_date: str = Form(...)
):
    _require_dco_assistant(request)
    _validate_scheme(scheme_code)

    period = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.id == period_id,
        models.DataFillingPeriod.sub_scheme_code == scheme_code
    ).first()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    now = _now_ist()
    if end_dt <= now:
        raise HTTPException(status_code=400, detail="End date must be in the future")

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    period.start_date = start_dt
    period.end_date = end_dt
    period.updated_at = _now_ist()

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("timing_update_failed scheme=%s period_id=%s", scheme_code, period_id, exc_info=True)
        raise HTTPException(status_code=500, detail="डेटाबेस त्रुटी")

    auth_user = get_auth_user(request)
    logger.info("timing_update scheme=%s period_id=%s user=%s", scheme_code, period_id, auth_user)
    invalidate_timing_cache(scheme_code)

    try:
        from src.notification_service import send_data_filling_period_alert
        background_tasks.add_task(send_data_filling_period_alert, None, period, 'updated')
    except Exception as e:
        logger.error("timing_alert_queue_failed scheme=%s period_id=%s: %s", scheme_code, period_id, e, exc_info=True)

    return JSONResponse({
        "success": True,
        "message": "Timing updated successfully"
    })


@router.post("/delete/{period_id}", response_class=JSONResponse)
async def delete_timing(
    request: Request,
    scheme_code: str,
    period_id: int,
    db: Session = Depends(get_db)
):
    _require_dco_assistant(request)
    _validate_scheme(scheme_code)

    period = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.id == period_id,
        models.DataFillingPeriod.sub_scheme_code == scheme_code
    ).first()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    period.is_active = False

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("timing_delete_failed scheme=%s period_id=%s", scheme_code, period_id, exc_info=True)
        raise HTTPException(status_code=500, detail="डेटाबेस त्रुटी")

    auth_user = get_auth_user(request)
    logger.info("timing_delete scheme=%s period_id=%s user=%s", scheme_code, period_id, auth_user)
    invalidate_timing_cache(scheme_code)

    return JSONResponse({
        "success": True,
        "message": "Period deactivated successfully"
    })


@router.get("/check", response_class=JSONResponse)
async def check_timing_status(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    from src.utils_timing import check_data_filling_allowed

    auth_level = get_auth_level(request)
    auth_role = get_auth_role(request)

    allowed, message = check_data_filling_allowed(db, auth_level, auth_role, scheme_code)
    return JSONResponse({"allowed": allowed, "message": message or ""})
