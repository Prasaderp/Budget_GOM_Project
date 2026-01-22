"""Excel populator for scheme 2215 district expenditure.

Handles two account heads (2215A195, 2215A201) with separate row mappings.
"""
from typing import Optional
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from ..models import DistrictExpenditure2215, SUB_SCHEME_CODE

# Row mappings for each account head (from Excel template analysis)
SECTION_ROW_MAP = {
    "2215A195": {
        "Chief Executive Officer, Zilla Parishad Thane": 8,
        "Chief Executive Officer, Zilla Parishad Palghar": 9,
        "Chief Executive Officer, Zilla Parishad Raigad": 10,
        "Chief Executive Officer, Zilla Parishad Ratnagiri": 11,
        "Chief Executive Officer, Zilla Parishad Sindhudurg": 12,
    },
    "2215A201": {
        "Collector Thane": 15,
        "Collector Palghar": 16,
        "Collector Raigad": 17,
        "Collector Ratnagiri": 18,
        "Collector Sindhudurg": 19,
    },
}

# Column mapping for data fields
COL_MAP = {
    "expenditure_2022_23": "D",
    "expenditure_2023_24": "E",
    "expenditure_2024_25": "F",
    "budget_estimate_2025_26": "G",
    "revised_demand_2025_26": "H",
    "budget_estimate_2026_27": "I",
}


def populate_sheet(
    wb: Workbook,
    db: Session,
    sheet_name: str,
    fiscal_year: Optional[str]
) -> None:
    """Populate the Excel sheet with district expenditure data for both account heads."""
    ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active

    query = db.query(DistrictExpenditure2215).filter(
        DistrictExpenditure2215.sub_scheme_code == SUB_SCHEME_CODE
    )
    
    if fiscal_year:
        query = query.filter(DistrictExpenditure2215.fiscal_year == fiscal_year)
        
    records = query.all()
    
    # Group records by (account_head_code, district)
    data_map = {(r.account_head_code, r.district): r for r in records}
    
    # Write data for each section
    for account_head, district_rows in SECTION_ROW_MAP.items():
        for district, row_num in district_rows.items():
            record = data_map.get((account_head, district))
            if not record:
                continue
                
            for field, col_letter in COL_MAP.items():
                val = getattr(record, field, 0) or 0
                ws[f"{col_letter}{row_num}"] = val
