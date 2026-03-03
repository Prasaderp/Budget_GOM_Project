"""
Fiscal year label generator for s2053 sub-schemes.

Converts a relative_years dict (from get_relative_fiscal_years) into
dynamic column header labels used across budget_post_details,
unit_expenditure, and budget_summary views.

Usage:
    from src.utils_fiscal_year import get_relative_fiscal_years
    ry = get_relative_fiscal_years("2025-26")
    labels = FiscalYearLabels(ry)
    labels.budget_post_col_keys  # ["Approved Posts 2024-25", "Approved Posts 2025-26", ...]
    labels.unit_expenditure_headers  # {internal_key: "Marathi header with year", ...}
    labels.summary_title            # "अर्थसंकल्पीय अंदाजपत्रक सन 2025-2026"
"""
from typing import Dict, List


class FiscalYearLabels:
    __slots__ = ("ry",)

    def __init__(self, relative_years: dict):
        self.ry = relative_years

    @property
    def curr(self) -> dict:
        return self.ry.get("fy_curr", {})

    @property
    def prev1(self) -> dict:
        return self.ry.get("fy_prev1", {})

    @property
    def prev2(self) -> dict:
        return self.ry.get("fy_prev2", {})

    @property
    def prev3(self) -> dict:
        return self.ry.get("fy_prev3", {})

    @property
    def prev4(self) -> dict:
        return self.ry.get("fy_prev4", {})

    @property
    def summary_title(self) -> str:
        return f"अर्थसंकल्पीय अंदाजपत्रक सन {self.curr.get('full', '')}"

    @property
    def budget_post_col_keys(self) -> List[str]:
        p1 = self.prev1.get("short", "")
        c = self.curr.get("short", "")
        return [
            f"Approved Posts {p1}",
            f"Approved Posts {c}",
            "Special Pay", "Basic Pay", "Grade Pay", "Total Pay",
            "Dearness Allowance 64%", "Local Supplementary Allowance",
            "House Rent Allowance", "Vehicle Allowance",
            "Washing Allowance", "Cash Allowance",
            "Footwear Allowance / Others", "Total",
        ]

    @property
    def budget_post_excel_col_order(self) -> List[str]:
        p1 = self.prev1.get("short", "")
        c = self.curr.get("short", "")
        return [
            "Sr No.", "Class", "Position",
            f"Approved Posts {p1}", f"Approved Posts {c}",
            "Special Pay", "Basic Pay", "Grade Pay", "Total Pay",
            "Dearness Allowance 64%", "Local Supplementary Allowance",
            "House Rent Allowance", "Vehicle Allowance",
            "Washing Allowance", "Cash Allowance",
            "Footwear Allowance / Others", "Total",
        ]

    @property
    def unit_expenditure_headers(self) -> Dict[str, str]:
        p4 = self.prev4.get("full", "")
        p3 = self.prev3.get("full", "")
        p2 = self.prev2.get("full", "")
        p1 = self.prev1.get("full", "")
        c = self.curr.get("full", "")
        return {
            "SrNo": "अ. क्र.",
            "UnitAccount": "लेख्याची प्राथमिक आणि दुय्यम युनिट",
            "expenditure_prev4": f"प्रत्यक्ष रक्कमा {p4}",
            "expenditure_prev3": f"प्रत्यक्ष रक्कमा {p3}",
            "expenditure_prev2": f"प्रत्यक्ष रक्कमा {p2}",
            "budget_prev1": f"अर्थसंकल्पीय अंदाज {p1}",
            "forecast_prev1": f"सुधारीत अंदाज {p1}",
            "budget_curr_estimating_officer": f"अर्थसंकल्पीय {c} प्राकक्लन",
            "budget_curr_controlling_officer": f"अर्थसंकल्पीय {c} नियंत्रक",
            "budget_curr_admin_dept": f"अर्थसंकल्पीय {c} प्रशासकीय",
            "budget_curr_finance_dept": f"अर्थसंकल्पीय {c} वित्त",
        }

    def approved_posts_key(self, period: str) -> str:
        fy = self.ry.get(period, {})
        return f"Approved Posts {fy.get('short', '')}"
