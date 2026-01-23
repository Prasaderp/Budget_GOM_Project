"""Template-based Excel export for scheme 7610 - Government Employee Loans.

Production-grade architecture that:
- Loads a single shared Excel template containing all 4 sub-schema tables
- Populates data from all 4 sub-schemas (76100149, 76100158, 76100167, 76101871)
- Ensures fiscal year consistency across all data sources
- Syncs data when downloaded from any sub-schema UI
"""
import io
import os
from typing import Optional

from fastapi import HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from src.schemes.common.excel_export import ExcelExportService
from .populators import populate_s7610_data

TEMPLATE_DIR = "excel_templates/s7610/subs/s7610"
BASE_FILENAME = "7610 - Annual Budget -2026-27"


def _get_template_path() -> Optional[str]:
    """Locate the shared Excel template."""
    if not os.path.exists(TEMPLATE_DIR):
        return None
    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith(('.xlsx', '.xls')):
            return os.path.join(TEMPLATE_DIR, filename)
    return None


def _generate_7610_workbook(db: Session, fiscal_year: Optional[str]) -> io.BytesIO:
    """Load template and populate with data from all 4 sub-schemas."""
    template_path = _get_template_path()
    if not template_path:
        raise HTTPException(
            status_code=404,
            detail=f"7610 Excel template not found in {TEMPLATE_DIR}",
        )

    try:
        wb = load_workbook(template_path, data_only=False)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load Excel template: {e}",
        )

    populate_s7610_data(wb, db, fiscal_year)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


async def export_7610_workbook_async(
    db: Session,
    fiscal_year: Optional[str] = None,
) -> StreamingResponse:
    """Async export with throttling support for 7610 workbook."""
    def generate():
        try:
            return _generate_7610_workbook(db, fiscal_year)
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate 7610 Excel: {exc}"
            )

    return await ExcelExportService.export_with_throttle(
        export_fn=generate,
        filename=BASE_FILENAME,
        fiscal_year=fiscal_year,
    )
