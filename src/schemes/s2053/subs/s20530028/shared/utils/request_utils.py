"""Request utility functions"""
from typing import Dict
from fastapi import Request


def get_request_info(request: Request) -> Dict[str, str]:
    """
    Extract request information for audit logging
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Dict with request information
    """
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return {
        "level": request.cookies.get('auth_level', ''),
        "role": request.cookies.get('auth_role', ''),
        "unit": request.cookies.get('auth_unit', ''),
        "ip": ip,
        "ua": request.headers.get("user-agent", "")[:200],
        "sid": request.cookies.get("session_id", "")
    }

