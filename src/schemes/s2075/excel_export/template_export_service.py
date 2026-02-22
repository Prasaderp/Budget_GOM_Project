"""Template-based Excel export for scheme 2075 - Miscellaneous General Services.

Production-grade architecture that:
- Loads a single shared Excel template containing both sub-schema sheets
- Populates data from both sub-schemas (20750249, 20750294)
- Ensures fiscal year consistency across all data sources
- Uses centralized ExcelExportService for throttling and error handling
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
from .populators import populate_s2075_data
from ..config import SCHEME_CONFIG

logger = logging.getLogger(__name__)

TEMPLATE_DIR = "excel_templates/s2075/subs/s2075"
BASE_FILENAME = f"{SCHEME_CONFIG.code} - Annual Budget - 2026-27"


def _get_template_path() -> Optional[str]:
    """Locate the shared Excel template."""
    if not os.path.exists(TEMPLATE_DIR):
        return None
    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith(('.xlsx', '.xls')):
            return os.path.join(TEMPLATE_DIR, filename)
    return None


def _generate_2075_workbook(db: Session, fiscal_year: Optional[str]) -> io.BytesIO:
    """Load template and populate with data from both sub-schemas."""
    template_path = _get_template_path()
    if not template_path:
        raise HTTPException(
            status_code=404,
            detail="Excel template not found",
        )

    try:
        wb = load_workbook(template_path, data_only=False)
    except Exception as e:
        logger.error(f"Failed to load Excel template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Excel template could not be loaded",
        )

    populate_s2075_data(wb, db, fiscal_year)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


async def export_2075_workbook_async(
    db: Session,
    fiscal_year: Optional[str] = None,
) -> StreamingResponse:
    """Async export with throttling support for 2075 workbook."""
    def generate():
        try:
            return _generate_2075_workbook(db, fiscal_year)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Failed to generate {SCHEME_CONFIG.code} Excel: {exc}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Excel workbook generation failed"
            )

    return await ExcelExportService.export_with_throttle(
        export_fn=generate,
        filename=BASE_FILENAME,
        fiscal_year=fiscal_year,
    )
