import sys
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from src.utils_static import OptimizedStaticFiles
from fastapi.templating import Jinja2Templates
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

# Shared routers (used across all schemes)
from src.routers import api_assistant, auth, admin, messages, ui_taluka_selection
from src.routers import ui_scheme_selection, timing_management, warnings, fiscal_year, training, settings
from src.routers import ui_shashan_niryan
from src.audit_middleware import AuditMiddleware

# Scheme-specific routers for 20530028
from src.schemes.s2053.subs.s20530028 import (
    api_router as s20530028_api,
    budget_details_router as ui_budget_details,
    post_status_router as ui_post_status,
    post_expenses_router as ui_post_expenses,
    unit_expenditure_router as ui_unit_expenditure,
    budget_summary_router as ui_budget_summary,
    abstract_router as ui_abstract,
    category_info_router as ui_category_info
)
from src.core.registry import scheme_registry
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

is_production = os.getenv("ENVIRONMENT", "development") == "production"

app = FastAPI(
    title="Budget Management System",
    description="Government Budget Management System",
    version="1.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json"
)

from src.core.templates import templates

app.mount("/static", OptimizedStaticFiles(directory="static"), name="static")
app.mount("/docs", OptimizedStaticFiles(directory="docs"), name="docs")

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
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
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" if request.method != "GET" else "public, max-age=60"
            response.headers["Vary"] = "Accept-Encoding"
        elif path in ["/", "/admin/login"]:
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        else:
            response.headers["Cache-Control"] = "private, max-age=30"

        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        })

        return response

app.add_middleware(PerformanceMiddleware)
app.add_middleware(AuditMiddleware)

SCHEME_REQUIRED_PATHS = ('/ui/shashan-niryan', '/ui/taluka-selection',
                         '/ui/timing-management', '/ui/warnings', '/ui/settings')

@app.middleware("http")
async def require_auth_for_ui(request: Request, call_next):
    path = request.url.path
    if path.startswith("/ui/"):
        auth_user = request.cookies.get("auth_user")
        if not auth_user:
            return RedirectResponse(url='/', status_code=303)
        if request.cookies.get("auth_role") == 'admin':
            return RedirectResponse(url='/admin/users', status_code=303)
        
        import re
        scheme_in_path = re.search(r'/ui/s(\d{8})/', path)
        if not scheme_in_path:
            if any(path.startswith(p) for p in SCHEME_REQUIRED_PATHS):
                if not request.cookies.get("selected_sub_scheme"):
                    return RedirectResponse(url='/ui/scheme-selection', status_code=303)
    elif path.startswith('/admin') and path != '/admin/login':
        role = request.cookies.get("auth_role", '')
        admin_sess = request.cookies.get("admin_user", '')
        if role != 'admin' and not admin_sess:
            return RedirectResponse(url='/admin/login', status_code=303)
    return await call_next(request)

if os.getenv("RUN_DB_CREATE_ALL", "true").lower() in {"1", "true", "yes"}:
    models.Base.metadata.create_all(bind=engine)
    run_database_migrations()
    db = SessionLocal()
    try:
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
app.include_router(timing_management.router)
app.include_router(warnings.router)
app.include_router(fiscal_year.router)
app.include_router(training.router)
app.include_router(settings.router)
app.include_router(ui_shashan_niryan.router)

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


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/health", include_in_schema=False)
async def health_check():
    cache_stats = memory_cache.get_stats()
    return {
        "status": "healthy",
        "cache": cache_stats
    }

@app.on_event("startup")
async def startup_event():
    logging.info("Application startup complete")
    
@app.on_event("shutdown")
async def shutdown_event():
    executor.shutdown(wait=False, cancel_futures=True)
    logging.info("Application shutdown")
