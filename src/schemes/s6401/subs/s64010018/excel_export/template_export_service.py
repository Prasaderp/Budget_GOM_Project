"""Template-based Excel export service for sub-scheme 64010018.

Architecture mirrors 2029/2053 schemes with async throttling and robust error handling.
"""
import io
import os
from typing import Optional

from fastapi import HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from src.schemes.common.excel_export import ExcelExportService
from .district_expenditure import populate_sheet

TEMPLATE_DIR = "excel_templates/s6401/subs/s64010018"
SHEET_NAME = "6401"  # Default sheet name, logic handles fallback to active sheet


def _get_template_path() -> str:
    """Find the Excel template file."""
    if not os.path.exists(TEMPLATE_DIR):
        return None
        
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
            detail=f"Excel template not found in {TEMPLATE_DIR}",
        )

    try:
        wb = load_workbook(template_path, data_only=False)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load Excel template: {e}",
        )

    populate_sheet(wb, db, SHEET_NAME, fiscal_year)

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
            # If it's already an HTTPException, re-raise it
            if isinstance(exc, HTTPException):
                raise exc
            # Otherwise wrap it
            raise HTTPException(
                status_code=500, detail=f"Failed to generate Excel: {exc}"
            )

    return await ExcelExportService.export_with_throttle(
        export_fn=generate,
        filename="64010018_district_expenditure",
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
        raise HTTPException(
            status_code=500, detail=f"Failed to generate Excel: {exc}"
        )

    return ExcelExportService.create_response(
        content=output,
        base_filename="64010018_district_expenditure",
        fiscal_year=fiscal_year,
    )
