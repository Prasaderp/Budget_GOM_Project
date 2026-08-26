import sys
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from src.utils_static import OptimizedStaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import logging
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src import models
from src.database import engine, SessionLocal, get_db, run_database_migrations
from src.utils_cache import memory_cache
from src.utils_auth import get_auth_user, get_auth_role, get_sub_scheme_code, verify_api_auth

# Shared routers (used across all schemes)
from src.routers import api_assistant, auth, admin, messages, ui_taluka_selection, ui_taluka_breakdown
from src.routers import ui_scheme_selection, timing_management, warnings, fiscal_year, training, settings
from src.routers import ui_shashan_niryan, completion_status
from src.audit_middleware import AuditMiddleware
from src.core.taluka.middleware import TalukaScopeMiddleware
from src.core.taluka import orm_filter as _taluka_orm_filter  # noqa: F401 — binds the do_orm_execute listener
from src.core.taluka import write as _taluka_write  # noqa: F401 — binds the total-space rebase backstop

from src.core.registry import scheme_registry

# Scheme-specific routers for 20530019 (District Administration - Charged)
from src.schemes.s2053.subs.s20530019 import (
    api_router as s20530019_api,
    budget_details_router as ui_budget_details_20530019,
    post_status_router as ui_post_status_20530019,
    post_expenses_router as ui_post_expenses_20530019,
    unit_expenditure_router as ui_unit_expenditure_20530019,
    budget_summary_router as ui_budget_summary_20530019,
    abstract_router as ui_abstract_20530019,
    category_info_router as ui_category_info_20530019,
)
from src.schemes.s2053.subs.s20530019.config import SCHEME_CONFIG as s20530019_config

scheme_registry.register_scheme(s20530019_config)

# Scheme-specific routers for 20530153 (District Administration - Charged)
from src.schemes.s2053.subs.s20530153 import (
    api_router as s20530153_api,
    budget_details_router as ui_budget_details_20530153,
    post_status_router as ui_post_status_20530153,
    post_expenses_router as ui_post_expenses_20530153,
    unit_expenditure_router as ui_unit_expenditure_20530153,
    budget_summary_router as ui_budget_summary_20530153,
    abstract_router as ui_abstract_20530153,
    category_info_router as ui_category_info_20530153,
)
from src.schemes.s2053.subs.s20530153.config import SCHEME_CONFIG as s20530153_config

scheme_registry.register_scheme(s20530153_config)

# Scheme-specific routers for 20530233 (District Administration - Charged)
from src.schemes.s2053.subs.s20530233 import (
    api_router as s20530233_api,
    budget_details_router as ui_budget_details_20530233,
    post_status_router as ui_post_status_20530233,
    post_expenses_router as ui_post_expenses_20530233,
    unit_expenditure_router as ui_unit_expenditure_20530233,
    budget_summary_router as ui_budget_summary_20530233,
    abstract_router as ui_abstract_20530233,
    category_info_router as ui_category_info_20530233,
)
from src.schemes.s2053.subs.s20530233.config import SCHEME_CONFIG as s20530233_config

scheme_registry.register_scheme(s20530233_config)

# Scheme-specific routers for 20530304 (District Administration - Charged)
from src.schemes.s2053.subs.s20530304 import (
    api_router as s20530304_api,
    budget_details_router as ui_budget_details_20530304,
    post_status_router as ui_post_status_20530304,
    post_expenses_router as ui_post_expenses_20530304,
    unit_expenditure_router as ui_unit_expenditure_20530304,
    budget_summary_router as ui_budget_summary_20530304,
    abstract_router as ui_abstract_20530304,
    category_info_router as ui_category_info_20530304,
)
from src.schemes.s2053.subs.s20530304.config import SCHEME_CONFIG as s20530304_config

scheme_registry.register_scheme(s20530304_config)

# Scheme-specific routers for 20530378 (District Administration - Charged)
from src.schemes.s2053.subs.s20530378 import (
    api_router as s20530378_api,
    budget_details_router as ui_budget_details_20530378,
    post_status_router as ui_post_status_20530378,
    post_expenses_router as ui_post_expenses_20530378,
    unit_expenditure_router as ui_unit_expenditure_20530378,
    budget_summary_router as ui_budget_summary_20530378,
    abstract_router as ui_abstract_20530378,
    category_info_router as ui_category_info_20530378,
)
from src.schemes.s2053.subs.s20530378.config import SCHEME_CONFIG as s20530378_config

scheme_registry.register_scheme(s20530378_config)

# Scheme-specific routers for 20530028 (District Administration - Voted)
from src.schemes.s2053.subs.s20530028 import (
    api_router as s20530028_api,
    budget_details_router as ui_budget_details,
    post_status_router as ui_post_status,
    post_expenses_router as ui_post_expenses,
    unit_expenditure_router as ui_unit_expenditure,
    budget_summary_router as ui_budget_summary,
    abstract_router as ui_abstract,
    category_info_router as ui_category_info,
)
from src.schemes.s2053.subs.s20530028.config import SCHEME_CONFIG as s20530028_config

scheme_registry.register_scheme(s20530028_config)

# Scheme-specific routers for 20530162
from src.schemes.s2053.subs.s20530162 import (
    api_router as s20530162_api,
    budget_details_router as ui_budget_details_20530162,
    post_status_router as ui_post_status_20530162,
    post_expenses_router as ui_post_expenses_20530162,
    unit_expenditure_router as ui_unit_expenditure_20530162,
    budget_summary_router as ui_budget_summary_20530162,
    abstract_router as ui_abstract_20530162,
    category_info_router as ui_category_info_20530162
)
from src.schemes.s2053.subs.s20530162.config import SCHEME_CONFIG as s20530162_config

scheme_registry.register_scheme(s20530162_config)

# Scheme-specific routers for 20530242
from src.schemes.s2053.subs.s20530242 import (
    api_router as s20530242_api,
    budget_details_router as ui_budget_details_20530242,
    post_status_router as ui_post_status_20530242,
    post_expenses_router as ui_post_expenses_20530242,
    unit_expenditure_router as ui_unit_expenditure_20530242,
    budget_summary_router as ui_budget_summary_20530242,
    abstract_router as ui_abstract_20530242,
    category_info_router as ui_category_info_20530242
)
from src.schemes.s2053.subs.s20530242.config import SCHEME_CONFIG as s20530242_config

