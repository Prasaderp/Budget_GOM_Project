from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from ...config import PRIMARY_UNITS


def _write(ws, cell_addr: Optional[str], value):
    if not cell_addr:
        return
    ws[cell_addr].value = value if value is not None else None


def populate_unit_expenditure(wb: Workbook, db: Session, sub_scheme_code: Optional[str] = None, fiscal_year: Optional[str] = None):
    from ...config import SHEET_NAMES
    
    sheet_name = SHEET_NAMES.get("unit_expenditure")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found in original workbook")
    ws = wb[sheet_name]
    
    def addr(col: str, row: int) -> str:
        return f"{col}{row}"

    col_order = ["C", "D", "E", "F", "G", "H", "I", "J", "K"]
    fields = [
        "expenditure_2021_22",
        "expenditure_2022_23",
        "expenditure_2023_24",
        "budget_2024_25",
        "forecast_2024_25",
        "budget_2025_26_estimating_officer",
        "budget_2025_26_controlling_officer",
        "budget_2025_26_admin_dept",
        "budget_2025_26_finance_dept",
    ]

    _, _, _, UnitExpenditure = get_scheme_models(sub_scheme_code)
    
    def write_district(district: str, start_row: int):
        row_map = {unit: row for unit, row in zip(PRIMARY_UNITS, range(start_row, start_row + len(PRIMARY_UNITS)))}
        query = db.query(UnitExpenditure).filter(UnitExpenditure.district == district)
        if fiscal_year:
            query = query.filter(UnitExpenditure.fiscal_year == fiscal_year)
        items: List = query.all()
        for it in items:
            row = row_map.get(it.unit_account)
            if not row:
                continue
            for col, field in zip(col_order, fields):
                _write(ws, addr(col, row), getattr(it, field, None))

    write_district("Mumbai City", 7)
    write_district("Mumbai Suburban", 30)
    write_district("Thane", 53)
    write_district("Palghar", 76)
    write_district("Raigad", 99)
    write_district("Ratnagiri", 122)
    write_district("Sindhudurg", 145)
    write_district("DCO Staff", 168)