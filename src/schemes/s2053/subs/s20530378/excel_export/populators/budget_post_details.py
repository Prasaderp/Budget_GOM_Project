from typing import Optional, List, Dict
from collections import defaultdict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models
from src.utils_da_rate import get_da_rate
from ...config import DESIGNATIONS, HRA_RATE_MAP


def _write(ws, cell_addr: Optional[str], value):
    if not cell_addr:
        return
    ws[cell_addr].value = value if value is not None else None


def populate_budget_post_details(wb: Workbook, db: Session, sub_scheme_code: Optional[str] = None, fiscal_year: Optional[str] = None):
    from ...config import SHEET_NAMES
    
    sheet_name = SHEET_NAMES.get("budget_post_details")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found in original workbook")
    ws = wb[sheet_name]
    
    # Get DA rate for fiscal year
    da_rate = get_da_rate(db, fiscal_year)

    def addr(col: str, row: int) -> str:
        return f"{col}{row}"

    from ...config import POSITION_ORDER
    
    # 20530378 designations
    perm_designations = [
        'Sub-Divisional Officer',
        'Naib Tehsildar',
        'Stenographer (Lower)',
        'Head Clerk (Awwal Karkun)',
        'Clerk',
        'Vehicle Driver',
        'Peon'
    ]
    
    temp_designations = [
        'Sub-Divisional Officer',
        'Naib Tehsildar',
        'Stenographer (Lower)',
        'Head Clerk (Awwal Karkun)',
        'Clerk',
        'Vehicle Driver',
        'Peon'
    ]

    perm_aliases = {}
    temp_aliases = {}

    def write_block(
        district: str,
        category: str,
        designations: List[str],
        start_row: int,
        designation_aliases: Optional[Dict[str, str]] = None,
    ):
        BudgetPostDetails, _, _, _ = get_scheme_models(sub_scheme_code)
        row_map = {desig: row for desig, row in zip(designations, range(start_row, start_row + len(designations)))}
        query = db.query(BudgetPostDetails).filter(
            BudgetPostDetails.district == district,
            BudgetPostDetails.category == category
        )
        if fiscal_year:
            query = query.filter(BudgetPostDetails.fiscal_year == fiscal_year)
        records: List = query.all()
        agg = defaultdict(lambda: {
            "sanctioned_posts_prev1": 0,
            "sanctioned_posts_curr": 0,
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
        })
        for it in records:
            canonical = designation_aliases.get(it.designation, it.designation) if designation_aliases else it.designation
            if canonical not in row_map:
                continue
            basic_pay = int(float(it.basic_pay or 0))
            grade_pay = int(it.grade_pay or 0)
            base_salary = basic_pay + grade_pay
            
            hra_rate_val = HRA_RATE_MAP.get(it.hra_rate, 0.3)
            dearness_allowance = int(base_salary * da_rate)
            house_rent_allowance = int(base_salary * hra_rate_val)
            
            agg[canonical]["sanctioned_posts_prev1"] += int(it.sanctioned_posts_prev1 or 0)
            agg[canonical]["sanctioned_posts_curr"] += int(it.sanctioned_posts_curr or 0)
            agg[canonical]["special_pay"] += int(it.special_pay or 0)
            agg[canonical]["basic_pay"] += basic_pay
            agg[canonical]["grade_pay"] += grade_pay
            agg[canonical]["dearness_allowance"] += dearness_allowance
            agg[canonical]["local_supplementary_allowance"] += int(it.local_supplementary_allowance or 0)
            agg[canonical]["house_rent_allowance"] += house_rent_allowance
            agg[canonical]["vehicle_allowance"] += int(it.vehicle_allowance or 0)
            agg[canonical]["washing_allowance"] += int(it.washing_allowance or 0)
            agg[canonical]["cash_allowance"] += int(it.cash_allowance or 0)
            agg[canonical]["footwear_allowance_other"] += int(it.footwear_allowance_other or 0)
        for desig, row in row_map.items():
            vals = agg.get(desig)
            if not vals:
                continue
            _write(ws, addr("D", row), vals["sanctioned_posts_prev1"])
            _write(ws, addr("E", row), vals["sanctioned_posts_curr"])
            _write(ws, addr("F", row), vals["special_pay"])
            _write(ws, addr("G", row), vals["basic_pay"])
            _write(ws, addr("H", row), vals["grade_pay"])
            _write(ws, addr("J", row), vals["dearness_allowance"])
            _write(ws, addr("K", row), vals["local_supplementary_allowance"])
            _write(ws, addr("L", row), vals["house_rent_allowance"])
            _write(ws, addr("M", row), vals["vehicle_allowance"])
            _write(ws, addr("N", row), vals["washing_allowance"])
            _write(ws, addr("O", row), vals["cash_allowance"])
            _write(ws, addr("P", row), vals["footwear_allowance_other"])

    # Row blocks for 20530378
    # Format: (district, permanent_start_row, temporary_start_row)
    blocks = [
        ("Mumbai City", 7, 22),
        ("Mumbai Suburban", 37, 52),
        ("Thane", 67, 82),
        ("Palghar", 97, 112),
        ("Raigad", 127, 142),
        ("Ratnagiri", 157, 172),
        ("Sindhudurg", 187, 202),
        ("DCO Staff", 217, 232), 
    ]

    for district, perm_start, temp_start in blocks:
        write_block(district, "Permanent", perm_designations, perm_start, perm_aliases)
        write_block(district, "Temporary", temp_designations, temp_start, temp_aliases)

