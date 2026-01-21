"""Post expenses populator for sub-scheme 20290037.

Follows 20290262 structure: 8 districts, 4 class types, filled/vacant counts.
"""
from typing import Optional, List, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from ...config import POST_EXPENSES_DISTRICT_COMPONENT

DISTRICT_CONFIG = [
    ("Mumbai City", {"1": 6, "2": 7, "3": 8, "4": 9}, 15),
    ("Mumbai Suburban", {"1": 22, "2": 23, "3": 24, "4": 25}, 31),
    ("Thane", {"1": 38, "2": 39, "3": 40, "4": 41}, 47),
    ("Palghar", {"1": 53, "2": 54, "3": 55, "4": 56}, 62),
    ("Raigad", {"1": 68, "2": 69, "3": 70, "4": 71}, 77),
    ("Ratnagiri", {"1": 84, "2": 85, "3": 86, "4": 87}, 93),
    ("Sindhudurg", {"1": 100, "2": 101, "3": 102, "4": 103}, 109),
    ("DCO Staff", {"1": 116, "2": 117, "3": 118, "4": 119}, 125),
]


def _write(ws, cell_addr: Optional[str], value):
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_post_expenses(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None,
):
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("post_expenses")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]
    _, _, PostExpenses, _ = get_scheme_models(sub_scheme_code)

    for district, row_map, fixed_row in DISTRICT_CONFIG:
        _write_district(ws, db, PostExpenses, district, row_map, fixed_row, fiscal_year)


def _write_district(
    ws,
    db: Session,
    model,
    district: str,
    row_map: Dict[str, int],
    fixed_row: int,
    fiscal_year: Optional[str],
):
    perm_counts, temp_counts = _get_category_counts(db, model, district, fiscal_year)
    for cls, row in row_map.items():
        _write(ws, f"C{row}", perm_counts.get(cls, {}).get("filled"))
        _write(ws, f"D{row}", perm_counts.get(cls, {}).get("vacant"))
        _write(ws, f"E{row}", temp_counts.get(cls, {}).get("filled"))
        _write(ws, f"F{row}", temp_counts.get(cls, {}).get("vacant"))
    _write_fixed_row(ws, db, model, district, fixed_row, fiscal_year)


def _get_category_counts(
    db: Session,
    model,
    district: str,
    fiscal_year: Optional[str],
) -> tuple:
    def aggregate(category: str) -> Dict[str, Dict[str, int]]:
        query = db.query(model).filter(
            model.district == district,
            model.category == category,
        )
        if fiscal_year:
            query = query.filter(model.fiscal_year == fiscal_year)
        result: Dict[str, Dict[str, int]] = {}
        for rec in query.all():
            cls = str(rec.class_type)
            if cls not in result:
                result[cls] = {"filled": 0, "vacant": 0}
            result[cls]["filled"] += int(rec.filled_posts or 0)
            result[cls]["vacant"] += int(rec.vacant_posts or 0)
        return result

    return aggregate("Permanent"), aggregate("Temporary")


def _write_fixed_row(
    ws,
    db: Session,
    model,
    district: str,
    fixed_row: int,
    fiscal_year: Optional[str],
):
    query = db.query(model).filter(model.district == district)
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)
    rep = query.first()
    if not rep:
        return
    component = POST_EXPENSES_DISTRICT_COMPONENT.get(district)
    component_value = None
    if component == "NPS":
        component_value = rep.nps
    elif component == "SeventhPayCommissionDifferenceNPS":
        component_value = rep.seventh_pay_commission_difference_nps
    elif component == "SeventhPayCommissionDifference":
        component_value = rep.seventh_pay_commission_difference
    values: List = [
        rep.medical_expenses,
        rep.festival_advance,
        rep.swagram_maharashtra_darshan,
        component_value,
        rep.other,
    ]
    for col, val in zip(["C", "D", "E", "F", "G", "H"], values):
        _write(ws, f"{col}{fixed_row}", val)