scheme_registry.register_scheme(s20530242_config)

# Scheme-specific routers for 20530313
from src.schemes.s2053.subs.s20530313 import (
    api_router as s20530313_api,
    budget_details_router as ui_budget_details_20530313,
    post_status_router as ui_post_status_20530313,
    post_expenses_router as ui_post_expenses_20530313,
    unit_expenditure_router as ui_unit_expenditure_20530313,
    budget_summary_router as ui_budget_summary_20530313,
    abstract_router as ui_abstract_20530313,
    category_info_router as ui_category_info_20530313
)
from src.schemes.s2053.subs.s20530313.config import SCHEME_CONFIG as s20530313_config

scheme_registry.register_scheme(s20530313_config)

# Scheme-specific routers for 20530387
from src.schemes.s2053.subs.s20530387 import (
    api_router as s20530387_api,
    budget_details_router as ui_budget_details_20530387,
    post_status_router as ui_post_status_20530387,
    post_expenses_router as ui_post_expenses_20530387,
    unit_expenditure_router as ui_unit_expenditure_20530387,
    budget_summary_router as ui_budget_summary_20530387,
    category_info_router as ui_category_info_20530387
)
from src.schemes.s2053.subs.s20530387.config import SCHEME_CONFIG as s20530387_config

scheme_registry.register_scheme(s20530387_config)

# Scheme-specific routers for 20290046 (District Administration - Charged)
from src.schemes.s2029.subs.s20290046 import (
    api_router as s20290046_api,
    budget_details_router as ui_budget_details_20290046,
    post_status_router as ui_post_status_20290046,
    post_expenses_router as ui_post_expenses_20290046,
    unit_expenditure_router as ui_unit_expenditure_20290046,
    budget_summary_router as ui_budget_summary_20290046,
    abstract_router as ui_abstract_20290046,
    category_info_router as ui_category_info_20290046,
)
from src.schemes.s2029.subs.s20290046.config import SCHEME_CONFIG as s20290046_config

scheme_registry.register_scheme(s20290046_config)

# Scheme-specific routers for 20290182 (District Administration - Charged)
from src.schemes.s2029.subs.s20290182 import (
    api_router as s20290182_api,
    budget_details_router as ui_budget_details_20290182,
    post_status_router as ui_post_status_20290182,
    post_expenses_router as ui_post_expenses_20290182,
    unit_expenditure_router as ui_unit_expenditure_20290182,
    budget_summary_router as ui_budget_summary_20290182,
    abstract_router as ui_abstract_20290182,
    category_info_router as ui_category_info_20290182,
)
from src.schemes.s2029.subs.s20290182.config import SCHEME_CONFIG as s20290182_config

scheme_registry.register_scheme(s20290182_config)

# Scheme-specific routers for 20290262 (District Administration - Charged)
from src.schemes.s2029.subs.s20290262 import (
    api_router as s20290262_api,
    budget_details_router as ui_budget_details_20290262,
    post_status_router as ui_post_status_20290262,
    post_expenses_router as ui_post_expenses_20290262,
    unit_expenditure_router as ui_unit_expenditure_20290262,
    budget_summary_router as ui_budget_summary_20290262,
    abstract_router as ui_abstract_20290262,
    category_info_router as ui_category_info_20290262,
)
from src.schemes.s2029.subs.s20290262.config import SCHEME_CONFIG as s20290262_config

scheme_registry.register_scheme(s20290262_config)

# Scheme-specific routers for 20290037 (District Administration - Charged)
from src.schemes.s2029.subs.s20290037 import (
    api_router as s20290037_api,
    budget_details_router as ui_budget_details_20290037,
    post_status_router as ui_post_status_20290037,
    post_expenses_router as ui_post_expenses_20290037,
    unit_expenditure_router as ui_unit_expenditure_20290037,
    budget_summary_router as ui_budget_summary_20290037,
    abstract_router as ui_abstract_20290037,
    category_info_router as ui_category_info_20290037,
)
from src.schemes.s2029.subs.s20290037.config import SCHEME_CONFIG as s20290037_config

scheme_registry.register_scheme(s20290037_config)

# Scheme 62450017
from src.schemes.s6245.subs.s62450017 import (
    SCHEME_CONFIG as s62450017_config,
    api_router as s62450017_api,
    ui_router as s62450017_ui,
)

scheme_registry.register_scheme(s62450017_config)
scheme_registry.register_router("62450017", s62450017_api)
scheme_registry.register_router("62450017", s62450017_ui)

# Scheme 64010018
from src.schemes.s6401.subs.s64010018 import (
    SCHEME_CONFIG as s64010018_config,
    api_router as s64010018_api,
    ui_router as s64010018_ui,
)

scheme_registry.register_scheme(s64010018_config)
scheme_registry.register_router("64010018", s64010018_api)
scheme_registry.register_router("64010018", s64010018_ui)

# Scheme 7610 sub-schemes
from src.schemes.s7610.subs.s76100149 import (
    SCHEME_CONFIG as s76100149_config,
    api_router as s76100149_api,
    ui_router as s76100149_ui,
)
from src.schemes.s7610.subs.s76100158 import (
    SCHEME_CONFIG as s76100158_config,
    api_router as s76100158_api,
    ui_router as s76100158_ui,
)
from src.schemes.s7610.subs.s76100167 import (
    SCHEME_CONFIG as s76100167_config,
    api_router as s76100167_api,
    ui_router as s76100167_ui,
)
from src.schemes.s7610.subs.s76101871 import (
    SCHEME_CONFIG as s76101871_config,
    api_router as s76101871_api,
    ui_router as s76101871_ui,
)

