"""Budget post details populator for sub-scheme 20290046.

Uses hardcoded row mappings due to merged cells in Excel template.
Districts: 7 + DCO Staff. Designations: 9 across 3 class types.
"""
from typing import Optional, Dict
from collections import defaultdict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from src.utils_da_rate import get_da_rate
from ...config import HRA_RATE_MAP

MUMBAI_CITY_PERM_MAP = {
    "Deputy Collector/Expert Officer": 7,
    "Head Clerk": 9,
    "Clerk": 10,
    "Vehicle Driver": 11,
    "Notice Bearer": 13,
    "Peon": 14,
}

MUMBAI_CITY_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 21,
    "City Architect": 22,
    "Assistant City Architect": 23,
    "Head Clerk": 25,
    "Divisional Officer": 26,
    "Clerk": 27,
    "Vehicle Driver": 28,
    "Peon": 30,
}

MUMBAI_SUBURBAN_PERM_MAP = {
    "Deputy Collector/Expert Officer": 40,
    "Head Clerk": 42,
    "Clerk": 43,
    "Vehicle Driver": 44,
    "Notice Bearer": 46,
    "Peon": 47,
}

MUMBAI_SUBURBAN_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 54,
    "City Architect": 55,
    "Assistant City Architect": 56,
    "Head Clerk": 58,
    "Divisional Officer": 59,
    "Clerk": 60,
    "Vehicle Driver": 61,
    "Peon": 63,
}

THANE_PERM_MAP = {
    "Deputy Collector/Expert Officer": 73,
    "Head Clerk": 75,
    "Clerk": 76,
    "Vehicle Driver": 77,
    "Notice Bearer": 79,
    "Peon": 80,
}

THANE_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 87,
    "City Architect": 88,
    "Assistant City Architect": 89,
    "Head Clerk": 91,
    "Divisional Officer": 92,
    "Clerk": 93,
    "Vehicle Driver": 94,
    "Peon": 96,
}

PALGHAR_PERM_MAP = {
    "Deputy Collector/Expert Officer": 106,
    "Head Clerk": 108,
    "Clerk": 109,
    "Vehicle Driver": 110,
    "Notice Bearer": 112,
    "Peon": 113,
}

PALGHAR_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 120,
    "City Architect": 121,
    "Assistant City Architect": 122,
    "Head Clerk": 124,
    "Divisional Officer": 125,
    "Clerk": 126,
    "Vehicle Driver": 127,
    "Peon": 129,
}

RAIGAD_PERM_MAP = {
    "Deputy Collector/Expert Officer": 139,
    "Head Clerk": 141,
    "Clerk": 142,
    "Vehicle Driver": 143,
    "Notice Bearer": 145,
    "Peon": 146,
}

RAIGAD_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 153,
    "City Architect": 154,
    "Assistant City Architect": 155,
    "Head Clerk": 157,
    "Divisional Officer": 158,
    "Clerk": 159,
    "Vehicle Driver": 160,
    "Peon": 162,
}

RATNAGIRI_PERM_MAP = {
    "Deputy Collector/Expert Officer": 172,
    "Head Clerk": 174,
    "Clerk": 175,
    "Vehicle Driver": 176,
    "Notice Bearer": 178,
    "Peon": 179,
}

RATNAGIRI_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 186,
    "City Architect": 187,
    "Assistant City Architect": 188,
    "Head Clerk": 190,
    "Divisional Officer": 191,
    "Clerk": 192,
    "Vehicle Driver": 193,
    "Peon": 195,
}

SINDHUDURG_PERM_MAP = {
    "Deputy Collector/Expert Officer": 205,
    "Head Clerk": 207,
    "Clerk": 208,
    "Vehicle Driver": 209,
    "Notice Bearer": 211,
    "Peon": 212,
}

SINDHUDURG_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 219,
    "City Architect": 220,
    "Assistant City Architect": 221,
    "Head Clerk": 223,
    "Divisional Officer": 224,
    "Clerk": 225,
    "Vehicle Driver": 226,
    "Peon": 228,
}

