"""Post expenses populator for sub-scheme 20530387.

SPECIAL: This scheme has NO districts - only DCO Main Office and DCO Staff.
Both units use NPS component.
"""
from typing import Optional, List, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from ...config import POST_EXPENSES_DISTRICT_COMPONENT


# DCO unit mappings: (unit, class_row_map, fixed_row)
# 4 classes: 1, 2, 3, 4
# NOTE: Adjust these values after verifying with actual template
DCO_UNIT_CONFIG = [
    ("DCO Staff", {"1": 6, "2": 7, "3": 8, "4": 9}, 15)
]


def _write(ws, cell_addr: Optional[str], value):
    """Write value to cell if address is valid."""
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_post_expenses(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None
):
    """Populate post expenses sheet with data."""
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("post_expenses")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]

    _, _, PostExpenses, _ = get_scheme_models(sub_scheme_code)

    for dco_unit, row_map, fixed_row in DCO_UNIT_CONFIG:
        _write_dco_data(ws, db, PostExpenses, dco_unit, row_map, fixed_row, fiscal_year)


def _write_dco_data(
    ws,
    db: Session,
    model,
    dco_unit: str,
    row_map: Dict[str, int],
    fixed_row: int,
    fiscal_year: Optional[str]
):
    """Write post expenses data for a single DCO unit."""
    perm_counts, temp_counts = _get_category_counts(db, model, dco_unit, fiscal_year)

    # Write permanent counts to columns C, D
    for cls, row in row_map.items():
        _write(ws, f"C{row}", perm_counts.get(cls, {}).get("filled"))
        _write(ws, f"D{row}", perm_counts.get(cls, {}).get("vacant"))

    # Write temporary counts to columns E, F
    for cls, row in row_map.items():
        _write(ws, f"E{row}", temp_counts.get(cls, {}).get("filled"))
        _write(ws, f"F{row}", temp_counts.get(cls, {}).get("vacant"))

    # Write fixed row values
    _write_fixed_row(ws, db, model, dco_unit, fixed_row, fiscal_year)


def _get_category_counts(
    db: Session,
    model,
    dco_unit: str,
    fiscal_year: Optional[str]
) -> tuple:
    """Get aggregated counts for permanent and temporary categories."""
    def aggregate(category: str) -> Dict[str, Dict[str, int]]:
        query = db.query(model).filter(model.district == dco_unit, model.category == category)
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
    dco_unit: str,
    fixed_row: int,
    fiscal_year: Optional[str]
):
    """Write fixed expense values for DCO unit."""
    query = db.query(model).filter(model.district == dco_unit)
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)

    rep = query.first()
    if not rep:
        return

    # Both DCO units use NPS component
    component = POST_EXPENSES_DISTRICT_COMPONENT.get(dco_unit)
    component_value = None
    if component == 'NPS':
        component_value = rep.nps
    elif component == 'SeventhPayCommissionDifferenceNPS':
        component_value = rep.seventh_pay_commission_difference_nps
    elif component == 'SeventhPayCommissionDifference':
        component_value = rep.seventh_pay_commission_difference

    values = [
        rep.medical_expenses, rep.festival_advance,
        rep.swagram_maharashtra_darshan, component_value, rep.other
    ]
    for col, val in zip(["C", "D", "E", "F", "G"], values):
        _write(ws, f"{col}{fixed_row}", val)
