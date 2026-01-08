"""
Centralized Excel Export Service for high-load production environments.

This module provides a production-grade Excel export service designed for
500+ concurrent users. It implements:

1. Request throttling with semaphore to prevent memory exhaustion
2. Memory-efficient streaming generation
3. Timeout protection for long-running exports
4. Consistent cache-busting headers
5. Centralized error handling and logging

Architecture:
    All subschemes MUST use this service instead of implementing their own
    export logic. This ensures consistent behavior and resource management.

Example usage:
    from src.schemes.common.excel_export import ExcelExportService
    
    result = await ExcelExportService.export_with_throttle(
        export_fn=lambda: generate_workbook(db, params),
        filename="budget_report",
        fiscal_year="2025-26"
    )
"""
import io
import time
import asyncio
import logging
from functools import wraps
from typing import Callable, Optional, Any, Union, Dict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from starlette.responses import StreamingResponse
from openpyxl import Workbook

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - Tune these for your production environment
# ============================================================================

# Maximum concurrent Excel export operations
# Prevents memory exhaustion with 500+ concurrent users
MAX_CONCURRENT_EXPORTS = 10

# Timeout for export operations (seconds)
EXPORT_TIMEOUT_SECONDS = 60

# Thread pool for CPU-bound Excel generation
_export_executor = ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_EXPORTS,
    thread_name_prefix="excel_export"
)

# Semaphore for throttling concurrent exports
_export_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXPORTS)

# Track active exports for monitoring
_active_exports: Dict[str, float] = {}


# ============================================================================
# CONSTANTS
# ============================================================================

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_no_cache_headers() -> Dict[str, str]:
    """
    Get standard no-cache headers for responses.
    
    Critical for Excel exports to prevent browsers from serving stale
    cached versions when users switch fiscal years or accounts.
    
    Returns:
        Dict with cache-prevention headers.
    """
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Content-Type-Options": "nosniff"
    }


def build_filename(base_filename: str, fiscal_year: Optional[str] = None) -> str:
    """
    Build cache-busted filename with fiscal year and timestamp.
    
    Args:
        base_filename: Base name without extension
        fiscal_year: Optional fiscal year (e.g., "2025-26")
    
    Returns:
        Complete filename with .xlsx extension
    """
    parts = [base_filename]
    
    if fiscal_year:
        # Sanitize for filesystem
        safe_fy = fiscal_year.replace("/", "-").replace("\\", "-")
        parts.append(safe_fy)
    
    # Add timestamp for cache busting
    parts.append(str(int(time.time())))
    
    return "_".join(parts) + ".xlsx"


# ============================================================================
# CORE EXPORT SERVICE
# ============================================================================

