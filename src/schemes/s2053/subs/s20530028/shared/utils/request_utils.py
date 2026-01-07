"""Request utility functions"""
from typing import Dict
from fastapi import Request
from src.utils_district import get_request_info as _get_request_info_centralized


def get_request_info(request: Request) -> Dict[str, str]:
    """Extract request information for audit logging (delegates to centralized utility)."""
    return _get_request_info_centralized(request)

