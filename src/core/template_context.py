"""Shared template context utilities for consistent auth variable passing."""
from typing import Dict
from fastapi import Request
from src.utils_auth import get_auth_user, get_auth_level, get_auth_role, get_auth_unit


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
        "auth_level": get_auth_level(request),
        "auth_role": get_auth_role(request),
        "auth_unit": get_auth_unit(request),
        "auth_user": get_auth_user(request),
    }
