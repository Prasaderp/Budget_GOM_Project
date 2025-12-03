from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import io

from src.database import get_db
from src.core.templates import templates
from src import models, schemas

router = APIRouter(prefix="/admin", tags=["Admin"], include_in_schema=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=8)

def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def is_admin_authed(request: Request) -> bool:
    admin_user = request.cookies.get("admin_user", "").strip()
    return bool(admin_user and len(admin_user) > 0)


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "auth_level": "admin"})


@router.post("/login")
async def admin_login(request: Request, db: Session = Depends(get_db)):
    try:
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            data = await request.json()
            username = (data.get("username") or "").strip()
            password = data.get("password") or ""
        else:
            form = await request.form()
            username = (form.get("username") or "").strip()
            password = form.get("password") or ""

        if not username or not password:
            raise HTTPException(status_code=401, detail="Username and password are required")

        admin = db.query(models.AdminUser.username, models.AdminUser.password_hash)\
                 .filter(models.AdminUser.username == username)\
                 .first()

        if not admin:
            pwd_context.verify("dummy", "$2b$12$dummyhashtopreventtimingattacks")
            raise HTTPException(status_code=401, detail="Invalid admin credentials")

        try:
            password_valid = pwd_context.verify(password, admin.password_hash)
        except Exception as e:
            print(f"Password verification error for user {username}: {e}")
            password_valid = False

        if not password_valid:
            raise HTTPException(status_code=401, detail="Invalid admin credentials")

        resp = RedirectResponse(url="/admin/users", status_code=303)
        resp.set_cookie(
            "admin_user",
            admin.username,
            httponly=True,
            samesite="lax",
            max_age=86400,
            secure=False
        )

        return resp

    except HTTPException:
        raise
    except Exception as e:
        print(f"Admin login error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def admin_logout():
    resp = JSONResponse({
        "message": "ok",
        "timestamp": None
    })

    resp.delete_cookie(
        "admin_user",
        path="/",
        domain=None,
        secure=False,
        httponly=True
    )

    return resp


@router.get("/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    if not is_admin_authed(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    ROLES = ['dco', 'officer1', 'officer2', 'assistant']
    role_filter = (request.query_params.get('role') or '').strip()
    updated_user = (request.query_params.get('updated') or '').strip()

    try:
        users_query = db.query(
            models.User.id,
            models.User.username,
            models.User.role,
            models.User.level,
            models.User.unit,
            models.User.is_active
        ).filter(
            (models.User.level != 'taluka') | (models.User.is_active == True)
        ).order_by(models.User.id.asc())

        if role_filter and role_filter in ROLES:
            users_query = users_query.filter(models.User.role == role_filter)

        users = users_query.all()

        users_list = [
            {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'level': user.level,
                'unit': user.unit or '-'
            }
            for user in users
        ]

        return templates.TemplateResponse("admin_users.html", {
            "request": request,
            "users": users_list,
            "roles": ROLES,
            "current_role": role_filter,
            "updated_user": updated_user,
            "auth_level": "admin"
        })

    except Exception as e:
        print(f"Admin users page error: {e}")
        return RedirectResponse(url="/admin/login", status_code=303)


@router.post("/users/update")
async def admin_update_user(request: Request, db: Session = Depends(get_db)):
    if not is_admin_authed(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        form = await request.form()

        try:
            user_id = int(form.get("id") or "0")
            if user_id <= 0:
                raise ValueError("Invalid user ID")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID")

        new_username = (form.get("username") or "").strip() or None
        new_password = (form.get("password") or "").strip() or None

        if not new_username and not new_password:
            return RedirectResponse(url="/admin/users", status_code=303)

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        changes_made = False

        if new_username and new_username != user.username:
            if len(new_username) < 3:
                raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
                
            from sqlalchemy import exists
            username_exists = db.query(exists().where(
                models.User.username == new_username,
                models.User.id != user_id
            )).scalar()

            if username_exists:
                raise HTTPException(status_code=400, detail="Username already taken")

            old_username = user.username
            user.username = new_username

            db.query(models.Message).filter(
                models.Message.from_username == old_username
            ).update({models.Message.from_username: new_username}, synchronize_session=False)

            db.query(models.Message).filter(
                models.Message.to_username == old_username
            ).update({models.Message.to_username: new_username}, synchronize_session=False)

            changes_made = True

        if new_password:
            if len(new_password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
            user.password_hash = hash_password(new_password)
            changes_made = True

        if changes_made:
            db.commit()
            return RedirectResponse(url=f"/admin/users?updated={user.username}", status_code=303)

        return RedirectResponse(url="/admin/users", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Admin user update error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/audit", response_class=HTMLResponse)
async def admin_audit_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
    table_name: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    if not is_admin_authed(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(models.AuditLog).filter(models.AuditLog.timestamp >= cutoff_date)
        
        if table_name:
            query = query.filter(models.AuditLog.table_name == table_name)
        if action:
            query = query.filter(models.AuditLog.action == action)
        if username:
            query = query.filter(models.AuditLog.username.ilike(f"%{username}%"))
        
        total_count = query.count()
        
        audit_logs = (
            query
            .order_by(desc(models.AuditLog.timestamp))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        
        activity_summary = (
            db.query(
                models.AuditLog.action,
                models.AuditLog.table_name,
                func.count(models.AuditLog.id).label('count')
            )
            .filter(models.AuditLog.timestamp >= cutoff_date)
            .group_by(models.AuditLog.action, models.AuditLog.table_name)
            .all()
        )
        
        user_activity = (
            db.query(
                models.AuditLog.username,
                models.AuditLog.user_level,
                models.AuditLog.user_role,
                func.count(models.AuditLog.id).label('activity_count')
            )
            .filter(models.AuditLog.timestamp >= cutoff_date)
            .group_by(models.AuditLog.username, models.AuditLog.user_level, models.AuditLog.user_role)
            .order_by(desc('activity_count'))
            .limit(10)
            .all()
        )
        
        tables_list = ['budget_post_details', 'post_status', 'post_expenses', 'unit_expenditure', 'users']
        actions_list = ['INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'EXPORT', 'VIEW']
        
        return templates.TemplateResponse("admin_audit.html", {
            "request": request,
            "audit_logs": audit_logs or [],
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "days": days,
            "table_name": table_name or "",
            "action": action or "",
            "username": username or "",
            "activity_summary": activity_summary or [],
            "user_activity": user_activity or [],
            "tables_list": tables_list,
            "actions_list": actions_list,
            "auth_level": "admin"
        })
    except Exception as e:
        print(f"Audit dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("admin_users.html", {
            "request": request,
            "users": [],
            "roles": ['dco', 'officer1', 'officer2', 'assistant'],
            "current_role": "",
            "updated_user": "",
            "error": f"Audit system error: {str(e)}",
            "auth_level": "admin"
        })


@router.get("/audit/export", response_class=StreamingResponse)
async def export_audit_logs(
    request: Request,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    table_name: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None)
):
    if not is_admin_authed(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(models.AuditLog).filter(models.AuditLog.timestamp >= cutoff_date)
    
    if table_name:
        query = query.filter(models.AuditLog.table_name == table_name)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if username:
        query = query.filter(models.AuditLog.username.ilike(f"%{username}%"))
    
    audit_logs = query.order_by(desc(models.AuditLog.timestamp)).limit(10000).all()
    
    data = []
    for log in audit_logs:
        data.append({
            'ID': log.id,
            'Table': log.table_name,
            'Record_ID': log.record_id,
            'Action': log.action,
            'Username': log.username,
            'User_Level': log.user_level,
            'User_Role': log.user_role,
            'User_Unit': log.user_unit or '',
            'IP_Address': log.ip_address or '',
            'Timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'Session_ID': log.session_id or '',
            'Changed_Fields_Count': len(log.changed_fields) if log.changed_fields else 0
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Audit_Logs', index=False)
    
    output.seek(0)
    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    
    return StreamingResponse(
        output, 
        headers=headers, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@router.get("/api/performance", response_class=JSONResponse)
async def get_performance_stats(request: Request):
    if not is_admin_authed(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from src.utils_cache import get_cache_stats
    from src.utils_performance import get_performance_stats as get_perf_stats
    return JSONResponse({
        "cache": get_cache_stats(),
        "endpoints": get_perf_stats()
    })


@router.post("/api/cache/clear", response_class=JSONResponse)
async def clear_cache(request: Request):
    if not is_admin_authed(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from src.utils_cache import clear_all_cache
    cleared = clear_all_cache()
    return JSONResponse({"cleared": cleared, "message": f"Cleared {cleared} cache entries"})
