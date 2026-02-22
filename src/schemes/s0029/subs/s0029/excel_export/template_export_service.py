"""Template-based Excel export service for sub-scheme 0029.

Simplified architecture - only populates Sheet 1 (अर्थसंकल्पीय जिल्हा).
Sheet 2 uses Excel formulas to auto-calculate from Sheet 1 data.
"""
import io
import os
import logging
from typing import Optional

from fastapi import HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from src.schemes.common.excel_export import ExcelExportService
from .arthsankalpiy_jilah import populate_section1

logger = logging.getLogger(__name__)

# Template configuration
TEMPLATE_DIR = "excel_templates/s0029/subs/s0029"
TEMPLATE_FILENAME = "Budget 0029 for 2021-2022.xlsx"
SHEET1_NAME = "अर्थसंकल्पीय जिल्हा"


def _get_template_path() -> str:
    """Find the Excel template file for s0029."""
    # Primary: exact template filename
    primary_path = os.path.join(TEMPLATE_DIR, TEMPLATE_FILENAME)
    if os.path.exists(primary_path):
        return primary_path
    
    # Fallback: search for any matching pattern
    if os.path.exists(TEMPLATE_DIR):
        for filename in os.listdir(TEMPLATE_DIR):
            if filename.endswith(('.xlsx', '.xls')):
                return os.path.join(TEMPLATE_DIR, filename)
    
    return None


def _generate_workbook(
    db: Session,
    fiscal_year: Optional[str],
) -> io.BytesIO:
    """Load template and populate with data."""
    template_path = _get_template_path()
    if not template_path:
        raise HTTPException(
            status_code=404,
            detail=f"Excel template not found. Please place template at: {TEMPLATE_DIR}/{TEMPLATE_FILENAME}",
        )

    try:
        wb = load_workbook(template_path, data_only=False)
    except Exception as e:
        logger.error(f"Failed to load Excel template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Excel export failed. Please try again.",
        )

    # Populate Sheet 1 with district revenue data
    populate_section1(wb, db, SHEET1_NAME, fiscal_year)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


async def export_original_workbook_async(
    db: Session,
    fiscal_year: Optional[str] = None,
) -> StreamingResponse:
    """Async version with throttling support.
    
    This is the production-grade method that should be used by API endpoints.
    """
    def generate():
        try:
            return _generate_workbook(db, fiscal_year)
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            logger.error(f"Failed to generate Excel: {exc}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Excel export failed. Please try again."
            )

    return await ExcelExportService.export_with_throttle(
        export_fn=generate,
        filename="0029_district_revenue",
        fiscal_year=fiscal_year,
    )


def export_original_workbook(
    db: Session,
    fiscal_year: Optional[str] = None,
) -> StreamingResponse:
    """Export the populated Excel workbook as a downloadable response (Synchronous)."""
    try:
        output = _generate_workbook(db, fiscal_year)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        logger.error(f"Failed to generate Excel: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Excel export failed. Please try again."
        )

    return ExcelExportService.create_response(
        content=output,
        base_filename="0029_district_revenue",
        fiscal_year=fiscal_year,
    )
