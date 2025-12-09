"""Response utility functions"""
from typing import Dict


def get_no_cache_headers() -> Dict[str, str]:
    """
    Get standard no-cache headers for responses
    
    Returns:
        Dict with no-cache headers
    """
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

