import io
import os
import logging
from typing import Optional
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import load_workbook
from src.schemes.common.excel_export import ExcelExportService
from .district_expenditure import populate_sheet

logger = logging.getLogger(__name__)

TEMPLATE_DIR = "excel_templates/s6401/subs/s64010018"
SHEET_NAME = "6401"

def _get_template_path() -> str:
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
    template_path = _get_template_path()
    if not template_path:
        logger.error(f"Template not found in {TEMPLATE_DIR}")
        raise HTTPException(
            status_code=500,
            detail="Excel export failed. Please try again.",
        )

    try:
        wb = load_workbook(template_path, data_only=False)
    except Exception as e:
        logger.error(f"Template load failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Excel export failed. Please try again.",
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
    def generate():
        try:
            return _generate_workbook(db, fiscal_year)
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            logger.error(f"Export generation failed: {exc}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Excel export failed. Please try again."
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
    try:
        output = _generate_workbook(db, fiscal_year)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        logger.error(f"Export generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Excel export failed. Please try again."
        )

    return ExcelExportService.create_response(
        content=output,
        base_filename="64010018_district_expenditure",
        fiscal_year=fiscal_year,
    )
