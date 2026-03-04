"""Unit expenditure populator for sub-scheme 20290262.

Follows 20290182: 7 districts, 9 primary units per district.
"""
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from ...config import PRIMARY_UNITS

FIELD_COLUMNS = ["C", "D", "E", "F", "G", "H", "I", "J", "K"]
FIELD_NAMES = [
    "expenditure_prev4",
    "expenditure_prev3",
    "expenditure_prev2",
    "budget_prev1",
    "forecast_prev1",
    "budget_curr_estimating_officer",
    "budget_curr_controlling_officer",
    "budget_curr_admin_dept",
    "budget_curr_finance_dept",
]

DISTRICT_START_ROWS = [
    ("Mumbai City", 7),
    ("Mumbai Suburban", 24),
    ("Thane", 41),
    ("Palghar", 57),
    ("Raigad", 74),
    ("Ratnagiri", 91),
    ("Sindhudurg", 108),
    ("DCO Staff", 125),
]


def _write(ws, cell_addr: Optional[str], value):
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_unit_expenditure(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None,
):
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("unit_expenditure")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]
    _, _, _, UnitExpenditure = get_scheme_models(sub_scheme_code)

    for district, start_row in DISTRICT_START_ROWS:
        _write_district(ws, db, UnitExpenditure, district, start_row, fiscal_year)


def _write_district(
    ws,
    db: Session,
    model,
    district: str,
    start_row: int,
    fiscal_year: Optional[str],
):
    row_map = {
        unit: row
        for unit, row in zip(
            PRIMARY_UNITS, range(start_row, start_row + len(PRIMARY_UNITS))
        )
    }
    query = db.query(model).filter(model.district == district)
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)
    items: List = query.all()
    for item in items:
        row = row_map.get(item.unit_account)
        if not row:
            continue
        for col, field in zip(FIELD_COLUMNS, FIELD_NAMES):
            _write(ws, f"{col}{row}", getattr(item, field, None))
