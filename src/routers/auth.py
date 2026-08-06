from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from collections import defaultdict
from time import time
from urllib.parse import quote
import re
import os
import logging

from src.database import get_db
from src import models, schemas
from src.audit_service import AuditService
from src.utils_fiscal_year import get_default_fiscal_year

router = APIRouter(prefix="/auth", tags=["Auth"], include_in_schema=False)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

_failed_attempts: dict = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60
ATTEMPT_WINDOW = 300

USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
MAX_USERNAME_LEN = 50
MAX_PASSWORD_LEN = 128

_IS_PROD = os.getenv("ENVIRONMENT", "development") == "production"


def _sanitize_username(username: str) -> str:
    if not username:
        return ""
    username = username.strip()[:MAX_USERNAME_LEN]
    return username if USERNAME_PATTERN.match(username) else ""


def _get_client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return ip or "unknown"


def _is_rate_limited(client_id: str) -> bool:
    now = time()
    _failed_attempts[client_id] = [t for t in _failed_attempts[client_id] if now - t < ATTEMPT_WINDOW]
    if len(_failed_attempts[client_id]) >= MAX_ATTEMPTS:
        oldest = min(_failed_attempts[client_id])
        if now - oldest < LOCKOUT_SECONDS:
            return True
        _failed_attempts[client_id] = []
    return False


def _record_failed_attempt(client_id: str) -> None:
    _failed_attempts[client_id].append(time())


def _clear_attempts(client_id: str) -> None:
    _failed_attempts.pop(client_id, None)


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


_DUMMY_HASH = pwd_context.hash("dummy_password_for_timing")


def _constant_time_fail() -> None:
    pwd_context.verify("x", _DUMMY_HASH)


def _set_auth_cookies(response, user_data: dict, is_admin: bool = False) -> None:
    base_opts = {"samesite": "lax", "max_age": 86400, "secure": _IS_PROD}

    response.set_cookie("auth_user", user_data["username"], httponly=True, **base_opts)
    response.set_cookie("auth_user_display", user_data["username"], httponly=False, **base_opts)
    response.set_cookie("auth_level", user_data["level"], httponly=False, **base_opts)
    response.set_cookie("auth_role", user_data["role"], httponly=False, **base_opts)

    if user_data.get("unit"):
        response.set_cookie("auth_unit", quote(user_data["unit"], safe=""), httponly=False, **base_opts)

    if is_admin:
        response.set_cookie("admin_user", user_data["username"], httponly=True, **base_opts)


def _delete_auth_cookies(response) -> None:
    for cookie in ("auth_user", "auth_user_display", "auth_level", "auth_role",
                   "auth_unit", "admin_user", "selected_scheme_type",
                   "selected_scheme", "selected_sub_scheme"):
        response.delete_cookie(cookie)


