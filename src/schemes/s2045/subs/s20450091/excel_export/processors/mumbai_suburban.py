from openpyxl.utils import get_column_letter

# District-specific row ranges for 20450091
# Mumbai Suburban: 31-60
DISTRICT_ROW_RANGES = {
    "budget_post_details": (30, 58),
    "post_status": (33, 65),
    "post_expenses": (17, 32),
    "unit_expenditure": (23, 44)
}

DISTRICT_WISE_ABSTRACT_RANGE = (21, 40, ['A', 'B', 'C'])

SHEETS_TO_EXCLUDE = ["Page-5", "Table-D"]

def apply_district_filtering(source_sheet, sheet_key):
    range_info = DISTRICT_ROW_RANGES.get(sheet_key)
    
    if range_info:
        if len(range_info) == 3:
            start_row, end_row, cols_to_include = range_info
        else:
            start_row, end_row = range_info
            cols_to_include = None
        
        rows_to_delete = []
        for row_num in range(1, source_sheet.max_row + 1):
            if not (start_row <= row_num <= end_row):
                rows_to_delete.append(row_num)
        
        for row_num in reversed(rows_to_delete):
            source_sheet.delete_rows(row_num)
        
        if cols_to_include:
            cols_to_delete = []
            for col_num in range(1, source_sheet.max_column + 1):
                col_letter = get_column_letter(col_num)
                if col_letter not in cols_to_include:
                    cols_to_delete.append(col_num)
            
            for col_num in reversed(cols_to_delete):
                source_sheet.delete_cols(col_num)

def apply_abstract_filtering(source_sheet):
    start_row, end_row, cols_to_include = DISTRICT_WISE_ABSTRACT_RANGE
    
    # Logic for abstract filtering if needed
    pass
