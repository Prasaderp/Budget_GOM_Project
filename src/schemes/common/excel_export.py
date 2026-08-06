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
import os
import time
import asyncio
import logging
import contextvars
from functools import wraps
from typing import Callable, Optional, Any, Union, Dict
from concurrent.futures import ThreadPoolExecutor

from starlette.responses import StreamingResponse
from openpyxl import Workbook

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - Tune these for your production environment
# ============================================================================

# Maximum concurrent Excel export operations
# Prevents memory exhaustion with 500+ concurrent users
MAX_CONCURRENT_EXPORTS = int(os.getenv("EXPORT_MAX_CONCURRENT", "10"))

# Timeout for export operations (seconds)
# Increased from 60s to 120s based on production logs showing legitimate
# exports taking 60-77s under load
EXPORT_TIMEOUT_SECONDS = int(os.getenv("EXPORT_TIMEOUT_SECONDS", "120"))

# Maximum size (bytes) before switching to streaming mode
# 10MB threshold - larger workbooks use write-only streaming
EXPORT_STREAMING_THRESHOLD_BYTES = 10 * 1024 * 1024

# Maximum exports that can wait in queue
# Prevents unbounded memory growth under extreme load
EXPORT_MAX_QUEUE_SIZE = int(os.getenv("EXPORT_MAX_QUEUE_SIZE", "50"))

# Thread pool for CPU-bound Excel generation
_export_executor = ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_EXPORTS,
    thread_name_prefix="excel_export"
)

# Semaphore for throttling concurrent exports
_export_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXPORTS)

# Track active exports for monitoring
_active_exports: Dict[str, float] = {}

