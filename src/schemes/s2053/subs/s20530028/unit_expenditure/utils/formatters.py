"""Formatting utilities for unit expenditure"""
from typing import List, Dict, Any
from ...models import UnitExpenditure
from ...config import UNIT_ACCOUNT_MAP_MR


def get_columns_to_sum() -> List:
    """Get list of columns to sum for aggregations"""
    return [
        UnitExpenditure.expenditure_2021_22,
        UnitExpenditure.expenditure_2022_23,
        UnitExpenditure.expenditure_2023_24,
        UnitExpenditure.budget_2024_25,
        UnitExpenditure.forecast_2024_25,
        UnitExpenditure.budget_2025_26_estimating_officer,
        UnitExpenditure.budget_2025_26_controlling_officer,
        UnitExpenditure.budget_2025_26_admin_dept,
        UnitExpenditure.budget_2025_26_finance_dept
    ]


def get_internal_data_keys() -> List[str]:
    """Get list of internal data keys (column names)"""
    return [col.name for col in get_columns_to_sum()]


def get_ordered_keys() -> List[str]:
    """Get ordered list of keys for display"""
    return ["SrNo", "UnitAccount"] + get_internal_data_keys()


def get_headers_map() -> Dict[str, str]:
    """Get mapping of internal keys to Marathi headers"""
    return {
        "SrNo": "अ. क्र.",
        "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट",
        "expenditure_2021_22": "प्रत्यक्ष रक्कमा 2021-2022",
        "expenditure_2022_23": "प्रत्यक्ष रक्कमा 2022-2023",
        "expenditure_2023_24": "प्रत्यक्ष रक्कमा 2023-2024",
        "budget_2024_25": "अर्थसंकल्पीय अंदाज 2024-2025",
        "forecast_2024_25": "सुधारीत अंदाज 2024-2025",
        "budget_2025_26_estimating_officer": "अर्थसंकल्पीय 2025-2026 प्राकक्लन",
        "budget_2025_26_controlling_officer": "अर्थसंकल्पीय 2025-2026 नियंत्रक",
        "budget_2025_26_admin_dept": "अर्थसंकल्पीय 2025-2026 प्रशासकीय",
        "budget_2025_26_finance_dept": "अर्थसंकल्पीय 2025-2026 वित्त",
    }


def format_summary_row(row: Any, index: int, internal_keys: List[str]) -> Dict[str, Any]:
    """Format a summary row with Marathi translation"""
    ua = row.unit_account or ""
    rd = {
        "SrNo": index,
        "UnitAccount": UNIT_ACCOUNT_MAP_MR.get(ua, ua),
        "UnitAccount_EN": ua
    }
    for k in internal_keys:
        v = int(getattr(row, k, 0) or 0)
        rd[k] = v
    return rd