# Scheme 2235 sub-schemes
from src.schemes.s2235.subs.s22353408 import (
    SCHEME_CONFIG as s22353408_config,
    api_router as s22353408_api,
    ui_router as s22353408_ui,
)
from src.schemes.s2235.subs.s22350311 import (
    SCHEME_CONFIG as s22350311_config,
    api_router as s22350311_api,
    ui_router as s22350311_ui,
)
from src.schemes.s2235.subs.s22353195 import (
    SCHEME_CONFIG as s22353195_config,
    api_router as s22353195_api,
    ui_router as s22353195_ui,
)
from src.schemes.s2235.subs.s22350338 import (
    SCHEME_CONFIG as s22350338_config,
    api_router as s22350338_api,
    ui_router as s22350338_ui,
)

# Scheme 2075 sub-schemes
from src.schemes.s2075 import (
    SCHEME_CONFIG as s2075_config,
    api_router as s2075_api,
    ui_router as s2075_ui,
)

# Scheme 2215
from src.schemes.s2215.subs.s2215 import (
    SCHEME_CONFIG as s2215_config,
    api_router as s2215_api,
    ui_router as s2215_ui,
)

# Scheme 2245
from src.schemes.s2245.subs.s2245 import (
    SCHEME_CONFIG as s2245_config,
    api_router as s2245_api,
    ui_router as s2245_ui,
)

# Scheme 0029
from src.schemes.s0029.subs.s0029 import (
    SCHEME_CONFIG as s0029_config,
    api_router as s0029_api,
    ui_router as s0029_ui,
)

scheme_registry.register_scheme(s22353408_config)
scheme_registry.register_router("22353408", s22353408_api)
scheme_registry.register_router("22353408", s22353408_ui)

scheme_registry.register_scheme(s22350311_config)
scheme_registry.register_router("22350311", s22350311_api)
scheme_registry.register_router("22350311", s22350311_ui)

scheme_registry.register_scheme(s22353195_config)
scheme_registry.register_router("22353195", s22353195_api)
scheme_registry.register_router("22353195", s22353195_ui)

scheme_registry.register_scheme(s22350338_config)
scheme_registry.register_router("22350338", s22350338_api)
scheme_registry.register_router("22350338", s22350338_ui)

scheme_registry.register_scheme(s76100149_config)
scheme_registry.register_router("76100149", s76100149_api)
scheme_registry.register_router("76100149", s76100149_ui)

scheme_registry.register_scheme(s76100158_config)
scheme_registry.register_router("76100158", s76100158_api)
scheme_registry.register_router("76100158", s76100158_ui)

scheme_registry.register_scheme(s76100167_config)
scheme_registry.register_router("76100167", s76100167_api)
scheme_registry.register_router("76100167", s76100167_ui)

scheme_registry.register_scheme(s76101871_config)
scheme_registry.register_router("76101871", s76101871_api)
scheme_registry.register_router("76101871", s76101871_ui)

scheme_registry.register_scheme(s2075_config)
scheme_registry.register_router("2075", s2075_api)
scheme_registry.register_router("2075", s2075_ui)

scheme_registry.register_scheme(s2215_config)
scheme_registry.register_router("2215", s2215_api)
scheme_registry.register_router("2215", s2215_ui)

scheme_registry.register_scheme(s2245_config)
scheme_registry.register_router("2245", s2245_api)
scheme_registry.register_router("2245", s2245_ui)

scheme_registry.register_scheme(s0029_config)
scheme_registry.register_router("0029", s0029_api)
scheme_registry.register_router("0029", s0029_ui)

# Scheme-specific routers for 20450091 (Stamp Duty Collection - Voted)
from src.schemes.s2045.subs.s20450091 import (
    api_router as s20450091_api,
    budget_details_router as ui_budget_details_20450091,
    post_status_router as ui_post_status_20450091,
    post_expenses_router as ui_post_expenses_20450091,
    unit_expenditure_router as ui_unit_expenditure_20450091,
    budget_summary_router as ui_budget_summary_20450091,
    abstract_router as ui_abstract_20450091,
    category_info_router as ui_category_info_20450091
)
from src.schemes.s2045.subs.s20450091.config import SCHEME_CONFIG as s20450091_config

scheme_registry.register_scheme(s20450091_config)

# Scheme 20450182 - Stamp Duty Collection Recovery (Other Charges)
from src.schemes.s2045.subs.s20450182 import (
    SCHEME_CONFIG as s20450182_config,
    api_router as s20450182_api,
    ui_router as s20450182_ui,
)
scheme_registry.register_scheme(s20450182_config)
scheme_registry.register_router("20450182", s20450182_api)
scheme_registry.register_router("20450182", s20450182_ui)

# Scheme 20450251 - Education Cess Grants to Village Panchayats
from src.schemes.s2045.subs.s20450251 import (
    SCHEME_CONFIG as s20450251_config,
    api_router as s20450251_api,
    ui_router as s20450251_ui,
)
scheme_registry.register_scheme(s20450251_config)
scheme_registry.register_router("20450251", s20450251_api)
scheme_registry.register_router("20450251", s20450251_ui)

# Scheme 20450262 - Collection Recovery & Employment Cess
from src.schemes.s2045.subs.s20450262 import (
    SCHEME_CONFIG as s20450262_config,
    api_router as s20450262_api,
    ui_router as s20450262_ui,
)
scheme_registry.register_scheme(s20450262_config)
scheme_registry.register_router("20450262", s20450262_api)
scheme_registry.register_router("20450262", s20450262_ui)

_IS_PROD = os.getenv("ENVIRONMENT", "development") == "production"
_CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8000").split(",") if o.strip()]

app = FastAPI(
    title="Budget Management System",
    description="Government Budget Management System",
    version="1.0.0",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json"
)

from src.core.templates import render

app.mount("/static", OptimizedStaticFiles(directory="static"), name="static")

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Accept"],
)

executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="bg_worker")

class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        path = request.url.path

        if path.startswith("/static/") or path.startswith("/docs/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            response.headers["Vary"] = "Accept-Encoding"
        elif path.startswith("/api/"):
            if path.startswith("/api/completion-status"):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            else:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" if request.method != "GET" else "public, max-age=60"
            response.headers["Vary"] = "Accept-Encoding"
        elif path in ["/", "/admin/login"]:
            response.headers.setdefault("Cache-Control", "no-cache, must-revalidate")
        else:
            response.headers.setdefault("Cache-Control", "private, max-age=30")

        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        })

        return response

