from fastapi import APIRouter, Depends, HTTPException, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.database import get_db
from src import models
from src.utils_timing import invalidate_timing_cache
from src.utils_scheme import get_scheme_base_template
from datetime import datetime
import logging

router = APIRouter(prefix="/timing", tags=["Timing Management"], include_in_schema=False)

templates = Jinja2Templates(directory="templates")


def is_dco_assistant(request: Request) -> bool:
    auth_level = request.cookies.get('auth_level', '')
    auth_role = request.cookies.get('auth_role', '')
    return auth_level == 'dco' and auth_role == 'assistant'


@router.get("/manage", response_class=HTMLResponse)
async def timing_management_page(request: Request, db: Session = Depends(get_db)):
    if not is_dco_assistant(request):
        raise HTTPException(status_code=403, detail="Access denied")
    
    periods = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.is_active == True
    ).order_by(models.DataFillingPeriod.created_at.desc()).all()
    
    return templates.TemplateResponse("timing_management.html", {
        "request": request,
        "periods": periods,
        "auth_level": "dco",
        "auth_role": "assistant",
        "resource_name": "डेटा भरण कालावधी व्यवस्थापन",
        "base_template": get_scheme_base_template(request)
    })


@router.post("/set", response_class=JSONResponse)
async def set_timing(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    level: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...)
):
    if not is_dco_assistant(request):
        raise HTTPException(status_code=403, detail="Access denied")
    
    auth_user = request.cookies.get('auth_user', '')
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    now = datetime.now()
    if start_dt < now:
        raise HTTPException(status_code=400, detail="Start date cannot be before current time")
    
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    if level not in ['district', 'taluka', 'both']:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.level == level,
        models.DataFillingPeriod.is_active == True
    ).update({"is_active": False})
    
    new_period = models.DataFillingPeriod(
        level=level,
        start_date=start_dt,
        end_date=end_dt,
        is_active=True,
        created_by=auth_user
    )
    
    db.add(new_period)
    db.commit()
    invalidate_timing_cache()
    
    try:
        from src.notification_service import send_data_filling_period_alert
        background_tasks.add_task(send_data_filling_period_alert, None, new_period, 'created')
    except Exception as e:
        logging.error(f"Failed to queue email alert for timing period: {e}", exc_info=True)
    
    return JSONResponse({
        "success": True,
        "message": "Timing set successfully",
        "period_id": new_period.id
    })


@router.post("/update/{period_id}", response_class=JSONResponse)
async def update_timing(
    request: Request,
    background_tasks: BackgroundTasks,
    period_id: int,
    db: Session = Depends(get_db),
    start_date: str = Form(...),
    end_date: str = Form(...)
):
    if not is_dco_assistant(request):
        raise HTTPException(status_code=403, detail="Access denied")
    
    period = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.id == period_id
    ).first()
    
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    now = datetime.now()
    if end_dt <= now:
        raise HTTPException(status_code=400, detail="End date must be in the future")
    
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    period.start_date = start_dt
    period.end_date = end_dt
    period.updated_at = datetime.now()
    
    db.commit()
    invalidate_timing_cache()
    
    try:
        from src.notification_service import send_data_filling_period_alert
        background_tasks.add_task(send_data_filling_period_alert, None, period, 'updated')
    except Exception as e:
        logging.error(f"Failed to queue email alert for timing period update: {e}", exc_info=True)
    
    return JSONResponse({
        "success": True,
        "message": "Timing updated successfully"
    })


@router.post("/delete/{period_id}", response_class=JSONResponse)
async def delete_timing(
    request: Request,
    period_id: int,
    db: Session = Depends(get_db)
):
    if not is_dco_assistant(request):
        raise HTTPException(status_code=403, detail="Access denied")
    
    period = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.id == period_id
    ).first()
    
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    period.is_active = False
    db.commit()
    invalidate_timing_cache()
    
    return JSONResponse({
        "success": True,
        "message": "Period deactivated successfully"
    })


@router.get("/check", response_class=JSONResponse)
async def check_timing_status(request: Request, db: Session = Depends(get_db)):
    from src.utils_timing import check_data_filling_allowed
    
    auth_level = request.cookies.get('auth_level', '')
    auth_role = request.cookies.get('auth_role', '')
    
    allowed, message = check_data_filling_allowed(db, auth_level, auth_role)
    return JSONResponse({"allowed": allowed, "message": message or ""})

