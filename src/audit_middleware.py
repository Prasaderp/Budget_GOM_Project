from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from src.database import SessionLocal
from src.audit_service import AuditService
import time
import logging

logger = logging.getLogger(__name__)
_SLOW_THRESHOLD_MS = 500


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.sensitive_paths = {'/api/login', '/admin/login', '/api/logout', '/admin/logout'}
        self.export_paths = {
            '/ui/budget-details/export-excel', '/ui/post-status/summary/export-excel', 
            '/ui/post-expenses/summary/export-excel', '/ui/unit-expenditure/export-excel'
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        path = request.url.path
        
        should_audit = (
            request.method in ['POST', 'PUT', 'DELETE'] or
            path in self.sensitive_paths or
            any(ep in path for ep in self.export_paths)
        )
        
        if should_audit:
            await self.log_request(request)
        
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # log slow requests
        if elapsed_ms > _SLOW_THRESHOLD_MS:
            logger.warning(f"SLOW_REQUEST: {request.method} {path} took {elapsed_ms:.1f}ms")
        
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        
        if should_audit and response.status_code < 400:
            await self.log_response(request, response, elapsed_ms / 1000)
        
        return response

    async def log_request(self, request: Request):
        try:
            db = SessionLocal()
            
            path = request.url.path
            method = request.method
            username = request.cookies.get("auth_user", "anonymous")
            
            if path in self.sensitive_paths:
                if 'login' in path and method == 'POST':
                    pass
                elif 'logout' in path and method == 'POST':
                    AuditService.log_action(
                        db=db,
                        request=request,
                        action='LOGOUT',
                        table_name='users',
                        record_id=0
                    )
                    db.commit()
            
            db.close()
        except Exception as e:
            print(f"Audit request logging error: {e}")

    async def log_response(self, request: Request, response: Response, duration: float):
        try:
            db = SessionLocal()
            path = request.url.path
            
            if any(export_path in path for export_path in self.export_paths):
                export_type = self.get_export_type(path)
                AuditService.log_export(
                    db=db,
                    request=request,
                    export_type=export_type
                )
                db.commit()
            
            db.close()
        except Exception as e:
            print(f"Audit response logging error: {e}")

    def get_export_type(self, path: str) -> str:
        if 'budget-details' in path:
            return 'budget_post_details'
        elif 'post-status' in path:
            return 'post_status'
        elif 'post-expenses' in path:
            return 'post_expenses'
        elif 'unit-expenditure' in path:
            return 'unit_expenditure'
        else:
            return 'unknown_export'
