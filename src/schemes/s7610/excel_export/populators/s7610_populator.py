"""Unified populator for scheme 7610 Excel export.

Handles all 4 sub-schemas in a single sheet:
- 76100149: घरबांधणी अग्रिमे (House Building Advance)
- 76100158: मोटार वाहनांच्या खरेदीसाठी अग्रिमे (Motor Vehicle Purchase Advance)  
- 76100167: इतर वाहनांच्या खरेदीसाठी अग्रिमे (Other Vehicle Purchase Advance)
- 76101871: वैयक्तीक संगणक यंत्रे खरेदीसाठी अग्रिमे (Personal Computer Purchase Advance)

Each sub-schema has 8 districts plus an एकूण (total) row.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.schemes.s7610.subs.s76100149.models import DistrictExpenditure76100149
from src.schemes.s7610.subs.s76100158.models import DistrictExpenditure76100158
from src.schemes.s7610.subs.s76100167.models import DistrictExpenditure76100167
from src.schemes.s7610.subs.s76101871.models import DistrictExpenditure76101871

SHEET_NAME = "Annual Budget 2021-22"

COL_MAP = {
    "expenditure_prev3": "C",
    "expenditure_prev2": "D",
    "expenditure_prev1": "E",
    "budget_estimate": "F",
    "revised_estimate": "G",
    "budget_estimate_next": "H",
}

DISTRICTS_ORDER = [
    "Mumbai City",
    "Mumbai Suburban",
    "Thane",
    "Palghar",
    "Raigad",
    "Ratnagiri",
    "Sindhudurg",
    "DCO Staff",
]

SUB_SCHEMA_ROW_MAP = {
    "76100149": {
        "Mumbai City": 9,
        "Mumbai Suburban": 10,
        "Thane": 11,
        "Palghar": 12,
        "Raigad": 13,
        "Ratnagiri": 14,
        "Sindhudurg": 15,
        "DCO Staff": 16,
    },
    "76100158": {
        "Mumbai City": 19,
        "Mumbai Suburban": 20,
        "Thane": 21,
        "Palghar": 22,
        "Raigad": 23,
        "Ratnagiri": 24,
        "Sindhudurg": 25,
        "DCO Staff": 26,
    },
    "76100167": {
        "Mumbai City": 29,
        "Mumbai Suburban": 30,
        "Thane": 31,
        "Palghar": 32,
        "Raigad": 33,
        "Ratnagiri": 34,
        "Sindhudurg": 35,
        "DCO Staff": 36,
    },
    "76101871": {
        "Mumbai City": 39,
        "Mumbai Suburban": 40,
        "Thane": 41,
        "Palghar": 42,
        "Raigad": 43,
        "Ratnagiri": 44,
        "Sindhudurg": 45,
        "DCO Staff": 46,
    },
}

MODEL_MAP = {
    "76100149": DistrictExpenditure76100149,
    "76100158": DistrictExpenditure76100158,
    "76100167": DistrictExpenditure76100167,
    "76101871": DistrictExpenditure76101871,
}


def _fetch_data_for_sub_schema(
    db: Session,
    model_class: Any,
    sub_scheme_code: str,
    fiscal_year: Optional[str],
) -> Dict[str, Any]:
    """Fetch all district records for a sub-schema and return as district->record map."""
    query = db.query(model_class).filter(
        model_class.sub_scheme_code == sub_scheme_code,
    )
    if fiscal_year:
        query = query.filter(model_class.fiscal_year == fiscal_year)
    
    records = query.all()
    return {r.district: r for r in records}



def _populate_sub_schema(
    ws: Any,
    db: Session,
    sub_scheme_code: str,
    fiscal_year: Optional[str],
) -> None:
    """Populate a single sub-schema section in the worksheet."""
    model_class = MODEL_MAP.get(sub_scheme_code)
    row_map = SUB_SCHEMA_ROW_MAP.get(sub_scheme_code)
    if not model_class or not row_map:
        return
    
    data_map = _fetch_data_for_sub_schema(db, model_class, sub_scheme_code, fiscal_year)
    
    for district in DISTRICTS_ORDER:
        row_num = row_map.get(district)
        if not row_num:
            continue
        record = data_map.get(district)
        if not record:
            continue
        for field, col in COL_MAP.items():
            value = getattr(record, field, 0) or 0
            ws[f"{col}{row_num}"] = value


def populate_s7610_data(
    wb: Workbook,
    db: Session,
    fiscal_year: Optional[str],
) -> None:
    """Populate all 4 sub-schemas in the workbook."""
    sheet_names = wb.sheetnames
    ws = None
    
    if SHEET_NAME in sheet_names:
        ws = wb[SHEET_NAME]
    elif sheet_names:
        ws = wb[sheet_names[0]]
    else:
        return
    
    for sub_scheme_code in SUB_SCHEMA_ROW_MAP:
        _populate_sub_schema(ws, db, sub_scheme_code, fiscal_year)