app.add_middleware(PerformanceMiddleware)
app.add_middleware(AuditMiddleware)
# Registered after AuditMiddleware so it executes before it (Starlette's
# add_middleware inserts at the front of the stack) — every request-scoped
# ORM query, including AuditMiddleware's own, sees the caller's data scope.
app.add_middleware(TalukaScopeMiddleware)

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    _MAX_BODY = 10 * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > self._MAX_BODY:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 403 and request.url.path.startswith("/ui/"):
        from src.utils_scheme import _extract_scheme_from_url
        from src.utils_district import get_user_district
        from src.config import DISTRICTS_MR
        
        scheme_code = _extract_scheme_from_url(request.url.path)
        scheme_config = None
        if scheme_code:
            scheme_config = scheme_registry.get_scheme(scheme_code)
        
        auth_level = request.cookies.get("auth_level", "")
        auth_unit = request.cookies.get("auth_unit", "")
        user_district = get_user_district(auth_level, auth_unit)
        
        if user_district and user_district in DISTRICTS_MR:
            user_district_display = DISTRICTS_MR[user_district]
        else:
            user_district_display = user_district or auth_unit
        
        allowed_districts = []
        if scheme_config:
            try:
                import importlib
                config_module = importlib.import_module(f"src.schemes.s{scheme_config.parent_scheme}.subs.s{scheme_code}.config")
                if hasattr(config_module, 'KONKAN_DISTRICTS'):
                    allowed_districts = [DISTRICTS_MR.get(d, d) for d in config_module.KONKAN_DISTRICTS if d != 'DCO Staff']
            except (ImportError, AttributeError):
                pass
        
        context = {
            "request": request,
            "scheme_code": scheme_code or "Unknown",
            "scheme_name": scheme_config.name_mr if scheme_config else "Unknown",
            "user_district": user_district_display,
            "allowed_districts": allowed_districts,
            "error_message": exc.detail if exc.detail != "Access denied" else None
        }
        
        return render(
            request,
            "access_denied.html",
            context,
            status_code=exc.status_code,
        )
    
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

SCHEME_REQUIRED_PATHS = ('/ui/taluka-selection', '/ui/timing-management', '/ui/warnings', '/ui/settings')

@app.middleware("http")
async def require_auth_for_ui(request: Request, call_next):
    path = request.url.path
    if path.startswith("/ui/"):
        auth_user = get_auth_user(request)
        if not auth_user:
            return RedirectResponse(url='/', status_code=303)
        if get_auth_role(request) == 'admin' and request.cookies.get("admin_user"):
            return RedirectResponse(url='/admin/users', status_code=303)

        import re
        scheme_in_path = re.search(r'/ui/s(\d{4,8})/', path)
        if not scheme_in_path:
            if any(path.startswith(p) for p in SCHEME_REQUIRED_PATHS):
                if not get_sub_scheme_code(request):
                    return RedirectResponse(url='/ui/scheme-selection', status_code=303)
    elif path.startswith('/admin') and path != '/admin/login':
        role = get_auth_role(request)
        admin_sess = request.cookies.get("admin_user", '')
        if role != 'admin' and not admin_sess:
            return RedirectResponse(url='/admin/login', status_code=303)
    return await call_next(request)

if os.getenv("RUN_DB_CREATE_ALL", "true").lower() in {"1", "true", "yes"}:
    models.Base.metadata.create_all(bind=engine)
    run_database_migrations()
    db = SessionLocal()
    try:
        from src.core.taluka.provisioning import backfill_district_office_twins
        backfill_district_office_twins(db)
        db.commit()

        if not _IS_PROD:
            from src.routers.auth import seed_users
            seed_users(db)

        from src.utils_fiscal_year import get_default_fiscal_year
        default_fy_value = get_default_fiscal_year(db)
        existing_fy = db.query(models.FiscalYear).filter(models.FiscalYear.year_range == default_fy_value).first()
        if not existing_fy:
            default_fy = models.FiscalYear(year_range=default_fy_value, is_active=True, created_by='system')
            db.add(default_fy)
            db.commit()
    finally:
        db.close()

# Shared routers
app.include_router(ui_scheme_selection.router)
app.include_router(ui_scheme_selection.placeholder_router)
app.include_router(api_assistant.router)
app.include_router(auth.router)
app.include_router(messages.router)
app.include_router(admin.router)
app.include_router(ui_taluka_selection.router)
app.include_router(ui_taluka_breakdown.router)
app.include_router(timing_management.router)
app.include_router(warnings.router)
app.include_router(fiscal_year.router)
app.include_router(training.router)
app.include_router(settings.router)
app.include_router(ui_shashan_niryan.router)
app.include_router(ui_shashan_niryan._PDF_ROUTER)
app.include_router(completion_status.router)

# Scheme 20530028 UI routers
app.include_router(ui_budget_details)
app.include_router(ui_post_status)
app.include_router(ui_post_expenses)
app.include_router(ui_unit_expenditure)
app.include_router(ui_abstract)
app.include_router(ui_category_info)
app.include_router(ui_budget_summary)

# Register 20530028 route prefixes from routers
for router in [ui_budget_details, ui_post_status, ui_post_expenses, ui_unit_expenditure, 
                ui_abstract, ui_category_info, ui_budget_summary]:
    if hasattr(router, 'prefix') and router.prefix:
        scheme_registry.register_route_prefix("20530028", router.prefix)

# Scheme 20530028 API router
app.include_router(s20530028_api)
if hasattr(s20530028_api, 'prefix') and s20530028_api.prefix:
    scheme_registry.register_route_prefix("20530028", s20530028_api.prefix)

# Scheme 20530162 UI routers
app.include_router(ui_budget_details_20530162)
app.include_router(ui_post_status_20530162)
app.include_router(ui_post_expenses_20530162)
app.include_router(ui_unit_expenditure_20530162)
app.include_router(ui_abstract_20530162)
app.include_router(ui_category_info_20530162)
app.include_router(ui_budget_summary_20530162)

