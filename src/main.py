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

from src.routers import ui_budget_details, ui_post_status, ui_post_expenses, ui_unit_expenditure, ui_abstract, ui_category_info, ui_budget_summary, ui_shashan_niryan
from src.routers import api_assistant
from src.routers import auth
from src.routers import admin
from src.routers import messages
from src.routers import ui_taluka_selection
from src.routers import ui_scheme_selection
from src.routers import timing_management
from src.routers import warnings
from src.routers import fiscal_year
from src.routers import training
from src.routers import settings
from src.audit_middleware import AuditMiddleware

is_production = os.getenv("ENVIRONMENT", "development") == "production"

app = FastAPI(
    title="Budget Management System",
    description="Government Budget Management System",
    version="1.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json"
)

templates = Jinja2Templates(directory="templates")
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

SCHEME_REQUIRED_PATHS = ('/ui/budget', '/ui/post-status', '/ui/post-expenses', '/ui/unit-expenditure', 
                         '/ui/abstract', '/ui/category-info', '/ui/shashan-niryan')

@app.middleware("http")
async def require_auth_for_ui(request: Request, call_next):
    path = request.url.path
    if path.startswith("/ui/"):
        auth_user = request.cookies.get("auth_user")
        if not auth_user:
            return RedirectResponse(url='/', status_code=303)
        if request.cookies.get("auth_role") == 'admin':
            return RedirectResponse(url='/admin/users', status_code=303)
        # Require scheme selection for budget-related routes
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

app.include_router(ui_scheme_selection.router)
app.include_router(ui_scheme_selection.placeholder_router)
app.include_router(ui_budget_details.router)
app.include_router(ui_post_status.router)
app.include_router(ui_post_expenses.router)
app.include_router(ui_unit_expenditure.router)
app.include_router(ui_abstract.router)
app.include_router(ui_category_info.router)
app.include_router(ui_budget_summary.router)
app.include_router(ui_shashan_niryan.router) 
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