"""Authentication router - Secure and optimized"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from collections import defaultdict
from time import time
import re
import logging

from src.database import get_db
from src import models, schemas
from src.audit_service import AuditService
from src.utils_fiscal_year import get_default_fiscal_year

router = APIRouter(prefix="/auth", tags=["Auth"], include_in_schema=False)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Rate limiting state (in-memory, resets on restart)
_failed_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60
ATTEMPT_WINDOW = 300  # 5 minutes

# Input validation patterns
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
MAX_USERNAME_LEN = 50
MAX_PASSWORD_LEN = 128


def _sanitize_username(username: str) -> str:
    """Sanitize and validate username"""
    if not username:
        return ""
    username = username.strip()[:MAX_USERNAME_LEN]
    return username if USERNAME_PATTERN.match(username) else ""


def _get_client_id(request: Request) -> str:
    """Get client identifier for rate limiting"""
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host
    return ip or "unknown"


def _is_rate_limited(client_id: str) -> bool:
    """Check if client is rate limited"""
    now = time()
    # Clean old attempts
    _failed_attempts[client_id] = [t for t in _failed_attempts[client_id] if now - t < ATTEMPT_WINDOW]
    
    if len(_failed_attempts[client_id]) >= MAX_ATTEMPTS:
        oldest = min(_failed_attempts[client_id])
        if now - oldest < LOCKOUT_SECONDS:
            return True
        # Lockout expired, clear attempts
        _failed_attempts[client_id] = []
    return False


def _record_failed_attempt(client_id: str):
    """Record a failed login attempt"""
    _failed_attempts[client_id].append(time())


def _clear_attempts(client_id: str):
    """Clear failed attempts on successful login"""
    _failed_attempts.pop(client_id, None)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password with fallback for legacy plain passwords"""
    if not plain or not hashed:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        # Fallback for legacy plain text passwords (temporary)
        return plain == hashed


def hash_password(plain: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(plain)


# Dummy hash for timing attack prevention
_DUMMY_HASH = pwd_context.hash("dummy_password_for_timing")


def _constant_time_fail():
    """Perform dummy hash to prevent timing attacks"""
    pwd_context.verify("x", _DUMMY_HASH)


def _set_auth_cookies(response, user_data: dict, is_admin: bool = False):
    """Set authentication cookies with proper security settings"""
    base_opts = {"samesite": "lax", "max_age": 86400}  # 24 hours
    
    # Secure cookie for auth (httponly)
    response.set_cookie("auth_user", user_data["username"], httponly=True, **base_opts)
    
    # Display cookies (accessible to JS for UI)
    response.set_cookie("auth_user_display", user_data["username"], httponly=False, **base_opts)
    response.set_cookie("auth_level", user_data["level"], httponly=False, **base_opts)
    response.set_cookie("auth_role", user_data["role"], httponly=False, **base_opts)
    
    if user_data.get("unit"):
        response.set_cookie("auth_unit", user_data["unit"], httponly=False, **base_opts)
    
    if is_admin:
        response.set_cookie("admin_user", user_data["username"], httponly=True, **base_opts)


def _delete_auth_cookies(response):
    """Delete all authentication cookies"""
    cookies = ["auth_user", "auth_user_display", "auth_level", "auth_role", 
               "auth_unit", "admin_user", "selected_scheme_type", 
               "selected_scheme", "selected_sub_scheme"]
    for cookie in cookies:
        response.delete_cookie(cookie)


@router.post("/login")
async def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Handle user login with security measures"""
    client_id = _get_client_id(request)
    
    # Check rate limiting
    if _is_rate_limited(client_id):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    
    # Validate and sanitize input
    username = _sanitize_username(payload.username)
    password = (payload.password or "")[:MAX_PASSWORD_LEN]
    
    if not username or len(username) < 2:
        _record_failed_attempt(client_id)
        _constant_time_fail()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not password or len(password) < 4:
        _record_failed_attempt(client_id)
        _constant_time_fail()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    try:
        # Check regular user
        user = db.query(models.User).filter(
            models.User.username == username,
            models.User.is_active == True
        ).first()
        
        if user and verify_password(password, user.password_hash):
            _clear_attempts(client_id)
            
            # Audit log
            try:
                AuditService.log_login(db, request, user.username)
                db.commit()
            except Exception:
                db.rollback()
            
            user_data = {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "level": user.level,
                "role": user.role,
                "unit": user.unit
            }
            
            resp = JSONResponse({"message": "ok", "user": user_data})
            _set_auth_cookies(resp, user_data)
            
            # Set fiscal year
            default_fy = get_default_fiscal_year(db)
            resp.set_cookie("fiscal_year", default_fy, httponly=False, samesite="lax", max_age=2592000)
            
            return resp
        
        # Check admin user (only if regular user not found)
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
                    "id": admin.id,
                    "username": admin.username,
                    "full_name": admin.username,
                    "level": "dco",
                    "unit": "KONKAN DIVISION",
                    "role": "admin"
                }
                
                resp = JSONResponse({"message": "ok", "user": user_data})
                _set_auth_cookies(resp, user_data, is_admin=True)
                resp.set_cookie("fiscal_year", "2025-26", httponly=False, samesite="lax", max_age=2592000)
                
                return resp
        
        # Failed - apply timing protection and record attempt
        _record_failed_attempt(client_id)
        _constant_time_fail()
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Authentication service unavailable")


@router.post("/logout")
async def logout_post():
    """Handle POST logout"""
    resp = JSONResponse({"message": "logged out"})
    _delete_auth_cookies(resp)
    return resp


@router.get("/logout")
async def logout_get():
    """Handle GET logout with redirect"""
    resp = RedirectResponse(url="/", status_code=303)
    _delete_auth_cookies(resp)
    return resp


# --- User seeding (dev only) ---
def seed_users(db: Session):
    """Seed default users for development"""
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

    districts = ['Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg']

    district_users = []
    for d in districts:
        key = d.lower().replace(' ', '_')
        district_users.extend([
            {"username": f"{key}_o1", "full_name": f"{d} Officer 1", "level": "district", "unit": d, "role": "officer1"},
            {"username": f"{key}_o2", "full_name": f"{d} Officer 2", "level": "district", "unit": d, "role": "officer2"},
            {"username": f"{key}_asst", "full_name": f"{d} Assistant", "level": "district", "unit": d, "role": "assistant"},
        ])

    from src.config import DCO_STAFF_IDENTIFIER
    dco_staff_users = [
        {"username": "dco_staff_o1", "full_name": "DCO Staff Officer 1", "level": "district", "unit": DCO_STAFF_IDENTIFIER, "role": "officer1"},
        {"username": "dco_staff_o2", "full_name": "DCO Staff Officer 2", "level": "district", "unit": DCO_STAFF_IDENTIFIER, "role": "officer2"},
        {"username": "dco_staff_asst", "full_name": "DCO Staff Assistant", "level": "district", "unit": DCO_STAFF_IDENTIFIER, "role": "assistant"},
    ]

    for u in division_users + district_users + dco_staff_users:
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
            db.add(models.User(
                username=u["username"],
                password_hash=password,
                full_name=u["full_name"],
                level=u["level"],
                unit=u["unit"],
                role=u["role"],
            ))

    admin_username = "admin_KONKAN"
    if not db.query(models.AdminUser).filter(models.AdminUser.username == admin_username).first():
        db.add(models.AdminUser(username=admin_username, password_hash=hash_password("admin@123")))

    db.commit()
