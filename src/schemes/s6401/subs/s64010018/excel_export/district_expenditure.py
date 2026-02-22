from typing import Optional
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from ..models import DistrictExpenditure64010018, SUB_SCHEME_CODE

DISTRICT_ROW_MAP = {
    "Thane": 12,
    "Palghar": 13,
    "Raigad": 14,
    "Ratnagiri": 15,
    "Sindhudurg": 16,
}

COL_MAP = {
    "expenditure_2022_23": "C",
    "expenditure_2023_24": "D",
    "expenditure_2024_25": "E",
    "budget_grant_2025_26": "F",
    "revised_estimate_2025_26": "G",
    "budget_estimate_2026_27": "H",
    "remarks": "I",
}

def populate_sheet(
    wb: Workbook,
    db: Session,
    sheet_name: str,
    fiscal_year: Optional[str]
) -> None:
    if sheet_name not in wb.sheetnames:
        ws = wb.active
    else:
        ws = wb[sheet_name]

    query = db.query(DistrictExpenditure64010018).filter(
        DistrictExpenditure64010018.sub_scheme_code == SUB_SCHEME_CODE
    )
    
    if fiscal_year:
        query = query.filter(DistrictExpenditure64010018.fiscal_year == fiscal_year)
        
    records = query.all()
    
    data_map = {r.district: r for r in records}
    
    for district, row_num in DISTRICT_ROW_MAP.items():
        record = data_map.get(district)
        if not record:
            continue
            
        for field, col_letter in COL_MAP.items():
            val = getattr(record, field, 0) or 0
            cell_ref = f"{col_letter}{row_num}"
            ws[cell_ref] = val
