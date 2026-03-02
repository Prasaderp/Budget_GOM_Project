"""Unified populator for scheme 2235 Excel export.

All 4 sub-schemas share identical field structure:
- expenditure_prev3 -> Column C
- expenditure_prev2 -> Column D
- expenditure_prev1 -> Column E
- budget_grant_curr -> Column F
- revised_grant_curr -> Column G
- budget_estimate_next -> Column H

Sheet row mappings:
- 22353195: 5 districts (Thane, Palghar, Raigad, Ratnagiri, Sindhudurg) - rows 7-11
- 22350338: 8 entities (Divisional Commissioner + 7 districts) - rows 7-14
- 22350311: 7 districts - rows 7-13
- 22353408: 7 districts - rows 7-13
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.schemes.s2235.subs.s22353195.models import DistrictExpenditure22353195
from src.schemes.s2235.subs.s22350338.models import DistrictExpenditure22350338
from src.schemes.s2235.subs.s22350311.models import DistrictExpenditure22350311
from src.schemes.s2235.subs.s22353408.models import DistrictExpenditure22353408

SHEET_NAMES = ["22353195", "22350338", "22350311", "22353408"]

MODEL_MAP = {
    "22353195": DistrictExpenditure22353195,
    "22350338": DistrictExpenditure22350338,
    "22350311": DistrictExpenditure22350311,
    "22353408": DistrictExpenditure22353408,
}

ROW_MAP_22353195 = {
    "Thane": 7,
    "Palghar": 8,
    "Raigad": 9,
    "Ratnagiri": 10,
    "Sindhudurg": 11,
}

ROW_MAP_22350338 = {
    "Divisional Commissioner": 7,
    "Mumbai City": 8,
    "Mumbai Suburban": 9,
    "Thane": 10,
    "Palghar": 11,
    "Raigad": 12,
    "Ratnagiri": 13,
    "Sindhudurg": 14,
}

ROW_MAP_22350311 = {
    "Mumbai City": 7,
    "Mumbai Suburban": 8,
    "Thane": 9,
    "Palghar": 10,
    "Raigad": 11,
    "Ratnagiri": 12,
    "Sindhudurg": 13,
}

ROW_MAP_22353408 = {
    "Mumbai City": 7,
    "Mumbai Suburban": 8,
    "Thane": 9,
    "Palghar": 10,
    "Raigad": 11,
    "Ratnagiri": 12,
    "Sindhudurg": 13,
}

ROW_MAPS = {
    "22353195": ROW_MAP_22353195,
    "22350338": ROW_MAP_22350338,
    "22350311": ROW_MAP_22350311,
    "22353408": ROW_MAP_22353408,
}

UNIFORM_FIELD_TO_COL = {
    "expenditure_prev3": "C",
    "expenditure_prev2": "D",
    "expenditure_prev1": "E",
    "budget_grant_curr": "F",
    "revised_grant_curr": "G",
    "budget_estimate_next": "H",
}


def _fetch_data(
    db: Session,
    model_class: Any,
    sub_scheme_code: str,
    fiscal_year: Optional[str],
) -> Dict[str, Any]:
    """Fetch district records for a sub-schema, keyed by district name."""
    query = db.query(model_class).filter(
        model_class.sub_scheme_code == sub_scheme_code,
    )
    if fiscal_year:
        query = query.filter(model_class.fiscal_year == fiscal_year)
    return {r.district: r for r in query.all()}


def _populate_sheet(
    wb: Any,
    db: Session,
    sub_scheme_code: str,
    fiscal_year: Optional[str],
) -> None:
    """Populate a single sub-schema sheet."""
    model_class = MODEL_MAP.get(sub_scheme_code)
    row_map = ROW_MAPS.get(sub_scheme_code)
    
    if not all([model_class, row_map]):
        return
    
    ws = None
    for name in wb.sheetnames:
        if sub_scheme_code in name:
            ws = wb[name]
            break
    if ws is None:
        return
    
    data = _fetch_data(db, model_class, sub_scheme_code, fiscal_year)
    
    for district, row in row_map.items():
        record = data.get(district)
        if not record:
            continue
        for field, col in UNIFORM_FIELD_TO_COL.items():
            value = getattr(record, field, None)
            ws[f"{col}{row}"] = value if value is not None else 0


def populate_s2235_data(
    wb: Any,
    db: Session,
    fiscal_year: Optional[str],
    is_xls: bool = False,
) -> None:
    """Populate all 4 sub-schema sheets in the workbook."""
    for sub_scheme_code in SHEET_NAMES:
        _populate_sheet(wb, db, sub_scheme_code, fiscal_year)
