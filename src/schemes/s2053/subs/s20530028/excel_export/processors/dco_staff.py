from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter

DISTRICT_ROW_RANGES = {
    "budget_post_details": (141, 186),
    "post_status": (100, 133),
    "post_expenses": (49, 64),
    "unit_expenditure": (70, 92)
}

SHEETS_TO_EXCLUDE = ["Page-5", "Table-D", "Distrs.wise Abstract"]

def apply_district_filtering(source_sheet: Worksheet, sheet_key: str):
    range_info = DISTRICT_ROW_RANGES.get(sheet_key)
    if not range_info:
        return
    
    start_row, end_row = range_info
    rows_to_delete = []
    
    for row_num in range(1, source_sheet.max_row + 1):
        if not (start_row <= row_num <= end_row):
            rows_to_delete.append(row_num)
    
    for row_num in reversed(rows_to_delete):
        source_sheet.delete_rows(row_num)

def apply_abstract_filtering(source_sheet: Worksheet):
    pass