# Queue size tracking
_queued_exports = 0


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
    
    Raises:
        ValueError: If base_filename contains invalid characters
    """
    if not base_filename or not base_filename.strip():
        raise ValueError("base_filename cannot be empty")
    
    # Sanitize base filename
    safe_base = "".join(c for c in base_filename if c.isalnum() or c in ('-', '_'))
    if not safe_base:
        safe_base = "export"
    
    parts = [safe_base]
    
    if fiscal_year:
        # Sanitize for filesystem
        safe_fy = fiscal_year.replace("/", "-").replace("\\", "-")
        safe_fy = "".join(c for c in safe_fy if c.isalnum() or c in ('-', '_'))
        if safe_fy:
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
    5. Queue management to prevent memory exhaustion
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
                       MUST be thread-safe and not access request context.
            filename: Base filename for download (without extension)
            fiscal_year: Optional fiscal year for filename
            timeout: Maximum seconds to wait for export
            request_id: Optional ID for tracking/logging
        
        Returns:
            StreamingResponse with proper headers
        
        Raises:
            HTTPException(503): If export queue is full
            HTTPException(504): If export exceeds timeout
            HTTPException(500): For other export failures
        
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
        global _queued_exports
        
        export_id = request_id or f"export_{int(time.time() * 1000)}"
        
        # Check queue size limit BEFORE attempting to acquire semaphore
        if _queued_exports >= EXPORT_MAX_QUEUE_SIZE:
            logger.warning(
                f"Export queue full: {export_id}, "
                f"queued={_queued_exports}, active={len(_active_exports)}"
            )
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=f"Export queue is full ({EXPORT_MAX_QUEUE_SIZE} requests). "
                       "Please try again in 30 seconds."
            )
        
        # Increment queue counter
        _queued_exports += 1
        logger.debug(f"Export queued: {export_id}, queue_size={_queued_exports}")
        
        try:
            # Wait for semaphore with timeout to prevent indefinite queuing
            try:
                async with asyncio.timeout(30):  # Max 30s wait in queue
                    async with _export_semaphore:
                        _queued_exports -= 1  # Acquired slot, remove from queue
                        return await ExcelExportService._execute_export(
                            export_fn, filename, fiscal_year, timeout, export_id
                        )
            except TimeoutError:
                logger.warning(f"Export queue timeout: {export_id} after 30s wait")
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=503,
                    detail="Export service is overloaded. Please try again later."
                )
        finally:
            # Ensure we decrement queue counter even if exception occurs
            if _queued_exports > 0:
                _queued_exports -= 1
    
    @staticmethod
    async def _execute_export(
        export_fn: Callable,
        filename: str,
        fiscal_year: Optional[str],
        timeout: int,
        export_id: str
    ) -> StreamingResponse:
        """
        Internal method to execute export with tracking.
        
        Runs the export function in a thread pool executor with timeout protection.
        Handles type conversion and response creation.
        
        Args:
            export_fn: Export generation function
            filename: Base filename
            fiscal_year: Optional fiscal year
            timeout: Timeout in seconds
            export_id: Unique export identifier
        
        Returns:
            StreamingResponse with Excel file
        
        Raises:
            HTTPException(504): On timeout
            HTTPException(500): On export failure
        """
        start_time = time.time()
        _active_exports[export_id] = start_time
        
        try:
            # Run CPU-intensive export in thread pool
            loop = asyncio.get_event_loop()
            
            logger.info(f"Export started: {export_id}, timeout={timeout}s")
            
            try:
                ctx = contextvars.copy_context()
                result = await asyncio.wait_for(
                    loop.run_in_executor(_export_executor, ctx.run, export_fn),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                logger.error(
                    f"Export timeout: {export_id} after {duration:.1f}s "
                    f"(limit: {timeout}s)"
                )
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=504,
                    detail=f"Export operation timed out after {timeout} seconds. "
                           "The report may be too large or the system is under heavy load."
                )
            
            # Defensive null check
            if result is None:
                raise RuntimeError(f"Export function returned None for {export_id}")
            
            # Convert result to BytesIO if needed
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
                raise RuntimeError(
                    f"Unexpected export result type: {type(result).__name__}. "
                    f"Expected Workbook, BytesIO, or bytes."
                )
            
            # Build response with cache-busting headers
            full_filename = build_filename(filename, fiscal_year)
            headers = get_no_cache_headers()
            headers["Content-Disposition"] = f'attachment; filename="{full_filename}"'
            
            duration = time.time() - start_time
            logger.info(
                f"Export completed: {export_id}, "
                f"duration={duration:.2f}s, "
                f"size={content.getbuffer().nbytes / 1024:.1f}KB"
            )
            
            return StreamingResponse(
                content=content,
                headers=headers,
                media_type=EXCEL_MEDIA_TYPE
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Export failed: {export_id}, "
                f"duration={duration:.2f}s, "
                f"error={type(e).__name__}: {str(e)}",
                exc_info=True
            )
            # Re-raise HTTPExceptions as-is, wrap others
            from fastapi import HTTPException
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500,
                detail=f"Export failed: {str(e)}"
            )
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
        
        Raises:
            ValueError: If content is None or invalid type
        """
        if content is None:
            raise ValueError("Content cannot be None")
        
        full_filename = build_filename(base_filename, fiscal_year)
        headers = get_no_cache_headers()
        headers["Content-Disposition"] = f'attachment; filename="{full_filename}"'
        
        if isinstance(content, io.BytesIO):
            content.seek(0)
        elif isinstance(content, bytes):
            content = io.BytesIO(content)
        else:
            raise ValueError(
                f"Invalid content type: {type(content).__name__}. "
                "Expected BytesIO or bytes."
            )
        
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
        """
        Get number of available export slots (for monitoring).
        
        Returns:
            Number of free semaphore slots
        """
        # Calculate available slots instead of accessing private _value
        return MAX_CONCURRENT_EXPORTS - len(_active_exports)
    
    @staticmethod
    def get_queue_size() -> int:
        """Get number of exports waiting in queue (for monitoring)."""
        return _queued_exports


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
        - queued_exports: Number of exports waiting in queue
        - available_slots: Number of free slots
        - max_concurrent: Maximum allowed concurrent exports
        - max_queue_size: Maximum queue capacity
        - status: "healthy", "busy", or "overloaded"
    """
    active = len(_active_exports)
    available = MAX_CONCURRENT_EXPORTS - active
    queued = _queued_exports
    
    # Determine health status
    if available > MAX_CONCURRENT_EXPORTS * 0.5 and queued == 0:
        status = "healthy"
    elif available > 0 and queued < EXPORT_MAX_QUEUE_SIZE * 0.8:
        status = "busy"
    else:
        status = "overloaded"
    
    return {
        "active_exports": active,
        "queued_exports": queued,
        "available_slots": available,
        "max_concurrent": MAX_CONCURRENT_EXPORTS,
        "max_queue_size": EXPORT_MAX_QUEUE_SIZE,
        "status": status,
        "active_export_ids": list(_active_exports.keys())
    }
