"""Shared Excel populator for s2045 district expenditure sub-schemes.

All 3 sub-schemes (0182, 0251, 0262) are in the SAME Excel file on Sheet 1,
at different row positions. This module provides the shared population logic.
"""
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

# Column mapping for all s2045 district expenditure tables
# Based on Excel template structure analysis
COLUMN_MAP = {
    "expenditure_prev3": "D",
    "expenditure_prev2": "E",
    "expenditure_prev1": "F",
    "budget_estimate_curr": "G",
    "quarterly_expenditure_prev1": "H",
    "budget_estimate_next": "I",
    "remarks": "J",
}

# Row mappings for each sub-scheme
# These MUST match the Excel template exactly

# 20450182: Rows 7-13 for 7 districts
ROW_MAP_20450182 = {
    "Mumbai City": 7,
    "Mumbai Suburban": 8,
    "Thane": 9,
    "Palghar": 10,
    "Raigad": 11,
    "Ratnagiri": 12,
    "Sindhudurg": 13,
}

# 20450251: Rows 25-29 for 5 districts (no Mumbai)
ROW_MAP_20450251 = {
    "Thane": 25,
    "Palghar": 26,
    "Raigad": 27,
    "Ratnagiri": 28,
    "Sindhudurg": 29,
}

# 20450262: Rows 41-47 for 7 districts
ROW_MAP_20450262 = {
    "Mumbai City": 41,
    "Mumbai Suburban": 42,
    "Thane": 43,
    "Palghar": 44,
    "Raigad": 45,
    "Ratnagiri": 46,
    "Sindhudurg": 47,
}


def populate_district_expenditure(
    ws,
    records: List,
    row_map: Dict[str, int],
) -> None:
    """
    Populate worksheet cells with district expenditure data.
    
    Args:
        ws: openpyxl worksheet object
        records: List of DistrictExpenditure model instances
        row_map: District name to row number mapping
    """
    # Build a lookup dict: district -> record
    data_map = {r.district: r for r in records}
    
    for district, row_num in row_map.items():
        record = data_map.get(district)
        if not record:
            continue
        
        for field, col_letter in COLUMN_MAP.items():
            val = getattr(record, field, None)
            cell_ref = f"{col_letter}{row_num}"
            
            if field == "remarks":
                # Remarks can be None or string
                ws[cell_ref] = val if val else ""
            else:
                # Numeric fields default to 0
                ws[cell_ref] = val if val is not None else 0

def get_row_map_for_subscheme(sub_scheme_code: str) -> Dict[str, int]:
    """Get the row mapping for a specific sub-scheme."""
    mappings = {
        "20450182": ROW_MAP_20450182,
        "20450251": ROW_MAP_20450251,
        "20450262": ROW_MAP_20450262,
    }
    return mappings.get(sub_scheme_code, {})

