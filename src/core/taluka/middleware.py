"""Request-scoped installation of the caller's DataScope (Phase 2).

Mirrors AuditMiddleware's shape (src/audit_middleware.py) exactly: a
BaseHTTPMiddleware that sets state on the way in and guarantees cleanup via
`finally` on the way out, regardless of how the downstream handler exits.

Must run before AuditMiddleware and before any handler code so the scope is
in place for every ORM query the request issues, including ones made by
AuditMiddleware itself. See src/main.py for the registration-order note —
Starlette's add_middleware inserts each new middleware at the front of the
stack, so this must be registered *after* AuditMiddleware to end up
executing *before* it.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.taluka.scope import resolve_scope_from_request, set_scope, reset_scope


class TalukaScopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        scope = resolve_scope_from_request(request)
        token = set_scope(scope)
        try:
            return await call_next(request)
        finally:
            reset_scope(token)