DCO_STAFF_PERM_MAP = {
    "Deputy Collector/Expert Officer": 238,
    "Head Clerk": 240,
    "Clerk": 241,
    "Vehicle Driver": 242,
    "Notice Bearer": 244,
    "Peon": 245,
}

DCO_STAFF_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 252,
    "City Architect": 253,
    "Assistant City Architect": 254,
    "Head Clerk": 256,
    "Divisional Officer": 257,
    "Clerk": 258,
    "Vehicle Driver": 259,
    "Peon": 261,
}

DISTRICT_ROW_MAPS = {
    "Mumbai City": (MUMBAI_CITY_PERM_MAP, MUMBAI_CITY_TEMP_MAP),
    "Mumbai Suburban": (MUMBAI_SUBURBAN_PERM_MAP, MUMBAI_SUBURBAN_TEMP_MAP),
    "Thane": (THANE_PERM_MAP, THANE_TEMP_MAP),
    "Palghar": (PALGHAR_PERM_MAP, PALGHAR_TEMP_MAP),
    "Raigad": (RAIGAD_PERM_MAP, RAIGAD_TEMP_MAP),
    "Ratnagiri": (RATNAGIRI_PERM_MAP, RATNAGIRI_TEMP_MAP),
    "Sindhudurg": (SINDHUDURG_PERM_MAP, SINDHUDURG_TEMP_MAP),
    "DCO Staff": (DCO_STAFF_PERM_MAP, DCO_STAFF_TEMP_MAP),
}

COL_MAP = [
    ("D", "sanctioned_posts_2024_25"), ("E", "sanctioned_posts_2025_26"),
    ("F", "special_pay"), ("G", "basic_pay"), ("H", "grade_pay"),
    ("J", "dearness_allowance"), ("K", "local_supplementary_allowance"),
    ("L", "house_rent_allowance"), ("M", "vehicle_allowance"),
    ("N", "washing_allowance"), ("O", "cash_allowance"), ("P", "footwear_allowance_other"),
]


def _write(ws, cell_addr: Optional[str], value):
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_budget_post_details(
    wb: Workbook, db: Session, sub_scheme_code: Optional[str] = None, fiscal_year: Optional[str] = None
):
    from ...config import SHEET_NAMES
    sheet_name = SHEET_NAMES.get("budget_post_details")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]
    da_rate = get_da_rate(db, fiscal_year)
    BudgetPostDetails, _, _, _ = get_scheme_models(sub_scheme_code)
    
    for district, (perm_map, temp_map) in DISTRICT_ROW_MAPS.items():
        _write_block(ws, db, BudgetPostDetails, district, "Permanent", perm_map, da_rate, fiscal_year)
        _write_block(ws, db, BudgetPostDetails, district, "Temporary", temp_map, da_rate, fiscal_year)


def _write_block(ws, db: Session, model, district: str, category: str, row_map: Dict[str, int], da_rate: float, fiscal_year: Optional[str]):
    query = db.query(model).filter(model.district == district, model.category == category)
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)
    records = query.all()
    agg = _aggregate_records(records, row_map, da_rate)
    _write_agg_data(ws, row_map, agg)


def _aggregate_records(records, row_map: Dict[str, int], da_rate: float) -> Dict[str, Dict[str, int]]:
    agg = defaultdict(lambda: {
        "sanctioned_posts_2024_25": 0, "sanctioned_posts_2025_26": 0,
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
        agg[desig]["sanctioned_posts_2024_25"] += int(rec.sanctioned_posts_2024_25 or 0)
        agg[desig]["sanctioned_posts_2025_26"] += int(rec.sanctioned_posts_2025_26 or 0)
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


def _write_agg_data(ws, row_map: Dict[str, int], agg: Dict):
    for desig, data in agg.items():
        row = row_map.get(desig)
        if not row:
            continue
        for col, field in COL_MAP:
            _write(ws, f"{col}{row}", data[field])
