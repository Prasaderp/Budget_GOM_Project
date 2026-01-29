"""Response utility functions for HTTP responses and Excel exports.

This module provides centralized response creation utilities to ensure
consistent cache control and security headers across all endpoints.
"""
import io
import time
from typing import Dict, Optional, Union
from starlette.responses import StreamingResponse


# Constants
EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def get_no_cache_headers() -> Dict[str, str]:
    """
    Get standard no-cache headers for responses.
    
    Returns:
        Dict with cache-prevention headers for HTTP responses.
    """
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }


def create_excel_response(
    content: Union[io.BytesIO, bytes],
    base_filename: str,
    fiscal_year: Optional[str] = None,
    include_timestamp: bool = True
) -> StreamingResponse:
    """
    Create a cache-safe StreamingResponse for Excel file downloads.
    
    This is the SINGLE source of truth for all Excel exports in the application.
    It ensures:
    1. Proper cache-prevention headers to avoid stale data issues
    2. Dynamic filename with fiscal year and timestamp for cache-busting
    3. Correct MIME type for xlsx files
    
    Args:
        content: BytesIO or bytes object containing the Excel file data.
        base_filename: Base name for the file (without extension).
        fiscal_year: Optional fiscal year to embed in filename (e.g., "2025-26").
        include_timestamp: If True, append Unix timestamp to filename.
    
    Returns:
        StreamingResponse configured for secure Excel download.
    
    Example:
        >>> output = io.BytesIO()
        >>> workbook.save(output)
        >>> output.seek(0)
        >>> return create_excel_response(output, "budget_report", fiscal_year="2025-26")
        # Downloads as: budget_report_2025-26_1736353738.xlsx
    """
    # Build dynamic filename with cache-busting components
    filename_parts = [base_filename]
    
    if fiscal_year:
        # Sanitize fiscal year for filename (replace invalid chars)
        safe_fy = fiscal_year.replace("/", "-").replace("\\", "-")
        filename_parts.append(safe_fy)
    
    if include_timestamp:
        filename_parts.append(str(int(time.time())))
    
    filename = "_".join(filename_parts) + ".xlsx"
    
    # Merge cache-prevention headers with content-disposition
    headers = get_no_cache_headers()
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    # Ensure content is seeked to start if BytesIO
    if isinstance(content, io.BytesIO):
        content.seek(0)
    
    return StreamingResponse(
        content=content,
        headers=headers,
        media_type=EXCEL_MEDIA_TYPE
    )

