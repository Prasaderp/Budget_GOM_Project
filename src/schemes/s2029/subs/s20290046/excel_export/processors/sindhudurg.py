"""Sindhudurg processor for sub-scheme 20290046."""
from openpyxl.utils import get_column_letter

DISTRICT_ROW_RANGES = {
    "budget_post_details": (198, 229),
    "post_status": (197, 228),
    "post_expenses": (97, 111),
    "unit_expenditure": (102, 117),
}

SHEETS_TO_EXCLUDE = []


def apply_district_filtering(source_sheet, sheet_key):
    range_info = DISTRICT_ROW_RANGES.get(sheet_key)
    if not range_info:
        return
    start_row, end_row = range_info
    rows_to_delete = [r for r in range(1, source_sheet.max_row + 1) if not (start_row <= r <= end_row)]
    for row_num in reversed(rows_to_delete):
        source_sheet.delete_rows(row_num)


def apply_abstract_filtering(source_sheet):
    pass
