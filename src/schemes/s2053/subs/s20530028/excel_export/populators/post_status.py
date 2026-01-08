from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openpyxl.workbook import Workbook

from src.utils_scheme import get_scheme_models


def _write(ws, cell_addr: Optional[str], value):
    if not cell_addr:
        return
    ws[cell_addr].value = value if value is not None else None


def populate_post_status(wb: Workbook, db: Session, sub_scheme_code: Optional[str] = None, fiscal_year: Optional[str] = None):
    from ...config import SHEET_NAMES
    
    _, PostStatus, _, _ = get_scheme_models(sub_scheme_code)
    sheet_name = SHEET_NAMES.get("post_status")
    if sheet_name not in wb.sheetnames:
        raise HTTPException(status_code=500, detail=f"Sheet '{sheet_name}' not found in original workbook")
    ws = wb[sheet_name]
    
    def addr(col: str, row: int) -> str:
        return f"{col}{row}"
    
    filled_cols = {"Class-1 & 2": "C", "Class-3": "D", "Class-4": "E"}
    vacant_cols = {"Class-1 & 2": "G", "Class-3": "H", "Class-4": "I"}

    query = db.query(PostStatus).filter(
        PostStatus.district == "Mumbai City",
        PostStatus.category == "Permanent"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    perm_records: List = query.all()
    for r in perm_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 7), r.posts)
        _write(ws, addr(col, 8), r.salary)
        _write(ws, addr(col, 9), r.grade_pay)
        _write(ws, addr(col, 11), r.special_pay)
        _write(ws, addr(col, 12), r.dearness_allowance)
        _write(ws, addr(col, 13), r.local_supplementary_allowance)
        _write(ws, addr(col, 14), r.house_rent_allowance)
        _write(ws, addr(col, 15), r.travel_allowance)
        _write(ws, addr(col, 16), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Mumbai City",
        PostStatus.category == "Temporary"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    temp_records: List = query.all()
    for r in temp_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 22), r.posts)
        _write(ws, addr(col, 23), r.salary)
        _write(ws, addr(col, 24), r.grade_pay)
        _write(ws, addr(col, 26), r.special_pay)
        _write(ws, addr(col, 27), r.dearness_allowance)
        _write(ws, addr(col, 28), r.local_supplementary_allowance)
        _write(ws, addr(col, 29), r.house_rent_allowance)
        _write(ws, addr(col, 30), r.travel_allowance)
        _write(ws, addr(col, 31), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Mumbai Suburban",
        PostStatus.category == "Permanent"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    ms_perm_records: List = query.all()
    for r in ms_perm_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 40), r.posts)
        _write(ws, addr(col, 41), r.salary)
        _write(ws, addr(col, 42), r.grade_pay)
        _write(ws, addr(col, 44), r.special_pay)
        _write(ws, addr(col, 45), r.dearness_allowance)
        _write(ws, addr(col, 46), r.local_supplementary_allowance)
        _write(ws, addr(col, 47), r.house_rent_allowance)
        _write(ws, addr(col, 48), r.travel_allowance)
        _write(ws, addr(col, 49), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Mumbai Suburban",
        PostStatus.category == "Temporary"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    ms_temp_records: List = query.all()
    for r in ms_temp_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 55), r.posts)
        _write(ws, addr(col, 56), r.salary)
        _write(ws, addr(col, 57), r.grade_pay)
        _write(ws, addr(col, 59), r.special_pay)
        _write(ws, addr(col, 60), r.dearness_allowance)
        _write(ws, addr(col, 61), r.local_supplementary_allowance)
        _write(ws, addr(col, 62), r.house_rent_allowance)
        _write(ws, addr(col, 63), r.travel_allowance)
        _write(ws, addr(col, 64), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Thane",
        PostStatus.category == "Permanent"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    tn_perm_records: List = query.all()
    for r in tn_perm_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 73), r.posts)
        _write(ws, addr(col, 74), r.salary)
        _write(ws, addr(col, 75), r.grade_pay)
        _write(ws, addr(col, 77), r.special_pay)
        _write(ws, addr(col, 78), r.dearness_allowance)
        _write(ws, addr(col, 79), r.local_supplementary_allowance)
        _write(ws, addr(col, 80), r.house_rent_allowance)
        _write(ws, addr(col, 81), r.travel_allowance)
        _write(ws, addr(col, 82), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Thane",
        PostStatus.category == "Temporary"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    tn_temp_records: List = query.all()
    for r in tn_temp_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 88), r.posts)
        _write(ws, addr(col, 89), r.salary)
        _write(ws, addr(col, 90), r.grade_pay)
        _write(ws, addr(col, 92), r.special_pay)
        _write(ws, addr(col, 93), r.dearness_allowance)
        _write(ws, addr(col, 94), r.local_supplementary_allowance)
        _write(ws, addr(col, 95), r.house_rent_allowance)
        _write(ws, addr(col, 96), r.travel_allowance)
        _write(ws, addr(col, 97), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Palghar",
        PostStatus.category == "Permanent"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    pg_perm_records: List = query.all()
    for r in pg_perm_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 106), r.posts)
        _write(ws, addr(col, 107), r.salary)
        _write(ws, addr(col, 108), r.grade_pay)
        _write(ws, addr(col, 110), r.special_pay)
        _write(ws, addr(col, 111), r.dearness_allowance)
        _write(ws, addr(col, 112), r.local_supplementary_allowance)
        _write(ws, addr(col, 113), r.house_rent_allowance)
        _write(ws, addr(col, 114), r.travel_allowance)
        _write(ws, addr(col, 115), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Palghar",
        PostStatus.category == "Temporary"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    pg_temp_records: List = query.all()
    for r in pg_temp_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 121), r.posts)
        _write(ws, addr(col, 122), r.salary)
        _write(ws, addr(col, 123), r.grade_pay)
        _write(ws, addr(col, 125), r.special_pay)
        _write(ws, addr(col, 126), r.dearness_allowance)
        _write(ws, addr(col, 127), r.local_supplementary_allowance)
        _write(ws, addr(col, 128), r.house_rent_allowance)
        _write(ws, addr(col, 129), r.travel_allowance)
        _write(ws, addr(col, 130), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Raigad",
        PostStatus.category == "Permanent"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    rg_perm_records: List = query.all()
    for r in rg_perm_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 139), r.posts)
        _write(ws, addr(col, 140), r.salary)
        _write(ws, addr(col, 141), r.grade_pay)
        _write(ws, addr(col, 143), r.special_pay)
        _write(ws, addr(col, 144), r.dearness_allowance)
        _write(ws, addr(col, 145), r.local_supplementary_allowance)
        _write(ws, addr(col, 146), r.house_rent_allowance)
        _write(ws, addr(col, 147), r.travel_allowance)
        _write(ws, addr(col, 148), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Raigad",
        PostStatus.category == "Temporary"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    rg_temp_records: List = query.all()
    for r in rg_temp_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 154), r.posts)
        _write(ws, addr(col, 155), r.salary)
        _write(ws, addr(col, 156), r.grade_pay)
        _write(ws, addr(col, 158), r.special_pay)
        _write(ws, addr(col, 159), r.dearness_allowance)
        _write(ws, addr(col, 160), r.local_supplementary_allowance)
        _write(ws, addr(col, 161), r.house_rent_allowance)
        _write(ws, addr(col, 162), r.travel_allowance)
        _write(ws, addr(col, 163), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Ratnagiri",
        PostStatus.category == "Permanent"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    rt_perm_records: List = query.all()
    for r in rt_perm_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 172), r.posts)
        _write(ws, addr(col, 173), r.salary)
        _write(ws, addr(col, 174), r.grade_pay)
        _write(ws, addr(col, 176), r.special_pay)
        _write(ws, addr(col, 177), r.dearness_allowance)
        _write(ws, addr(col, 178), r.local_supplementary_allowance)
        _write(ws, addr(col, 179), r.house_rent_allowance)
        _write(ws, addr(col, 180), r.travel_allowance)
        _write(ws, addr(col, 181), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Ratnagiri",
        PostStatus.category == "Temporary"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    rt_temp_records: List = query.all()
    for r in rt_temp_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 187), r.posts)
        _write(ws, addr(col, 188), r.salary)
        _write(ws, addr(col, 189), r.grade_pay)
        _write(ws, addr(col, 191), r.special_pay)
        _write(ws, addr(col, 192), r.dearness_allowance)
        _write(ws, addr(col, 193), r.local_supplementary_allowance)
        _write(ws, addr(col, 194), r.house_rent_allowance)
        _write(ws, addr(col, 195), r.travel_allowance)
        _write(ws, addr(col, 196), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Sindhudurg",
        PostStatus.category == "Permanent"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    sd_perm_records: List = query.all()
    for r in sd_perm_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 205), r.posts)
        _write(ws, addr(col, 206), r.salary)
        _write(ws, addr(col, 207), r.grade_pay)
        _write(ws, addr(col, 209), r.special_pay)
        _write(ws, addr(col, 210), r.dearness_allowance)
        _write(ws, addr(col, 211), r.local_supplementary_allowance)
        _write(ws, addr(col, 212), r.house_rent_allowance)
        _write(ws, addr(col, 213), r.travel_allowance)
        _write(ws, addr(col, 214), r.other)

    query = db.query(PostStatus).filter(
        PostStatus.district == "Sindhudurg",
        PostStatus.category == "Temporary"
    )
    if fiscal_year:
        query = query.filter(PostStatus.fiscal_year == fiscal_year)
    sd_temp_records: List = query.all()
    for r in sd_temp_records:
        col = filled_cols.get(r.class_type) if r.status == "Filled" else vacant_cols.get(r.class_type) if r.status == "Vacant" else None
        if not col:
            continue
        _write(ws, addr(col, 220), r.posts)
        _write(ws, addr(col, 221), r.salary)
        _write(ws, addr(col, 222), r.grade_pay)
        _write(ws, addr(col, 224), r.special_pay)
        _write(ws, addr(col, 225), r.dearness_allowance)
        _write(ws, addr(col, 226), r.local_supplementary_allowance)
        _write(ws, addr(col, 227), r.house_rent_allowance)
        _write(ws, addr(col, 228), r.travel_allowance)
        _write(ws, addr(col, 229), r.other)
