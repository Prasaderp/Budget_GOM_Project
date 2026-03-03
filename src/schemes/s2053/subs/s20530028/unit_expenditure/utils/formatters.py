"""Formatting utilities for unit expenditure"""
from typing import List, Dict, Any
from ...models import UnitExpenditure
from ...config import UNIT_ACCOUNT_MAP_MR


def get_columns_to_sum() -> List:
    """Get list of columns to sum for aggregations"""
    return [
        UnitExpenditure.expenditure_prev4,
        UnitExpenditure.expenditure_prev3,
        UnitExpenditure.expenditure_prev2,
        UnitExpenditure.budget_prev1,
        UnitExpenditure.forecast_prev1,
        UnitExpenditure.budget_curr_estimating_officer,
        UnitExpenditure.budget_curr_controlling_officer,
        UnitExpenditure.budget_curr_admin_dept,
        UnitExpenditure.budget_curr_finance_dept
    ]


def get_internal_data_keys() -> List[str]:
    """Get list of internal data keys (column names)"""
    return [col.name for col in get_columns_to_sum()]


def get_ordered_keys() -> List[str]:
    """Get ordered list of keys for display"""
    return ["SrNo", "UnitAccount"] + get_internal_data_keys()


from src.utils_fiscal_year import get_relative_fiscal_years

def get_headers_map(fiscal_year: str = '2025-26') -> Dict[str, str]:
    """Get mapping of internal keys to Marathi headers"""
    ry = get_relative_fiscal_years(fiscal_year)
    return {
        "SrNo": "अ. क्र.",
        "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट",
        "expenditure_prev4": f"प्रत्यक्ष रक्कमा {ry['fy_prev4']['full']}",
        "expenditure_prev3": f"प्रत्यक्ष रक्कमा {ry['fy_prev3']['full']}",
        "expenditure_prev2": f"प्रत्यक्ष रक्कमा {ry['fy_prev2']['full']}",
        "budget_prev1": f"अर्थसंकल्पीय अंदाज {ry['fy_prev1']['full']}",
        "forecast_prev1": f"सुधारीत अंदाज {ry['fy_prev1']['full']}",
        "budget_curr_estimating_officer": f"अर्थसंकल्पीय {ry['fy_curr']['full']} प्राकक्लन",
        "budget_curr_controlling_officer": f"अर्थसंकल्पीय {ry['fy_curr']['full']} नियंत्रक",
        "budget_curr_admin_dept": f"अर्थसंकल्पीय {ry['fy_curr']['full']} प्रशासकीय",
        "budget_curr_finance_dept": f"अर्थसंकल्पीय {ry['fy_curr']['full']} वित्त",
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