class ExcelExportService:
    """
    Production-grade Excel export service with concurrency control.
    
    This service ensures the system remains stable under high load by:
    1. Limiting concurrent exports via semaphore
    2. Running CPU-intensive operations in thread pool
    3. Providing timeouts for long-running operations
    4. Standardizing response headers
    """
    
    @staticmethod
    async def export_with_throttle(
        export_fn: Callable[[], Union[Workbook, io.BytesIO, bytes]],
        filename: str,
        fiscal_year: Optional[str] = None,
        timeout: int = EXPORT_TIMEOUT_SECONDS,
        request_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        Execute export with concurrency throttling and timeout.
        
        This is the PRIMARY method all export endpoints should use.
        It handles resource management, error handling, and response creation.
        
        Args:
            export_fn: Callable that returns Workbook, BytesIO, or bytes.
                       This function runs in a thread pool.
            filename: Base filename for download (without extension)
            fiscal_year: Optional fiscal year for filename
            timeout: Maximum seconds to wait for export
            request_id: Optional ID for tracking/logging
        
        Returns:
            StreamingResponse with proper headers
        
        Raises:
            TimeoutError: If export exceeds timeout
            MemoryError: If system is under too much load
            RuntimeError: For other export failures
        
        Example:
            async def export_budget(request, db):
                def generate():
                    wb = Workbook()
                    populate_budget_data(wb, db)
                    output = io.BytesIO()
                    wb.save(output)
                    return output
                
                return await ExcelExportService.export_with_throttle(
                    export_fn=generate,
                    filename="budget_report",
                    fiscal_year="2025-26"
                )
        """
        export_id = request_id or f"export_{int(time.time() * 1000)}"
        
        # Check if we can acquire a slot
        if not _export_semaphore.locked() or _export_semaphore._value > 0:
            async with _export_semaphore:
                return await ExcelExportService._execute_export(
                    export_fn, filename, fiscal_year, timeout, export_id
                )
        else:
            # Too many concurrent exports - return 503
            logger.warning(f"Export throttled: {export_id}, active: {len(_active_exports)}")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Server is busy processing other exports. Please try again in a few seconds."
            )
    
    @staticmethod
    async def _execute_export(
        export_fn: Callable,
        filename: str,
        fiscal_year: Optional[str],
        timeout: int,
        export_id: str
    ) -> StreamingResponse:
        """Internal method to execute export with tracking."""
        _active_exports[export_id] = time.time()
        
        try:
            # Run CPU-intensive export in thread pool
            loop = asyncio.get_event_loop()
            
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(_export_executor, export_fn),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Export timeout: {export_id} after {timeout}s")
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=504,
                    detail=f"Export operation timed out after {timeout} seconds"
                )
            
            # Convert result to bytes if needed
            if isinstance(result, Workbook):
                output = io.BytesIO()
                result.save(output)
                output.seek(0)
                content = output
            elif isinstance(result, io.BytesIO):
                result.seek(0)
                content = result
            elif isinstance(result, bytes):
                content = io.BytesIO(result)
            else:
                raise RuntimeError(f"Unexpected export result type: {type(result)}")
            
            # Build response
            full_filename = build_filename(filename, fiscal_year)
            headers = get_no_cache_headers()
            headers["Content-Disposition"] = f'attachment; filename="{full_filename}"'
            
            logger.info(
                f"Export completed: {export_id}, "
                f"duration: {time.time() - _active_exports[export_id]:.2f}s"
            )
            
            return StreamingResponse(
                content=content,
                headers=headers,
                media_type=EXCEL_MEDIA_TYPE
            )
            
        except Exception as e:
            logger.error(f"Export failed: {export_id}, error: {e}", exc_info=True)
            raise
        finally:
            _active_exports.pop(export_id, None)
    
    @staticmethod
    def create_response(
        content: Union[io.BytesIO, bytes],
        base_filename: str,
        fiscal_year: Optional[str] = None
    ) -> StreamingResponse:
        """
        Create streaming response for Excel download (synchronous version).
        
        Use this for simple exports that don't need throttling.
        For production endpoints with high traffic, use export_with_throttle instead.
        
        Args:
            content: BytesIO or bytes containing Excel data
            base_filename: Base filename without extension
            fiscal_year: Optional fiscal year for filename
        
        Returns:
            StreamingResponse with cache-prevention headers
        """
        full_filename = build_filename(base_filename, fiscal_year)
        headers = get_no_cache_headers()
        headers["Content-Disposition"] = f'attachment; filename="{full_filename}"'
        
        if isinstance(content, io.BytesIO):
            content.seek(0)
        elif isinstance(content, bytes):
            content = io.BytesIO(content)
        
        return StreamingResponse(
            content=content,
            headers=headers,
            media_type=EXCEL_MEDIA_TYPE
        )
    
    @staticmethod
    def get_active_export_count() -> int:
        """Get number of currently active exports (for monitoring)."""
        return len(_active_exports)
    
    @staticmethod
    def get_available_slots() -> int:
        """Get number of available export slots (for monitoring)."""
        return _export_semaphore._value


# ============================================================================
# DECORATOR FOR SIMPLE INTEGRATION
# ============================================================================

def throttled_export(filename: str, fiscal_year_param: str = "fiscal_year"):
    """
    Decorator to wrap export endpoints with throttling.
    
    Args:
        filename: Base filename for the export
        fiscal_year_param: Name of the fiscal_year parameter in the function
    
    Example:
        @throttled_export("budget_report")
        async def export_budget(request, db, fiscal_year):
            wb = Workbook()
            populate_data(wb, db)
            output = io.BytesIO()
            wb.save(output)
            return output  # Return BytesIO, service handles response
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            fiscal_year = kwargs.get(fiscal_year_param)
            
            # Create export function that captures args
            def export_fn():
                # For async functions, we need special handling
                if asyncio.iscoroutinefunction(func):
                    loop = asyncio.new_event_loop()
                    try:
                        return loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
                else:
                    return func(*args, **kwargs)
            
            return await ExcelExportService.export_with_throttle(
                export_fn=export_fn,
                filename=filename,
                fiscal_year=fiscal_year
            )
        return wrapper
    return decorator


# ============================================================================
# HEALTH CHECK / MONITORING
# ============================================================================

def get_export_health() -> Dict[str, Any]:
    """
    Get health status of the export service.
    
    Returns dict with:
        - active_exports: Number of currently running exports
        - available_slots: Number of free slots
        - max_concurrent: Maximum allowed concurrent exports
        - status: "healthy", "busy", or "overloaded"
    """
    active = len(_active_exports)
    available = _export_semaphore._value
    
    if available > MAX_CONCURRENT_EXPORTS * 0.5:
        status = "healthy"
    elif available > 0:
        status = "busy"
    else:
        status = "overloaded"
    
    return {
        "active_exports": active,
        "available_slots": available,
        "max_concurrent": MAX_CONCURRENT_EXPORTS,
        "status": status,
        "active_export_ids": list(_active_exports.keys())
    }
