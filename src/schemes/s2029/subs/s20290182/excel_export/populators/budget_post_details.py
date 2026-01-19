"""Budget post details populator for sub-scheme 20290182.

Uses hardcoded row mappings due to merged cells in Excel template.
Mappings must match exact Excel row numbers for each district.
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
    "Head Clerk (Awwal Karkun)": 7,
    "Clerk": 8,
    "Peon": 10,
}

MUMBAI_CITY_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 17,
    "Naib Tehsildar": 18,
    "Head Clerk (Awwal Karkun)": 20,
    "Sub-Divisional Officer": 21,
    "Clerical": 22,
    "Divisional Officer": 23,
    "Talathi": 24,
    "Clerk": 25,
    "Vehicle Driver": 26,
    "Peon": 28,
    "Mahar Keri": 29,
}

MUMBAI_SUBURBAN_PERM_MAP = {
    "Head Clerk (Awwal Karkun)": 39,
    "Clerk": 40,
    "Peon": 42,
}

MUMBAI_SUBURBAN_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 49,
    "Naib Tehsildar": 50,
    "Head Clerk (Awwal Karkun)": 52,
    "Sub-Divisional Officer": 53,
    "Clerical": 54,
    "Divisional Officer": 55,
    "Talathi": 56,
    "Clerk": 57,
    "Vehicle Driver": 58,
    "Peon": 60,
    "Mahar Keri": 61,
}

THANE_PERM_MAP = {
    "Head Clerk (Awwal Karkun)": 71,
    "Clerk": 72,
    "Peon": 74,
}

THANE_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 81,
    "Naib Tehsildar": 82,
    "Head Clerk (Awwal Karkun)": 84,
    "Sub-Divisional Officer": 85,
    "Clerical": 86,
    "Divisional Officer": 87,
    "Talathi": 88,
    "Clerk": 89,
    "Vehicle Driver": 90,
    "Peon": 92,
    "Mahar Keri": 93,
}

PALGHAR_PERM_MAP = {
    "Head Clerk (Awwal Karkun)": 102,
    "Clerk": 103,
    "Peon": 105,
}

PALGHAR_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 112,
    "Naib Tehsildar": 113,
    "Head Clerk (Awwal Karkun)": 115,
    "Sub-Divisional Officer": 116,
    "Clerical": 117,
    "Divisional Officer": 118,
    "Talathi": 119,
    "Clerk": 120,
    "Vehicle Driver": 121,
    "Peon": 123,
    "Mahar Keri": 124,
}

RAIGAD_PERM_MAP = {
    "Head Clerk (Awwal Karkun)": 134,
    "Clerk": 135,
    "Peon": 137,
}

RAIGAD_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 144,
    "Naib Tehsildar": 145,
    "Head Clerk (Awwal Karkun)": 147,
    "Sub-Divisional Officer": 148,
    "Clerical": 149,
    "Divisional Officer": 150,
    "Talathi": 151,
    "Clerk": 152,
    "Vehicle Driver": 153,
    "Peon": 155,
    "Mahar Keri": 156,
}

RATNAGIRI_PERM_MAP = {
    "Head Clerk (Awwal Karkun)": 166,
    "Clerk": 167,
    "Peon": 169,
}

RATNAGIRI_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 176,
    "Naib Tehsildar": 177,
    "Head Clerk (Awwal Karkun)": 179,
    "Sub-Divisional Officer": 180,
    "Clerical": 181,
    "Divisional Officer": 182,
    "Talathi": 183,
    "Clerk": 184,
    "Vehicle Driver": 185,
    "Peon": 187,
    "Mahar Keri": 188,
}

SINDHUDURG_PERM_MAP = {
    "Head Clerk (Awwal Karkun)": 198,
    "Clerk": 199,
    "Peon": 201,
}

SINDHUDURG_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 208,
    "Naib Tehsildar": 209,
    "Head Clerk (Awwal Karkun)": 211,
    "Sub-Divisional Officer": 212,
    "Clerical": 213,
    "Divisional Officer": 214,
    "Talathi": 215,
    "Clerk": 216,
    "Vehicle Driver": 217,
    "Peon": 219,
    "Mahar Keri": 220,
}

DCO_STAFF_PERM_MAP = {
    "Head Clerk (Awwal Karkun)": 230,
    "Clerk": 231,
    "Peon": 233,
}

DCO_STAFF_TEMP_MAP = {
    "Deputy Collector/Expert Officer": 240,
    "Naib Tehsildar": 241,
    "Head Clerk (Awwal Karkun)": 243,
    "Sub-Divisional Officer": 244,
    "Clerical": 245,
    "Divisional Officer": 246,
    "Talathi": 247,
    "Clerk": 248,
    "Vehicle Driver": 249,
    "Peon": 251,
    "Mahar Keri": 252,
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
    ("D", "sanctioned_posts_2024_25"),
    ("E", "sanctioned_posts_2025_26"),
    ("F", "special_pay"),
    ("G", "basic_pay"),
    ("H", "grade_pay"),
    ("J", "dearness_allowance"),
    ("K", "local_supplementary_allowance"),
    ("L", "house_rent_allowance"),
    ("M", "vehicle_allowance"),
    ("N", "washing_allowance"),
    ("O", "cash_allowance"),
    ("P", "footwear_allowance_other"),
]


def _write(ws, cell_addr: Optional[str], value):
    if cell_addr:
        ws[cell_addr].value = value if value is not None else None


def populate_budget_post_details(
    wb: Workbook,
    db: Session,
    sub_scheme_code: Optional[str] = None,
    fiscal_year: Optional[str] = None,
):
    from ...config import SHEET_NAMES

    sheet_name = SHEET_NAMES.get("budget_post_details")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found")
    ws = wb[sheet_name]
    da_rate = get_da_rate(db, fiscal_year)
    BudgetPostDetails, _, _, _ = get_scheme_models(sub_scheme_code)

    for district, (perm_map, temp_map) in DISTRICT_ROW_MAPS.items():
        _write_block(
            ws,
            db,
            BudgetPostDetails,
            district,
            "Permanent",
            perm_map,
            da_rate,
            fiscal_year,
        )
        _write_block(
            ws,
            db,
            BudgetPostDetails,
            district,
            "Temporary",
            temp_map,
            da_rate,
            fiscal_year,
        )


def _write_block(
    ws,
    db: Session,
    model,
    district: str,
    category: str,
    row_map: Dict[str, int],
    da_rate: float,
    fiscal_year: Optional[str],
):
    query = db.query(model).filter(
        model.district == district,
        model.category == category,
    )
    if fiscal_year:
        query = query.filter(model.fiscal_year == fiscal_year)
    records = query.all()
    agg = _aggregate_records(records, row_map, da_rate)
    _write_agg_data(ws, row_map, agg)


def _aggregate_records(records, row_map: Dict[str, int], da_rate: float):
    agg = defaultdict(
        lambda: {
            "sanctioned_posts_2024_25": 0,
            "sanctioned_posts_2025_26": 0,
            "special_pay": 0,
            "basic_pay": 0,
            "grade_pay": 0,
            "dearness_allowance": 0,
            "local_supplementary_allowance": 0,
            "house_rent_allowance": 0,
            "vehicle_allowance": 0,
            "washing_allowance": 0,
            "cash_allowance": 0,
            "footwear_allowance_other": 0,
        }
    )
    for rec in records:
        desig = rec.designation
        if desig not in row_map:
            continue
        basic_pay = int(float(rec.basic_pay or 0))
        grade_pay = int(rec.grade_pay or 0)
        base_salary = basic_pay + grade_pay
        hra_rate_val = HRA_RATE_MAP.get(rec.hra_rate, 0.3)
        agg[desig]["sanctioned_posts_2024_25"] += int(
            rec.sanctioned_posts_2024_25 or 0
        )
        agg[desig]["sanctioned_posts_2025_26"] += int(
            rec.sanctioned_posts_2025_26 or 0
        )
        agg[desig]["special_pay"] += int(rec.special_pay or 0)
        agg[desig]["basic_pay"] += basic_pay
        agg[desig]["grade_pay"] += grade_pay
        agg[desig]["dearness_allowance"] += int(base_salary * da_rate)
        agg[desig]["local_supplementary_allowance"] += int(
            rec.local_supplementary_allowance or 0
        )
        agg[desig]["house_rent_allowance"] += int(base_salary * hra_rate_val)
        agg[desig]["vehicle_allowance"] += int(rec.vehicle_allowance or 0)
        agg[desig]["washing_allowance"] += int(rec.washing_allowance or 0)
        agg[desig]["cash_allowance"] += int(rec.cash_allowance or 0)
        agg[desig]["footwear_allowance_other"] += int(
            rec.footwear_allowance_other or 0
        )
    return agg


def _write_agg_data(ws, row_map: Dict[str, int], agg):
    for desig, data in agg.items():
        row = row_map.get(desig)
        if not row:
            continue
        for col, field in COL_MAP:
            _write(ws, f"{col}{row}", data[field])

