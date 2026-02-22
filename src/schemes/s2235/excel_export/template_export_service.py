"""Template-based Excel export for scheme 2235 - Social Security and Welfare.

Production-grade architecture that:
- Loads a single shared Excel template containing all 4 sub-schema sheets
- Populates data from all 4 sub-schemas (22353195, 22350338, 22350311, 22353408)
- Ensures fiscal year consistency across all data sources
- Syncs data when downloaded from any sub-schema UI
"""
import io
import os
import logging
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from src.schemes.common.excel_export import ExcelExportService
from .populators import populate_s2235_data

TEMPLATE_DIR = "excel_templates/s2235/subs/s2235"
BASE_FILENAME = "2235-Annual-Budget-2026-27"


def _get_template_path() -> Optional[str]:
    """Locate the shared Excel template."""
    if not os.path.exists(TEMPLATE_DIR):
        return None
    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith('.xlsx'):
            return os.path.join(TEMPLATE_DIR, filename)
    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith('.xls'):
            return os.path.join(TEMPLATE_DIR, filename)
    return None


def _generate_2235_workbook(db: Session, fiscal_year: Optional[str]) -> io.BytesIO:
    """Load template and populate with data from all 4 sub-schemas."""
    template_path = _get_template_path()
    if not template_path:
        logger.error(f"2235 Excel template not found in {TEMPLATE_DIR}")
        raise HTTPException(
            status_code=404,
            detail="2235 Excel template not found",
        )

    if template_path.endswith('.xls'):
        raise HTTPException(
            status_code=500,
            detail="Legacy .xls format not supported. Please convert template to .xlsx format.",
        )

    try:
        wb = load_workbook(template_path, data_only=False)
    except Exception as e:
        logger.error(f"Failed to load Excel template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to load Excel template. Please try again.",
        )

    populate_s2235_data(wb, db, fiscal_year)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


async def export_2235_workbook_async(
    db: Session,
    fiscal_year: Optional[str] = None,
) -> StreamingResponse:
    """Async export with throttling support for 2235 workbook."""
    def generate():
        try:
            return _generate_2235_workbook(db, fiscal_year)
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            logger.error(f"Failed to generate 2235 Excel: {exc}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate 2235 Excel. Please try again."
            )

    return await ExcelExportService.export_with_throttle(
        export_fn=generate,
        filename=BASE_FILENAME,
        fiscal_year=fiscal_year,
    )
