"""Template-based Excel export for combined 2245-2215 schemes.

Production-grade architecture that:
- Loads a single shared Excel template containing both scheme sheets
- Populates data from s2245 (natural calamity) tables
- Populates data from s2215 (water scarcity) tables
- Ensures fiscal year consistency across both data sources
"""
import io
import os
from typing import Optional

from fastapi import HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from src.schemes.common.excel_export import ExcelExportService
from .populators import populate_s2245_data, populate_s2215_data

TEMPLATE_DIR = "excel_templates/s2245_2215/subs/s2245_2215"
BASE_FILENAME = "2245_2215_combined_budget"


def _get_template_path() -> Optional[str]:
    """Locate the shared Excel template."""
    if not os.path.exists(TEMPLATE_DIR):
        return None
    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith(('.xlsx', '.xls')):
            return os.path.join(TEMPLATE_DIR, filename)
    return None


def _generate_combined_workbook(db: Session, fiscal_year: Optional[str]) -> io.BytesIO:
    """Load template and populate with data from both schemes."""
    template_path = _get_template_path()
    if not template_path:
        raise HTTPException(
            status_code=404,
            detail=f"Combined Excel template not found in {TEMPLATE_DIR}",
        )

    try:
        wb = load_workbook(template_path, data_only=False)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load Excel template: {e}",
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
    """Async export with throttling support for combined workbook."""
    def generate():
        try:
            return _generate_combined_workbook(db, fiscal_year)
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate combined Excel: {exc}"
            )

    return await ExcelExportService.export_with_throttle(
        export_fn=generate,
        filename=BASE_FILENAME,
        fiscal_year=fiscal_year,
    )
