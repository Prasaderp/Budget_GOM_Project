"""Budget post details populator for sub-scheme 20530242.

20530242 has only 1 designation (Divisional Officer) in Class-3.
Row mappings are simplified compared to 20530162.
"""
from typing import Optional, List, Dict
from collections import defaultdict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from src.utils_da_rate import get_da_rate
from ...config import HRA_RATE_MAP


def _write(ws, cell_addr: Optional[str], value):
    """Write value to cell if address is valid."""
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_budget_post_details(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None
):
    """Populate budget post details sheet with data."""
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("budget_post_details")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]

    da_rate = get_da_rate(db, fiscal_year)
    BudgetPostDetails, _, _, _ = get_scheme_models(sub_scheme_code)

    # 20530242 has single designation
    designations = ['Divisional Officer']

    # District block mappings: (district, perm_start_row, temp_start_row)
    blocks = [
        ("Mumbai City", 7, 16),
        ("Mumbai Suburban", 25, 34),
        ("Thane", 43, 52),
        ("Palghar", 61, 70),
        ("Raigad", 79, 88),
        ("Ratnagiri", 97, 106),
        ("Sindhudurg", 115, 124),
        ("DCO Staff", 133, 142),
    ]

    for district, perm_start, temp_start in blocks:
        _write_block(ws, db, BudgetPostDetails, district, "Permanent",
                     designations, perm_start, da_rate, fiscal_year)
        _write_block(ws, db, BudgetPostDetails, district, "Temporary",
                     designations, temp_start, da_rate, fiscal_year)


def _write_block(
    ws,
    db: Session,
    model,
    district: str,
    category: str,
    designations: List[str],
    start_row: int,
    da_rate: float,
    fiscal_year: Optional[str]
):
    """Write a single district/category block to worksheet."""
    row_map = {d: r for d, r in zip(designations, range(start_row, start_row + len(designations)))}

    query = db.query(model).filter(model.district == district, model.category == category)
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)

    agg = _aggregate_records(query.all(), row_map, da_rate)
    _write_aggregated_data(ws, row_map, agg)


def _aggregate_records(
    records: List,
    row_map: Dict[str, int],
    da_rate: float
) -> Dict[str, Dict[str, int]]:
    """Aggregate records by designation with calculated fields."""
    agg = defaultdict(lambda: {
        "sanctioned_posts_prev1": 0, "sanctioned_posts_curr": 0,
        "special_pay": 0, "basic_pay": 0, "grade_pay": 0,
        "dearness_allowance": 0, "local_supplementary_allowance": 0,
        "house_rent_allowance": 0, "vehicle_allowance": 0,
        "washing_allowance": 0, "cash_allowance": 0, "footwear_allowance_other": 0,
    })

    for rec in records:
        desig = rec.designation
        if desig not in row_map:
            continue

        basic_pay = int(float(rec.basic_pay or 0))
        grade_pay = int(rec.grade_pay or 0)
        base_salary = basic_pay + grade_pay
        hra_rate_val = HRA_RATE_MAP.get(rec.hra_rate, 0.3)

        agg[desig]["sanctioned_posts_prev1"] += int(rec.sanctioned_posts_prev1 or 0)
        agg[desig]["sanctioned_posts_curr"] += int(rec.sanctioned_posts_curr or 0)
        agg[desig]["special_pay"] += int(rec.special_pay or 0)
        agg[desig]["basic_pay"] += basic_pay
        agg[desig]["grade_pay"] += grade_pay
        agg[desig]["dearness_allowance"] += int(base_salary * da_rate)
        agg[desig]["local_supplementary_allowance"] += int(rec.local_supplementary_allowance or 0)
        agg[desig]["house_rent_allowance"] += int(base_salary * hra_rate_val)
        agg[desig]["vehicle_allowance"] += int(rec.vehicle_allowance or 0)
        agg[desig]["washing_allowance"] += int(rec.washing_allowance or 0)
        agg[desig]["cash_allowance"] += int(rec.cash_allowance or 0)
        agg[desig]["footwear_allowance_other"] += int(rec.footwear_allowance_other or 0)

    return agg


def _write_aggregated_data(ws, row_map: Dict[str, int], agg: Dict):
    """Write aggregated data to worksheet cells."""
    col_map = [
        ("D", "sanctioned_posts_prev1"), ("E", "sanctioned_posts_curr"),
        ("F", "special_pay"), ("G", "basic_pay"), ("H", "grade_pay"),
        ("J", "dearness_allowance"), ("K", "local_supplementary_allowance"),
        ("L", "house_rent_allowance"), ("M", "vehicle_allowance"),
        ("N", "washing_allowance"), ("O", "cash_allowance"), ("P", "footwear_allowance_other"),
    ]

    for desig, row in row_map.items():
        vals = agg.get(desig)
        if not vals:
            continue
        for col, field in col_map:
            _write(ws, f"{col}{row}", vals[field])