# Register 20530162 route prefixes from routers
for router in [ui_budget_details_20530162, ui_post_status_20530162, ui_post_expenses_20530162, 
                ui_unit_expenditure_20530162, ui_abstract_20530162, ui_category_info_20530162, 
                ui_budget_summary_20530162]:
    if hasattr(router, 'prefix') and router.prefix:
        scheme_registry.register_route_prefix("20530162", router.prefix)

# Scheme 20530162 API router
app.include_router(s20530162_api)
if hasattr(s20530162_api, 'prefix') and s20530162_api.prefix:
    scheme_registry.register_route_prefix("20530162", s20530162_api.prefix)

# Scheme 20530019 UI routers
app.include_router(ui_budget_details_20530019)
app.include_router(ui_post_status_20530019)
app.include_router(ui_post_expenses_20530019)
app.include_router(ui_unit_expenditure_20530019)
app.include_router(ui_abstract_20530019)
app.include_router(ui_category_info_20530019)
app.include_router(ui_budget_summary_20530019)

# Register 20530019 route prefixes from routers
for router in [
    ui_budget_details_20530019,
    ui_post_status_20530019,
    ui_post_expenses_20530019,
    ui_unit_expenditure_20530019,
    ui_abstract_20530019,
    ui_category_info_20530019,
    ui_budget_summary_20530019,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20530019", router.prefix)

# Scheme 20530019 API router
app.include_router(s20530019_api)
if hasattr(s20530019_api, "prefix") and s20530019_api.prefix:
    scheme_registry.register_route_prefix("20530019", s20530019_api.prefix)

# Scheme 20530153 UI routers
app.include_router(ui_budget_details_20530153)
app.include_router(ui_post_status_20530153)
app.include_router(ui_post_expenses_20530153)
app.include_router(ui_unit_expenditure_20530153)
app.include_router(ui_abstract_20530153)
app.include_router(ui_category_info_20530153)
app.include_router(ui_budget_summary_20530153)

# Register 20530153 route prefixes from routers
for router in [
    ui_budget_details_20530153,
    ui_post_status_20530153,
    ui_post_expenses_20530153,
    ui_unit_expenditure_20530153,
    ui_abstract_20530153,
    ui_category_info_20530153,
    ui_budget_summary_20530153,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20530153", router.prefix)

# Scheme 20530153 API router
app.include_router(s20530153_api)
if hasattr(s20530153_api, "prefix") and s20530153_api.prefix:
    scheme_registry.register_route_prefix("20530153", s20530153_api.prefix)

# Scheme 20530233 UI routers
app.include_router(ui_budget_details_20530233)
app.include_router(ui_post_status_20530233)
app.include_router(ui_post_expenses_20530233)
app.include_router(ui_unit_expenditure_20530233)
app.include_router(ui_abstract_20530233)
app.include_router(ui_category_info_20530233)
app.include_router(ui_budget_summary_20530233)

# Register 20530233 route prefixes from routers
for router in [
    ui_budget_details_20530233,
    ui_post_status_20530233,
    ui_post_expenses_20530233,
    ui_unit_expenditure_20530233,
    ui_abstract_20530233,
    ui_category_info_20530233,
    ui_budget_summary_20530233,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20530233", router.prefix)

# Scheme 20530233 API router
app.include_router(s20530233_api)
if hasattr(s20530233_api, "prefix") and s20530233_api.prefix:
    scheme_registry.register_route_prefix("20530233", s20530233_api.prefix)

# Scheme 20530304 UI routers
app.include_router(ui_budget_details_20530304)
app.include_router(ui_post_status_20530304)
app.include_router(ui_post_expenses_20530304)
app.include_router(ui_unit_expenditure_20530304)
app.include_router(ui_abstract_20530304)
app.include_router(ui_category_info_20530304)
app.include_router(ui_budget_summary_20530304)

# Register 20530304 route prefixes from routers
for router in [
    ui_budget_details_20530304,
    ui_post_status_20530304,
    ui_post_expenses_20530304,
    ui_unit_expenditure_20530304,
    ui_abstract_20530304,
    ui_category_info_20530304,
    ui_budget_summary_20530304,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20530304", router.prefix)

# Scheme 20530304 API router
app.include_router(s20530304_api)
if hasattr(s20530304_api, "prefix") and s20530304_api.prefix:
    scheme_registry.register_route_prefix("20530304", s20530304_api.prefix)

# Scheme 20530378 UI routers
app.include_router(ui_budget_details_20530378)
app.include_router(ui_post_status_20530378)
app.include_router(ui_post_expenses_20530378)
app.include_router(ui_unit_expenditure_20530378)
app.include_router(ui_abstract_20530378)
app.include_router(ui_category_info_20530378)
app.include_router(ui_budget_summary_20530378)

# Register 20530378 route prefixes from routers
for router in [
    ui_budget_details_20530378,
    ui_post_status_20530378,
    ui_post_expenses_20530378,
    ui_unit_expenditure_20530378,
    ui_abstract_20530378,
    ui_category_info_20530378,
    ui_budget_summary_20530378,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20530378", router.prefix)

# Scheme 20530378 API router
app.include_router(s20530378_api)
if hasattr(s20530378_api, "prefix") and s20530378_api.prefix:
    scheme_registry.register_route_prefix("20530378", s20530378_api.prefix)

# Scheme 20530242 UI routers
app.include_router(ui_budget_details_20530242)
app.include_router(ui_post_status_20530242)
app.include_router(ui_post_expenses_20530242)
app.include_router(ui_unit_expenditure_20530242)
app.include_router(ui_abstract_20530242)
app.include_router(ui_category_info_20530242)
app.include_router(ui_budget_summary_20530242)

# Register 20530242 route prefixes from routers
for router in [ui_budget_details_20530242, ui_post_status_20530242, ui_post_expenses_20530242, 
                ui_unit_expenditure_20530242, ui_abstract_20530242, ui_category_info_20530242, 
                ui_budget_summary_20530242]:
    if hasattr(router, 'prefix') and router.prefix:
        scheme_registry.register_route_prefix("20530242", router.prefix)

# Scheme 20530242 API router
app.include_router(s20530242_api)
if hasattr(s20530242_api, 'prefix') and s20530242_api.prefix:
    scheme_registry.register_route_prefix("20530242", s20530242_api.prefix)

# Scheme 20530313 UI routers
app.include_router(ui_budget_details_20530313)
app.include_router(ui_post_status_20530313)
app.include_router(ui_post_expenses_20530313)
app.include_router(ui_unit_expenditure_20530313)
app.include_router(ui_abstract_20530313)
app.include_router(ui_category_info_20530313)
app.include_router(ui_budget_summary_20530313)

# Register 20530313 route prefixes from routers
for router in [ui_budget_details_20530313, ui_post_status_20530313, ui_post_expenses_20530313, 
                ui_unit_expenditure_20530313, ui_abstract_20530313, ui_category_info_20530313, 
                ui_budget_summary_20530313]:
    if hasattr(router, 'prefix') and router.prefix:
        scheme_registry.register_route_prefix("20530313", router.prefix)

# Scheme 20530313 API router
app.include_router(s20530313_api)
if hasattr(s20530313_api, 'prefix') and s20530313_api.prefix:
    scheme_registry.register_route_prefix("20530313", s20530313_api.prefix)

# Scheme 20530387 UI routers
app.include_router(ui_budget_details_20530387)
app.include_router(ui_post_status_20530387)
app.include_router(ui_post_expenses_20530387)
app.include_router(ui_unit_expenditure_20530387)
app.include_router(ui_category_info_20530387)
app.include_router(ui_budget_summary_20530387)

# Register 20530387 route prefixes from routers
for router in [ui_budget_details_20530387, ui_post_status_20530387, ui_post_expenses_20530387, 
                ui_unit_expenditure_20530387, ui_category_info_20530387, 
                ui_budget_summary_20530387]:
    if hasattr(router, 'prefix') and router.prefix:
        scheme_registry.register_route_prefix("20530387", router.prefix)

# Scheme 20530387 API router
app.include_router(s20530387_api)
if hasattr(s20530387_api, 'prefix') and s20530387_api.prefix:
    scheme_registry.register_route_prefix("20530387", s20530387_api.prefix)

# Scheme 20290046 UI routers
app.include_router(ui_budget_details_20290046)
app.include_router(ui_post_status_20290046)
app.include_router(ui_post_expenses_20290046)
app.include_router(ui_unit_expenditure_20290046)
app.include_router(ui_abstract_20290046)
app.include_router(ui_category_info_20290046)
app.include_router(ui_budget_summary_20290046)

# Register 20290046 route prefixes from routers
for router in [
    ui_budget_details_20290046,
    ui_post_status_20290046,
    ui_post_expenses_20290046,
    ui_unit_expenditure_20290046,
    ui_abstract_20290046,
    ui_category_info_20290046,
    ui_budget_summary_20290046,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20290046", router.prefix)

# Scheme 20290046 API router
app.include_router(s20290046_api)
if hasattr(s20290046_api, "prefix") and s20290046_api.prefix:
    scheme_registry.register_route_prefix("20290046", s20290046_api.prefix)

# Scheme 20290182 UI routers
app.include_router(ui_budget_details_20290182)
app.include_router(ui_post_status_20290182)
app.include_router(ui_post_expenses_20290182)
app.include_router(ui_unit_expenditure_20290182)
app.include_router(ui_abstract_20290182)
app.include_router(ui_category_info_20290182)
app.include_router(ui_budget_summary_20290182)

# Register 20290182 route prefixes from routers
for router in [
    ui_budget_details_20290182,
    ui_post_status_20290182,
    ui_post_expenses_20290182,
    ui_unit_expenditure_20290182,
    ui_abstract_20290182,
    ui_category_info_20290182,
    ui_budget_summary_20290182,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20290182", router.prefix)

# Scheme 20290182 API router
app.include_router(s20290182_api)
if hasattr(s20290182_api, "prefix") and s20290182_api.prefix:
    scheme_registry.register_route_prefix("20290182", s20290182_api.prefix)

# Scheme 20290262 UI routers
app.include_router(ui_budget_details_20290262)
app.include_router(ui_post_status_20290262)
app.include_router(ui_post_expenses_20290262)
app.include_router(ui_unit_expenditure_20290262)
app.include_router(ui_abstract_20290262)
app.include_router(ui_category_info_20290262)
app.include_router(ui_budget_summary_20290262)

for router in [
    ui_budget_details_20290262, ui_post_status_20290262, ui_post_expenses_20290262,
    ui_unit_expenditure_20290262, ui_abstract_20290262, ui_category_info_20290262,
    ui_budget_summary_20290262,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20290262", router.prefix)

app.include_router(s20290262_api)
if hasattr(s20290262_api, "prefix") and s20290262_api.prefix:
    scheme_registry.register_route_prefix("20290262", s20290262_api.prefix)

# Scheme 20290037 UI routers
app.include_router(ui_budget_details_20290037)
app.include_router(ui_post_status_20290037)
app.include_router(ui_post_expenses_20290037)
app.include_router(ui_unit_expenditure_20290037)
app.include_router(ui_abstract_20290037)
app.include_router(ui_category_info_20290037)
app.include_router(ui_budget_summary_20290037)

for router in [
    ui_budget_details_20290037, ui_post_status_20290037, ui_post_expenses_20290037,
    ui_unit_expenditure_20290037, ui_abstract_20290037, ui_category_info_20290037,
    ui_budget_summary_20290037,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20290037", router.prefix)

app.include_router(s20290037_api)
if hasattr(s20290037_api, "prefix") and s20290037_api.prefix:
    scheme_registry.register_route_prefix("20290037", s20290037_api.prefix)

# Scheme 62450017 routers
app.include_router(s62450017_api)
app.include_router(s62450017_ui)
if hasattr(s62450017_api, 'prefix') and s62450017_api.prefix:
    scheme_registry.register_route_prefix("62450017", s62450017_api.prefix)
if hasattr(s62450017_ui, 'prefix') and s62450017_ui.prefix:
    scheme_registry.register_route_prefix("62450017", s62450017_ui.prefix)

# Scheme 64010018 routers
app.include_router(s64010018_api)
app.include_router(s64010018_ui)
if hasattr(s64010018_api, 'prefix') and s64010018_api.prefix:
    scheme_registry.register_route_prefix("64010018", s64010018_api.prefix)
if hasattr(s64010018_ui, 'prefix') and s64010018_ui.prefix:
    scheme_registry.register_route_prefix("64010018", s64010018_ui.prefix)

# Scheme 7610 sub-scheme routers
app.include_router(s76100149_api)
app.include_router(s76100149_ui)
if hasattr(s76100149_api, 'prefix') and s76100149_api.prefix:
    scheme_registry.register_route_prefix("76100149", s76100149_api.prefix)
if hasattr(s76100149_ui, 'prefix') and s76100149_ui.prefix:
    scheme_registry.register_route_prefix("76100149", s76100149_ui.prefix)

app.include_router(s76100158_api)
app.include_router(s76100158_ui)
if hasattr(s76100158_api, 'prefix') and s76100158_api.prefix:
    scheme_registry.register_route_prefix("76100158", s76100158_api.prefix)
if hasattr(s76100158_ui, 'prefix') and s76100158_ui.prefix:
    scheme_registry.register_route_prefix("76100158", s76100158_ui.prefix)

app.include_router(s76100167_api)
app.include_router(s76100167_ui)
if hasattr(s76100167_api, 'prefix') and s76100167_api.prefix:
    scheme_registry.register_route_prefix("76100167", s76100167_api.prefix)
if hasattr(s76100167_ui, 'prefix') and s76100167_ui.prefix:
    scheme_registry.register_route_prefix("76100167", s76100167_ui.prefix)

app.include_router(s76101871_api)
app.include_router(s76101871_ui)
if hasattr(s76101871_api, 'prefix') and s76101871_api.prefix:
    scheme_registry.register_route_prefix("76101871", s76101871_api.prefix)
if hasattr(s76101871_ui, 'prefix') and s76101871_ui.prefix:
    scheme_registry.register_route_prefix("76101871", s76101871_ui.prefix)

# Scheme 2235 sub-scheme routers
app.include_router(s22353408_api)
app.include_router(s22353408_ui)
if hasattr(s22353408_api, 'prefix') and s22353408_api.prefix:
    scheme_registry.register_route_prefix("22353408", s22353408_api.prefix)
if hasattr(s22353408_ui, 'prefix') and s22353408_ui.prefix:
    scheme_registry.register_route_prefix("22353408", s22353408_ui.prefix)

app.include_router(s22350311_api)
app.include_router(s22350311_ui)
if hasattr(s22350311_api, 'prefix') and s22350311_api.prefix:
    scheme_registry.register_route_prefix("22350311", s22350311_api.prefix)
if hasattr(s22350311_ui, 'prefix') and s22350311_ui.prefix:
    scheme_registry.register_route_prefix("22350311", s22350311_ui.prefix)

app.include_router(s22353195_api)
app.include_router(s22353195_ui)
if hasattr(s22353195_api, 'prefix') and s22353195_api.prefix:
    scheme_registry.register_route_prefix("22353195", s22353195_api.prefix)
if hasattr(s22353195_ui, 'prefix') and s22353195_ui.prefix:
    scheme_registry.register_route_prefix("22353195", s22353195_ui.prefix)

app.include_router(s22350338_api)
app.include_router(s22350338_ui)
if hasattr(s22350338_api, 'prefix') and s22350338_api.prefix:
    scheme_registry.register_route_prefix("22350338", s22350338_api.prefix)
if hasattr(s22350338_ui, 'prefix') and s22350338_ui.prefix:
    scheme_registry.register_route_prefix("22350338", s22350338_ui.prefix)

# Scheme 2075 unified router
app.include_router(s2075_api)
app.include_router(s2075_ui)
if hasattr(s2075_api, 'prefix') and s2075_api.prefix:
    scheme_registry.register_route_prefix("2075", s2075_api.prefix)
if hasattr(s2075_ui, 'prefix') and s2075_ui.prefix:
    scheme_registry.register_route_prefix("2075", s2075_ui.prefix)

app.include_router(s2215_api)
app.include_router(s2215_ui)
if hasattr(s2215_api, 'prefix') and s2215_api.prefix:
    scheme_registry.register_route_prefix("2215", s2215_api.prefix)
if hasattr(s2215_ui, 'prefix') and s2215_ui.prefix:
    scheme_registry.register_route_prefix("2215", s2215_ui.prefix)

app.include_router(s2245_api)
app.include_router(s2245_ui)

app.include_router(s0029_api)
app.include_router(s0029_ui)
if hasattr(s0029_api, 'prefix') and s0029_api.prefix:
    scheme_registry.register_route_prefix("0029", s0029_api.prefix)
if hasattr(s0029_ui, 'prefix') and s0029_ui.prefix:
    scheme_registry.register_route_prefix("0029", s0029_ui.prefix)

if hasattr(s2245_api, 'prefix') and s2245_api.prefix:
    scheme_registry.register_route_prefix("2245", s2245_api.prefix)
if hasattr(s2245_ui, 'prefix') and s2245_ui.prefix:
    scheme_registry.register_route_prefix("2245", s2245_ui.prefix)

# Redirect handlers for old shared URLs to scheme-aware URLs
from src.utils_scheme import get_current_scheme_code
from typing import Optional

def _get_default_scheme_code() -> Optional[str]:
    """Get first implemented scheme code as fallback"""
    implemented = scheme_registry.get_implemented_schemes()
    return next(iter(implemented.keys()), None) if implemented else None

@app.get("/ui/shashan-niryan", include_in_schema=False)
async def redirect_shashan_niryan(request: Request):
    scheme_code = get_current_scheme_code(request) or _get_default_scheme_code()
    if not scheme_code:
        return RedirectResponse(url="/ui/scheme-selection", status_code=307)
    return RedirectResponse(url=f"/ui/s{scheme_code}/shashan-niryan", status_code=307)

@app.get("/ui/taluka-selection", include_in_schema=False)
async def redirect_taluka_selection(request: Request):
    scheme_code = get_current_scheme_code(request) or _get_default_scheme_code()
    if not scheme_code:
        return RedirectResponse(url="/ui/scheme-selection", status_code=307)
    return RedirectResponse(url=f"/ui/s{scheme_code}/taluka-selection", status_code=307)

@app.get("/timing/manage", include_in_schema=False)
async def redirect_timing_manage(request: Request):
    scheme_code = get_current_scheme_code(request) or _get_default_scheme_code()
    if not scheme_code:
        return RedirectResponse(url="/ui/scheme-selection", status_code=307)
    return RedirectResponse(url=f"/ui/s{scheme_code}/timing-management", status_code=307)

@app.get("/warnings", include_in_schema=False)
async def redirect_warnings(request: Request):
    scheme_code = get_current_scheme_code(request) or _get_default_scheme_code()
    if not scheme_code:
        return RedirectResponse(url="/ui/scheme-selection", status_code=307)
    return RedirectResponse(url=f"/ui/s{scheme_code}/warnings", status_code=307)

@app.get("/settings", include_in_schema=False)
async def redirect_settings(request: Request):
    scheme_code = get_current_scheme_code(request) or _get_default_scheme_code()
    if not scheme_code:
        return RedirectResponse(url="/ui/scheme-selection", status_code=307)
    return RedirectResponse(url=f"/ui/s{scheme_code}/settings", status_code=307)

# Backward compatibility redirects for 20530028 old generic URLs
@app.get("/ui/budget-post-details", include_in_schema=False)
async def redirect_budget_post_details(request: Request):
    return RedirectResponse(url="/ui/s20530028/budget-post-details" + (f"?{request.url.query}" if request.url.query else ""), status_code=307)

@app.get("/ui/post-status", include_in_schema=False)
async def redirect_post_status(request: Request):
    return RedirectResponse(url="/ui/s20530028/post-status" + (f"?{request.url.query}" if request.url.query else ""), status_code=307)

@app.get("/ui/post-expenses", include_in_schema=False)
async def redirect_post_expenses(request: Request):
    return RedirectResponse(url="/ui/s20530028/post-expenses" + (f"?{request.url.query}" if request.url.query else ""), status_code=307)

@app.get("/ui/unit-expenditure", include_in_schema=False)
async def redirect_unit_expenditure(request: Request):
    return RedirectResponse(url="/ui/s20530028/unit-expenditure" + (f"?{request.url.query}" if request.url.query else ""), status_code=307)

@app.get("/ui/district-wise-abstract", include_in_schema=False)
async def redirect_district_wise_abstract(request: Request):
    return RedirectResponse(url="/ui/s20530028/district-wise-abstract" + (f"?{request.url.query}" if request.url.query else ""), status_code=307)

@app.get("/ui/category-wise-info", include_in_schema=False)
async def redirect_category_wise_info(request: Request):
    return RedirectResponse(url="/ui/s20530028/category-wise-info" + (f"?{request.url.query}" if request.url.query else ""), status_code=307)

@app.get("/ui/budget-summary", include_in_schema=False)
async def redirect_budget_summary(request: Request):
    return RedirectResponse(url="/ui/s20530028/budget-summary" + (f"?{request.url.query}" if request.url.query else ""), status_code=307)


# Scheme 20450091 UI routers
app.include_router(ui_budget_details_20450091)
app.include_router(ui_post_status_20450091)
app.include_router(ui_post_expenses_20450091)
app.include_router(ui_unit_expenditure_20450091)
app.include_router(ui_abstract_20450091)
app.include_router(ui_category_info_20450091)
app.include_router(ui_budget_summary_20450091)

# Register 20450091 route prefixes from routers
for router in [
    ui_budget_details_20450091,
    ui_post_status_20450091,
    ui_post_expenses_20450091,
    ui_unit_expenditure_20450091,
    ui_abstract_20450091,
    ui_category_info_20450091,
    ui_budget_summary_20450091,
]:
    if hasattr(router, "prefix") and router.prefix:
        scheme_registry.register_route_prefix("20450091", router.prefix)

# Scheme 20450091 API router
app.include_router(s20450091_api)
if hasattr(s20450091_api, "prefix") and s20450091_api.prefix:
    scheme_registry.register_route_prefix("20450091", s20450091_api.prefix)

# Scheme 20450182 routers
app.include_router(s20450182_api)
app.include_router(s20450182_ui)
if hasattr(s20450182_api, 'prefix') and s20450182_api.prefix:
    scheme_registry.register_route_prefix("20450182", s20450182_api.prefix)
if hasattr(s20450182_ui, 'prefix') and s20450182_ui.prefix:
    scheme_registry.register_route_prefix("20450182", s20450182_ui.prefix)

# Scheme 20450251 routers
app.include_router(s20450251_api)
app.include_router(s20450251_ui)
if hasattr(s20450251_api, 'prefix') and s20450251_api.prefix:
    scheme_registry.register_route_prefix("20450251", s20450251_api.prefix)
if hasattr(s20450251_ui, 'prefix') and s20450251_ui.prefix:
    scheme_registry.register_route_prefix("20450251", s20450251_ui.prefix)

# Scheme 20450262 routers
app.include_router(s20450262_api)
app.include_router(s20450262_ui)
if hasattr(s20450262_api, 'prefix') and s20450262_api.prefix:
    scheme_registry.register_route_prefix("20450262", s20450262_api.prefix)
if hasattr(s20450262_ui, 'prefix') and s20450262_ui.prefix:
    scheme_registry.register_route_prefix("20450262", s20450262_ui.prefix)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_login_page(request: Request):
    return render(request, "login.html", {})

@app.get("/health", include_in_schema=False)
async def health_check(request: Request, _=Depends(verify_api_auth)):
    return {"status": "healthy"}

@app.get("/export-health", include_in_schema=False)
async def export_health_check(request: Request, _=Depends(verify_api_auth)):
    from src.schemes.common.excel_export import get_export_health
    return get_export_health()

@app.on_event("startup")
async def startup_event():
    logging.info("Application startup complete")
    
@app.on_event("shutdown")
async def shutdown_event():
    executor.shutdown(wait=False, cancel_futures=True)
    logging.info("Application shutdown")
