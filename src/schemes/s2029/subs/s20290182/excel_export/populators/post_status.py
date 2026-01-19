"""Post status populator for sub-scheme 20290182.

Structure follows 20290046: 8 districts, 3 class types, Permanent/Temporary.
"""
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models

FILLED_COLS = {"Class-1 & 2": "C", "Class-3": "D", "Class-4": "E"}
VACANT_COLS = {"Class-1 & 2": "G", "Class-3": "H", "Class-4": "I"}

DISTRICT_ROWS = [
    ("Mumbai City", 7, 22),
    ("Mumbai Suburban", 39, 54),
    ("Thane", 71, 86),
    ("Palghar", 103, 118),
    ("Raigad", 135, 150),
    ("Ratnagiri", 167, 182),
    ("Sindhudurg", 199, 214),
    ("DCO Staff", 231, 246),
]

FIELD_OFFSETS = [
    (0, "posts"),
    (1, "salary"),
    (2, "grade_pay"),
    (4, "special_pay"),
    (5, "dearness_allowance"),
    (6, "local_supplementary_allowance"),
    (7, "house_rent_allowance"),
    (8, "travel_allowance"),
    (9, "other"),
]


def _write(ws, cell_addr: Optional[str], value):
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_post_status(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None,
):
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("post_status")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]
    _, PostStatus, _, _ = get_scheme_models(sub_scheme_code)

    for district, perm_start, temp_start in DISTRICT_ROWS:
        _write_block(ws, db, PostStatus, district, "Permanent", perm_start, fiscal_year)
        _write_block(ws, db, PostStatus, district, "Temporary", temp_start, fiscal_year)


def _write_block(
    ws,
    db: Session,
    model,
    district: str,
    category: str,
    start_row: int,
    fiscal_year: Optional[str],
):
    query = db.query(model).filter(
        model.district == district,
        model.category == category,
    )
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)
    records: List = query.all()
    for rec in records:
        col = (
            FILLED_COLS.get(rec.class_type)
            if rec.status == "Filled"
            else VACANT_COLS.get(rec.class_type)
            if rec.status == "Vacant"
            else None
        )
        if not col:
            continue
        for offset, field in FIELD_OFFSETS:
            _write(ws, f"{col}{start_row + offset}", getattr(rec, field, None))

