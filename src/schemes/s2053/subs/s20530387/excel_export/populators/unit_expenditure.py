"""Unit expenditure populator for sub-scheme 20530387.

SPECIAL: This scheme has NO districts - only DCO Main Office and DCO Staff.
Populates 15 primary units with 9 fiscal year fields per unit.
"""
from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from ...config import PRIMARY_UNITS


# Fiscal year field columns
FIELD_COLUMNS = ["C", "D", "E", "F", "G", "H", "I", "J", "K"]
FIELD_NAMES = [
    "expenditure_2021_22", "expenditure_2022_23", "expenditure_2023_24",
    "budget_2024_25", "forecast_2024_25",
    "budget_2025_26_estimating_officer", "budget_2025_26_controlling_officer",
    "budget_2025_26_admin_dept", "budget_2025_26_finance_dept",
]

# DCO unit start rows
# NOTE: Adjust these values after verifying with actual template
DCO_UNIT_START_ROWS = [
    ("DCO Staff", 7)
]


def _write(ws, cell_addr: Optional[str], value):
    """Write value to cell if address is valid."""
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_unit_expenditure(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None
):
    """Populate unit expenditure sheet with data."""
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("unit_expenditure")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]

    _, _, _, UnitExpenditure = get_scheme_models(sub_scheme_code)

    for dco_unit, start_row in DCO_UNIT_START_ROWS:
        _write_dco_data(ws, db, UnitExpenditure, dco_unit, start_row, fiscal_year)


def _write_dco_data(
    ws,
    db: Session,
    model,
    dco_unit: str,
    start_row: int,
    fiscal_year: Optional[str]
):
    """Write unit expenditure data for a single DCO unit."""
    row_map = {unit: row for unit, row in zip(PRIMARY_UNITS, range(start_row, start_row + len(PRIMARY_UNITS)))}

    query = db.query(model).filter(model.district == dco_unit)
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)

    items: List = query.all()
    for item in items:
        row = row_map.get(item.unit_account)
        if not row:
            continue
        for col, field in zip(FIELD_COLUMNS, FIELD_NAMES):
            _write(ws, f"{col}{row}", getattr(item, field, None))
