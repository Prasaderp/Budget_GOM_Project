"""Populator for Page 1 - अर्थसंकल्पीय जिल्हा (Section 1 data)."""
from typing import Optional
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from ..models import DistrictRevenue0029
from ..config import TABLE_SECTIONS

DISTRICTS = [
    "Mumbai City",
    "Mumbai Suburban",
    "Thane",
    "Palghar",
    "Raigad",
    "Ratnagiri",
    "Sindhudurg",
]

SECTION_ROW_MAP = {
    "00290258": 7,
    "00290311": 17,
    "00290383": 27,
    "00290445": 37,
    "00290507": 47,
    "00290572": 57,
    "00290641": 67,
    "00290712": 77,
    "00290249": 87,
    "00290786": 97,
    "00290866": 107,
    "00290937": 117,
    "00291111": 127,
    "00291174": 137,
    "00291245": 147,
    "00291307": 157,
    "00291361": 167,
    "00291541": 177,
    "00291601": 187,
    "00291666": 197,
    "00290991": 207,
    "00291058": 217,
    "00291423": 227,
    "00291488": 237,
    "00291728": 247,
    "00290231": 257,
    "00290857": 267,
    "00291782": 277,
}

COL_MAP = {
    "C": "actual_2017_18",
    "D": "actual_2018_19",
    "E": "actual_2019_20",
    "F": "budget_estimate_2020_21",
    "G": "revised_estimate_2020_21",
    "H": "budget_estimate_2021_22",
}


def populate_section1(
    wb: Workbook,
    db: Session,
    sheet_name: str,
    fiscal_year: Optional[str] = None,
):
    if sheet_name not in wb.sheetnames:
        return
    ws = wb[sheet_name]

    query = db.query(DistrictRevenue0029).filter(
        DistrictRevenue0029.sub_scheme_code == "0029"
    )
    if fiscal_year:
        query = query.filter(DistrictRevenue0029.fiscal_year == fiscal_year)

    records = query.all()

    record_map = {}
    for rec in records:
        key = (rec.table_section_code, rec.district)
        record_map[key] = rec

    for section_code, header_row in SECTION_ROW_MAP.items():
        for idx, district in enumerate(DISTRICTS):
            row = header_row + 1 + idx
            rec = record_map.get((section_code, district))
            if not rec:
                continue
            for col, field in COL_MAP.items():
                value = getattr(rec, field, 0) or 0
                ws[f"{col}{row}"] = value
