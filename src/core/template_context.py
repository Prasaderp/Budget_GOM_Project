"""Shared template context utilities for consistent auth variable passing."""
from typing import Dict
from fastapi import Request


def get_standard_template_context(request: Request) -> Dict[str, str]:
    """
    Returns standard authentication context variables required by base.html.
    
    This ensures all templates receive consistent auth variables for proper
    navigation link rendering and access control checks.
    
    Args:
        request: FastAPI Request object containing cookies
        
    Returns:
        Dictionary with auth_level, auth_role, auth_unit, auth_user keys
    """
    return {
        "auth_level": request.cookies.get("auth_level", ""),
        "auth_role": request.cookies.get("auth_role", ""),
        "auth_unit": request.cookies.get("auth_unit", ""),
        "auth_user": request.cookies.get("auth_user", ""),
    }
