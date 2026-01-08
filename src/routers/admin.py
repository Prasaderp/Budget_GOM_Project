"""Admin router - Secure and optimized"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import io
import re

from src.database import get_db
from src.core.templates import templates
from src import models
from src.utils_auth import is_admin, get_admin_user

router = APIRouter(prefix="/admin", tags=["Admin"], include_in_schema=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Validation
_SAFE_INPUT = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
_VALID_ROLES = frozenset({'dco', 'officer1', 'officer2', 'assistant'})

def _sanitize(val: str, max_len: int = 50) -> str:
    """Sanitize input string"""
    if not val or not isinstance(val, str):
        return ""
    val = val.strip()[:max_len]
    return val if _SAFE_INPUT.match(val) else ""


def _require_admin(request: Request):
    """Check admin auth, raise or redirect if not"""
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Unauthorized")


# Pre-computed dummy hash for timing attack prevention
_DUMMY_HASH = pwd_context.hash("dummy_password")


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "auth_level": "admin"})


@router.post("/login")
async def admin_login(request: Request, db: Session = Depends(get_db)):
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            data = await request.json()
            username = _sanitize(data.get("username", ""))
            password = (data.get("password") or "")[:128]
        else:
            form = await request.form()
            username = _sanitize(form.get("username", ""))
            password = (form.get("password") or "")[:128]
        
        if not username or not password or len(password) < 4:
            pwd_context.verify("x", _DUMMY_HASH)  # Timing protection
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        admin = db.query(models.AdminUser.username, models.AdminUser.password_hash)\
                 .filter(models.AdminUser.username == username).first()
        
        if not admin:
            pwd_context.verify("x", _DUMMY_HASH)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not pwd_context.verify(password, admin.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        resp = RedirectResponse(url="/admin/users", status_code=303)
        resp.set_cookie("admin_user", admin.username, httponly=True, samesite="lax", max_age=86400)
        return resp
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def admin_logout():
    resp = JSONResponse({"message": "ok"})
    resp.delete_cookie("admin_user", path="/", httponly=True)
    return resp


@router.get("/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    
    role_filter = request.query_params.get('role', '').strip()
    if role_filter and role_filter not in _VALID_ROLES:
        role_filter = ""
    
    updated_user = _sanitize(request.query_params.get('updated', ''))
    
    try:
        query = db.query(
            models.User.id, models.User.username, models.User.role,
            models.User.level, models.User.unit, models.User.is_active
        ).filter(
            (models.User.level != 'taluka') | (models.User.is_active == True)
        ).order_by(models.User.id.asc())
        
        if role_filter:
            query = query.filter(models.User.role == role_filter)
        
        users = [{'id': u.id, 'username': u.username, 'role': u.role, 'level': u.level, 'unit': u.unit or '-'} 
                 for u in query.all()]
        
        return templates.TemplateResponse("admin_users.html", {
            "request": request, "users": users, "roles": list(_VALID_ROLES),
            "current_role": role_filter, "updated_user": updated_user, "auth_level": "admin"
        })
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=303)


@router.post("/users/update")
async def admin_update_user(request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    
    try:
        form = await request.form()
        
        try:
            user_id = int(form.get("id") or "0")
            if user_id <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID")
        
        new_username = _sanitize(form.get("username", ""))
        new_password = (form.get("password") or "").strip()[:128]
        
        if not new_username and not new_password:
            return RedirectResponse(url="/admin/users", status_code=303)
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        changes = False
        
        if new_username and new_username != user.username:
            if len(new_username) < 3:
                raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
            
            from sqlalchemy import exists
            if db.query(exists().where(models.User.username == new_username, models.User.id != user_id)).scalar():
                raise HTTPException(status_code=400, detail="Username already taken")
            
            old = user.username
            user.username = new_username
            
            # Update references in messages
            db.query(models.Message).filter(models.Message.from_username == old)\
              .update({models.Message.from_username: new_username}, synchronize_session=False)
            db.query(models.Message).filter(models.Message.to_username == old)\
              .update({models.Message.to_username: new_username}, synchronize_session=False)
            changes = True
        
        if new_password:
            if len(new_password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
            user.password_hash = pwd_context.hash(new_password)
            changes = True
        
        if changes:
            db.commit()
            return RedirectResponse(url=f"/admin/users?updated={user.username}", status_code=303)
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/audit", response_class=HTMLResponse)
async def admin_audit_dashboard(
    request: Request, db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
    table_name: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = db.query(models.AuditLog).filter(models.AuditLog.timestamp >= cutoff)
        
        # Sanitize filters
        if table_name:
            table_name = _sanitize(table_name, 100)
            query = query.filter(models.AuditLog.table_name == table_name)
        if action:
            action = _sanitize(action, 20)
            query = query.filter(models.AuditLog.action == action)
        if username:
            username = _sanitize(username)
            query = query.filter(models.AuditLog.username.ilike(f"%{username}%"))
        
        total = query.count()
        logs = query.order_by(desc(models.AuditLog.timestamp)).offset((page-1)*page_size).limit(page_size).all()
        
        # Activity summary
        summary = db.query(models.AuditLog.action, models.AuditLog.table_name, func.count(models.AuditLog.id).label('count'))\
            .filter(models.AuditLog.timestamp >= cutoff).group_by(models.AuditLog.action, models.AuditLog.table_name).all()
        
        # User activity
        user_activity = db.query(models.AuditLog.username, models.AuditLog.user_level, models.AuditLog.user_role, func.count(models.AuditLog.id).label('count'))\
            .filter(models.AuditLog.timestamp >= cutoff).group_by(models.AuditLog.username, models.AuditLog.user_level, models.AuditLog.user_role)\
            .order_by(desc('count')).limit(10).all()
        
        return templates.TemplateResponse("admin_audit.html", {
            "request": request, "audit_logs": logs or [], "total_count": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "current_page": page, "page_size": page_size, "days": days,
            "table_name": table_name or "", "action": action or "", "username": username or "",
            "activity_summary": summary or [], "user_activity": user_activity or [],
            "tables_list": ['budget_post_details', 'post_status', 'post_expenses', 'unit_expenditure', 'users'],
            "actions_list": ['INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'EXPORT', 'VIEW'],
            "auth_level": "admin"
        })
    except Exception:
        return templates.TemplateResponse("admin_users.html", {
            "request": request, "users": [], "roles": list(_VALID_ROLES),
            "current_role": "", "updated_user": "", "error": "Audit system error", "auth_level": "admin"
        })


@router.get("/audit/export", response_class=StreamingResponse)
async def export_audit_logs(
    request: Request, db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    table_name: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None)
):
    _require_admin(request)
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(models.AuditLog).filter(models.AuditLog.timestamp >= cutoff)
    
    if table_name:
        query = query.filter(models.AuditLog.table_name == _sanitize(table_name, 100))
    if action:
        query = query.filter(models.AuditLog.action == _sanitize(action, 20))
    if username:
        query = query.filter(models.AuditLog.username.ilike(f"%{_sanitize(username)}%"))
    
    logs = query.order_by(desc(models.AuditLog.timestamp)).limit(10000).all()
    
    data = [{
        'ID': l.id, 'Table': l.table_name, 'Record_ID': l.record_id, 'Action': l.action,
        'Username': l.username, 'User_Level': l.user_level, 'User_Role': l.user_role,
        'User_Unit': l.user_unit or '', 'IP_Address': l.ip_address or '',
        'Timestamp': l.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'Session_ID': l.session_id or '',
        'Changed_Fields_Count': len(l.changed_fields) if l.changed_fields else 0
    } for l in logs]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name='Audit_Logs', index=False)
    output.seek(0)
    
    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(output, headers={'Content-Disposition': f'attachment; filename="{filename}"'},
                            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@router.get("/api/performance", response_class=JSONResponse)
async def get_performance_stats(request: Request):
    _require_admin(request)
    from src.utils_cache import get_cache_stats
    from src.utils_performance import get_performance_stats as get_perf_stats
    return JSONResponse({"cache": get_cache_stats(), "endpoints": get_perf_stats()})


@router.post("/api/cache/clear", response_class=JSONResponse)
async def clear_cache(request: Request):
    _require_admin(request)
    from src.utils_cache import clear_all_cache
    cleared = clear_all_cache()
    return JSONResponse({"cleared": cleared, "message": f"Cleared {cleared} cache entries"})
