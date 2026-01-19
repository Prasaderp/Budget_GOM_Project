"""Post status populator for sub-scheme 20530313.

20530313 has 2 designations in Class-3 and Class-4.
"""
from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models


# Column mappings for class types
FILLED_COLS = {"Class-3": "C", "Class-4": "D"}
VACANT_COLS = {"Class-3": "F", "Class-4": "G"}

# District row mappings: (district, perm_start, temp_start)
# NOTE: Adjust these values after verifying with actual template
DISTRICT_ROWS = [
    ("Mumbai City", 7, 22),
    ("Mumbai Suburban", 40, 55),
    ("Thane", 73, 88),
    ("Palghar", 106, 121),
    ("Raigad", 139, 154),
    ("Ratnagiri", 172, 187),
    ("Sindhudurg", 205, 220),
    ("DCO Staff", 238, 253),
]


def _write(ws, cell_addr: Optional[str], value):
    """Write value to cell if address is valid."""
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_post_status(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None
):
    """Populate post status sheet with data."""
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("post_status")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]

    _, PostStatus, _, _ = get_scheme_models(sub_scheme_code)

    for district, perm_start, temp_start in DISTRICT_ROWS:
        _write_district_block(ws, db, PostStatus, district, "Permanent", perm_start, fiscal_year)
        _write_district_block(ws, db, PostStatus, district, "Temporary", temp_start, fiscal_year)


def _write_district_block(
    ws,
    db: Session,
    model,
    district: str,
    category: str,
    start_row: int,
    fiscal_year: Optional[str]
):
    """Write post status data for a district/category block."""
    query = db.query(model).filter(model.district == district, model.category == category)
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)

    records: List = query.all()
    for rec in records:
        col = FILLED_COLS.get(rec.class_type) if rec.status == "Filled" else \
              VACANT_COLS.get(rec.class_type) if rec.status == "Vacant" else None
        if not col:
            continue
        _write_record_to_cells(ws, col, start_row, rec)


def _write_record_to_cells(ws, col: str, start_row: int, rec):
    """Write a single record's fields to cells."""
    field_offsets = [
        (0, "posts"), (1, "salary"), (2, "grade_pay"),
        (4, "special_pay"), (5, "dearness_allowance"),
        (6, "local_supplementary_allowance"), (7, "house_rent_allowance"),
        (8, "travel_allowance"), (9, "other"),
    ]

    for offset, field in field_offsets:
        value = getattr(rec, field, None)
        _write(ws, f"{col}{start_row + offset}", value)
