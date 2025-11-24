from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src import models
from src import schemas
from src.audit_service import AuditService
from passlib.context import CryptContext
import logging

router = APIRouter(prefix="/auth", tags=["Auth"], include_in_schema=False)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)

def verify_password(plain_password: str, stored_password: str) -> bool:
    if not stored_password or not plain_password:
        return False
    try:
        return pwd_context.verify(plain_password, stored_password)
    except Exception:
        return plain_password == stored_password

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


@router.post("/login")
async def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    uname = (payload.username or '').strip()
    password = payload.password or ''

    if not uname or not password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        user = db.query(models.User).filter(
            models.User.username == uname, 
            models.User.is_active == True
        ).first()

        if user and verify_password(password, user.password_hash):
            try:
                AuditService.log_login(db, request, user.username)
                db.commit()
            except Exception:
                db.rollback()
            
            resp = JSONResponse({
                "message": "ok",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "level": user.level,
                    "role": user.role,
                    "unit": user.unit
                }
            })
            resp.set_cookie("auth_user", user.username, httponly=True, samesite="lax", max_age=86400)
            resp.set_cookie("auth_user_display", user.username, httponly=False, samesite="lax", max_age=86400)
            resp.set_cookie("auth_level", user.level, httponly=False, samesite="lax", max_age=86400)
            resp.set_cookie("auth_role", user.role, httponly=False, samesite="lax", max_age=86400)
            if user.unit:
                resp.set_cookie("auth_unit", user.unit, httponly=False, samesite="lax", max_age=86400)
            # Set default fiscal year cookie if not already set
            resp.set_cookie("fiscal_year", "2025-26", httponly=False, samesite="lax", max_age=2592000)
            return resp

        if not user:
            admin = db.query(models.AdminUser).filter(
                models.AdminUser.username == uname
            ).first()

            if admin and verify_password(password, admin.password_hash):
                try:
                    AuditService.log_login(db, request, admin.username)
                    db.commit()
                except Exception:
                    db.rollback()
                
                resp = JSONResponse({
                    "message": "ok",
                    "user": {
                        "id": admin.id,
                        "username": admin.username,
                        "full_name": admin.username,
                        "level": "dco",
                        "unit": "KONKAN DIVISION",
                        "role": "admin"
                    }
                })
                resp.set_cookie("admin_user", admin.username, httponly=True, samesite="lax", max_age=86400)
                resp.set_cookie("auth_user", admin.username, httponly=True, samesite="lax", max_age=86400)
                resp.set_cookie("auth_role", "admin", httponly=False, samesite="lax", max_age=86400)
                resp.set_cookie("auth_level", "dco", httponly=False, samesite="lax", max_age=86400)
                resp.set_cookie("auth_unit", "KONKAN DIVISION", httponly=False, samesite="lax", max_age=86400)
                # Set default fiscal year cookie if not already set
                resp.set_cookie("fiscal_year", "2025-26", httponly=False, samesite="lax", max_age=2592000)
                return resp

        pwd_context.verify("dummy", "$2b$10$dummyhashtopreventtimingattacksX")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error for user {uname}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Authentication service unavailable")


@router.post("/logout")
async def logout():
    resp = JSONResponse({"message": "logged out"})
    resp.delete_cookie("auth_user")
    resp.delete_cookie("auth_user_display")
    resp.delete_cookie("auth_level")
    resp.delete_cookie("auth_role")
    resp.delete_cookie("auth_unit")
    return resp


def seed_users(db: Session):
    password_map = {
        'assistant': 'assistant@123',
        'officer2': 'officer2@123',
        'officer1': 'officer1@123',
        'dco': 'dco@123',
    }

    db.query(models.AdminUser).delete(synchronize_session=False)

    division_users = [
        {"username": "dco_main", "full_name": "DCO Konkan", "level": "dco", "unit": "KONKAN DIVISION", "role": "dco"},
        {"username": "dco_o1", "full_name": "Division Officer 1", "level": "dco", "unit": "KONKAN DIVISION", "role": "officer1"},
        {"username": "dco_o2", "full_name": "Division Officer 2", "level": "dco", "unit": "KONKAN DIVISION", "role": "officer2"},
        {"username": "dco_asst", "full_name": "Division Assistant", "level": "dco", "unit": "KONKAN DIVISION", "role": "assistant"},
    ]

    districts = [ 'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg' ]

    district_users = []
    for d in districts:
        key = d.lower().replace(' ', '_')
        district_users.extend([
            {"username": f"{key}_o1", "full_name": f"{d} Officer 1", "level": "district", "unit": d, "role": "officer1"},
            {"username": f"{key}_o2", "full_name": f"{d} Officer 2", "level": "district", "unit": d, "role": "officer2"},
            {"username": f"{key}_asst", "full_name": f"{d} Assistant", "level": "district", "unit": d, "role": "assistant"},
        ])

    all_users = division_users + district_users
    for u in all_users:
        existing = db.query(models.User).filter(models.User.username == u["username"]).first()
        password = hash_password(password_map[u["role"]])
        if existing:
            existing.full_name = u["full_name"]
            existing.level = u["level"]
            existing.unit = u["unit"]
            existing.role = u["role"]
            if not existing.password_hash or len(existing.password_hash) < 30:
                existing.password_hash = password
        else:
            new_user = models.User(
                username=u["username"],
                password_hash=password,
                full_name=u["full_name"],
                level=u["level"],
                unit=u["unit"],
                role=u["role"],
            )
            db.add(new_user)

    admin_username = "admin_KONKAN"
    exists = db.query(models.AdminUser).filter(models.AdminUser.username == admin_username).first()
    if not exists:
        db.add(models.AdminUser(username=admin_username, password_hash=hash_password("admin@123")))

    db.commit()


