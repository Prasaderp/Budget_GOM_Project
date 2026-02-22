import io
import os
import logging
from typing import Optional
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import load_workbook
from src.schemes.common.excel_export import ExcelExportService
from .populators import populate_s2245_data, populate_s2215_data

logger = logging.getLogger(__name__)

TEMPLATE_DIR = "excel_templates/s2245_2215/subs/s2245_2215"
BASE_FILENAME = "2245_2215_combined_budget"

def _get_template_path() -> Optional[str]:
    if not os.path.exists(TEMPLATE_DIR):
        return None
    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith(('.xlsx', '.xls')):
            return os.path.join(TEMPLATE_DIR, filename)
    return None

def _generate_combined_workbook(db: Session, fiscal_year: Optional[str]) -> io.BytesIO:
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
    populate_s2245_data(wb, db, fiscal_year)
    populate_s2215_data(wb, db, fiscal_year)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

async def export_combined_workbook_async(
    db: Session,
    fiscal_year: Optional[str] = None,
) -> StreamingResponse:
    def generate():
        try:
            return _generate_combined_workbook(db, fiscal_year)
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            logger.error(f"Export generation failed: {exc}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail="Excel export failed. Please try again."
            )
    return await ExcelExportService.export_with_throttle(
        export_fn=generate,
        filename=BASE_FILENAME,
        fiscal_year=fiscal_year,
    )