@router.post("/login")
async def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_id = _get_client_id(request)

    if _is_rate_limited(client_id):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")

    username = _sanitize_username(payload.username)
    password = (payload.password or "")[:MAX_PASSWORD_LEN]

    if not username or len(username) < 2 or not password or len(password) < 4:
        _record_failed_attempt(client_id)
        _constant_time_fail()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        user = db.query(models.User).filter(
            models.User.username == username,
            models.User.is_active == True
        ).first()

        if user and verify_password(password, user.password_hash):
            _clear_attempts(client_id)
            try:
                AuditService.log_login(db, request, user.username)
                db.commit()
            except Exception:
                db.rollback()

            user_data = {
                "id": user.id, "username": user.username, "full_name": user.full_name,
                "level": user.level, "role": user.role, "unit": user.unit
            }
            resp = JSONResponse({"message": "ok", "user": user_data})
            _set_auth_cookies(resp, user_data)
            default_fy = get_default_fiscal_year(db)
            resp.set_cookie("fiscal_year", default_fy, httponly=True, samesite="lax",
                            max_age=2592000, secure=_IS_PROD)
            return resp

        if not user:
            admin = db.query(models.AdminUser).filter(
                models.AdminUser.username == username
            ).first()

            if admin and verify_password(password, admin.password_hash):
                _clear_attempts(client_id)
                try:
                    AuditService.log_login(db, request, admin.username)
                    db.commit()
                except Exception:
                    db.rollback()

                user_data = {
                    "id": admin.id, "username": admin.username, "full_name": admin.username,
                    "level": "dco", "unit": "KONKAN DIVISION", "role": "admin"
                }
                resp = JSONResponse({"message": "ok", "user": user_data})
                _set_auth_cookies(resp, user_data, is_admin=True)
                resp.set_cookie("fiscal_year", get_default_fiscal_year(db), httponly=True,
                                samesite="lax", max_age=2592000, secure=_IS_PROD)
                return resp

        _record_failed_attempt(client_id)
        _constant_time_fail()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("login_error: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail="Authentication service unavailable")


@router.post("/logout")
async def logout_post():
    resp = JSONResponse({"message": "logged out"})
    _delete_auth_cookies(resp)
    return resp


@router.get("/logout")
async def logout_get():
    resp = RedirectResponse(url="/", status_code=303)
    _delete_auth_cookies(resp)
    return resp


def seed_users(db: Session, force: bool = False) -> None:
    """Idempotent user seed. Skipped on production startup; `force=True` is
    the deliberate operator path (scripts/reset_database.py), where the whole
    point is to hand back a database that has credentials and nothing else.
    """
    if _IS_PROD and not force:
        return

    password_map = {
        'assistant': 'assistant@123',
        'officer2': 'officer2@123',
        'officer1': 'officer1@123',
        'dco': 'dco@123',
    }

    from src.config import DCO_STAFF_IDENTIFIER
    districts = ['Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg']

    all_users = [
        {"username": "dco_main", "full_name": "DCO Konkan", "level": "dco", "unit": "KONKAN DIVISION", "role": "dco"},
        {"username": "dco_o1", "full_name": "Division Officer 1", "level": "dco", "unit": "KONKAN DIVISION", "role": "officer1"},
        {"username": "dco_o2", "full_name": "Division Officer 2", "level": "dco", "unit": "KONKAN DIVISION", "role": "officer2"},
        {"username": "dco_asst", "full_name": "Division Assistant", "level": "dco", "unit": "KONKAN DIVISION", "role": "assistant"},
        {"username": "dco_staff_o1", "full_name": "DCO Staff Officer 1", "level": "district", "unit": DCO_STAFF_IDENTIFIER, "role": "officer1"},
        {"username": "dco_staff_o2", "full_name": "DCO Staff Officer 2", "level": "district", "unit": DCO_STAFF_IDENTIFIER, "role": "officer2"},
        {"username": "dco_staff_asst", "full_name": "DCO Staff Assistant", "level": "district", "unit": DCO_STAFF_IDENTIFIER, "role": "assistant"},
    ]

    for d in districts:
        key = d.lower().replace(' ', '_')
        all_users.extend([
            {"username": f"{key}_o1", "full_name": f"{d} Officer 1", "level": "district", "unit": d, "role": "officer1"},
            {"username": f"{key}_o2", "full_name": f"{d} Officer 2", "level": "district", "unit": d, "role": "officer2"},
            {"username": f"{key}_asst", "full_name": f"{d} Assistant", "level": "district", "unit": d, "role": "assistant"},
        ])

    existing = {u.username for u in db.query(models.User.username).all()}

    for u in all_users:
        if u["username"] in existing:
            db.query(models.User).filter(models.User.username == u["username"]).update(
                {"full_name": u["full_name"], "level": u["level"], "unit": u["unit"],
                 "role": u["role"], "is_active": True},
                synchronize_session=False
            )
        else:
            db.add(models.User(
                username=u["username"],
                password_hash=hash_password(password_map[u["role"]]),
                full_name=u["full_name"], level=u["level"],
                unit=u["unit"], role=u["role"], is_active=True
            ))

    admin_username = "admin_KONKAN"
    if not db.query(models.AdminUser).filter(models.AdminUser.username == admin_username).first():
        db.add(models.AdminUser(username=admin_username, password_hash=hash_password("admin@123")))

    db.commit()
