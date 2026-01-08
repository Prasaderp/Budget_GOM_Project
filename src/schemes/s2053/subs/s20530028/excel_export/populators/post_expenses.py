from typing import Optional, List, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models


def _write(ws, cell_addr: Optional[str], value):
    if not cell_addr:
        return
    ws[cell_addr].value = value if value is not None else None


def populate_post_expenses(wb: Workbook, db: Session, sub_scheme_code: Optional[str] = None, fiscal_year: Optional[str] = None):
    from ...config import SHEET_NAMES, POST_EXPENSES_DISTRICT_COMPONENT
    
    sheet_name = SHEET_NAMES.get("post_expenses")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found in original workbook")
    ws = wb[sheet_name]
    
    def addr(col: str, row: int) -> str:
        return f"{col}{row}"

    _, _, PostExpenses, _ = get_scheme_models(sub_scheme_code)
    
    def aggregate_counts(records: List) -> Dict[str, Dict[str, int]]:
        result: Dict[str, Dict[str, int]] = {}
        for r in records:
            cls = str(r.class_type)
            if cls not in result:
                result[cls] = {"filled": 0, "vacant": 0}
            result[cls]["filled"] += int(r.filled_posts or 0)
            result[cls]["vacant"] += int(r.vacant_posts or 0)
        return result

    def write_for_district(district: str, row_map: Dict[str, int], fixed_row: int):
        query_perm = db.query(PostExpenses).filter(
            PostExpenses.district == district,
            PostExpenses.category == "Permanent"
        )
        if fiscal_year:
            query_perm = query_perm.filter(PostExpenses.fiscal_year == fiscal_year)
        perm_records: List = query_perm.all()
        
        query_temp = db.query(PostExpenses).filter(
            PostExpenses.district == district,
            PostExpenses.category == "Temporary"
        )
        if fiscal_year:
            query_temp = query_temp.filter(PostExpenses.fiscal_year == fiscal_year)
        temp_records: List = query_temp.all()
        
        perm_counts = aggregate_counts(perm_records)
        temp_counts = aggregate_counts(temp_records)
        for cls, row in row_map.items():
            _write(ws, addr("C", row), perm_counts.get(cls, {}).get("filled"))
            _write(ws, addr("D", row), perm_counts.get(cls, {}).get("vacant"))
        for cls, row in row_map.items():
            _write(ws, addr("E", row), temp_counts.get(cls, {}).get("filled"))
            _write(ws, addr("F", row), temp_counts.get(cls, {}).get("vacant"))
        query_rep = db.query(PostExpenses).filter(PostExpenses.district == district)
        if fiscal_year:
            query_rep = query_rep.filter(PostExpenses.fiscal_year == fiscal_year)
        representative = query_rep.first()
        if representative:
            active_component = POST_EXPENSES_DISTRICT_COMPONENT.get(district)
            if active_component == 'SeventhPayCommissionDifferenceNPS':
                selected_value = representative.seventh_pay_commission_difference_nps
            elif active_component == 'NPS':
                selected_value = representative.nps
            elif active_component == 'SeventhPayCommissionDifference':
                selected_value = representative.seventh_pay_commission_difference
            else:
                selected_value = None
            fixed_values = [
                representative.medical_expenses,
                representative.festival_advance,
                representative.swagram_maharashtra_darshan,
                selected_value,
                representative.other,
            ]
            fixed_cols = ["C", "D", "E", "F", "G"]
            for col, val in zip(fixed_cols, fixed_values):
                _write(ws, addr(col, fixed_row), val)

    write_for_district("Mumbai City", {"1": 6, "2": 7, "3": 8, "4": 9}, 15)
    write_for_district("Mumbai Suburban", {"1": 22, "2": 23, "3": 24, "4": 25}, 31)
    write_for_district("Thane", {"1": 38, "2": 39, "3": 40, "4": 41}, 47)
    write_for_district("Palghar", {"1": 54, "2": 55, "3": 56, "4": 57}, 63)
    write_for_district("Raigad", {"1": 70, "2": 71, "3": 72, "4": 73}, 79)
    write_for_district("Ratnagiri", {"1": 86, "2": 87, "3": 88, "4": 89}, 95)
    write_for_district("Sindhudurg", {"1": 102, "2": 103, "3": 104, "4": 105}, 111)
