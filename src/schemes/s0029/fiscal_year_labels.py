"""
Fiscal year label generator for scheme 0029 — Land Revenue Receipts.

Converts a relative_years dict (from get_relative_fiscal_years) into
dynamic column header labels used in section1 (list + form + inline-edit)
and section2 (summary list) views.

The s0029 revenue table has 6 year columns:
  - 3 actual revenue columns       (prev3, prev2, prev1)
  - Budget estimate (curr)
  - Revised estimate (curr, tagged "सुधारीत")
  - Budget estimate next (next1)

Note: This scheme uses "जमा" (revenue) terminology, not "खर्च" (expenditure).

Usage:
    from src.utils_fiscal_year import get_relative_fiscal_years
    ry = get_relative_fiscal_years("2025-26")
    labels = FiscalYearLabels0029(ry)
    labels.list_headers        # ordered header dict for section1/section2 tables
    labels.form_labels         # dict for section1 edit form fields
    labels.inline_edit_labels  # dict for section1 inline quick-edit form
"""
from __future__ import annotations

from typing import Dict


class FiscalYearLabels0029:
    """Immutable, zero-allocation label resolver for s0029 revenue views."""

    __slots__ = ("ry",)

    def __init__(self, relative_years: dict) -> None:
        self.ry = relative_years

    # ------------------------------------------------------------------
    # shorthand accessors
    # ------------------------------------------------------------------
    @property
    def prev3(self) -> dict:
        return self.ry.get("fy_prev3", {})

    @property
    def prev2(self) -> dict:
        return self.ry.get("fy_prev2", {})

    @property
    def prev1(self) -> dict:
        return self.ry.get("fy_prev1", {})

    @property
    def curr(self) -> dict:
        return self.ry.get("fy_curr", {})

    @property
    def next1(self) -> dict:
        return self.ry.get("fy_next1", {})

    # ------------------------------------------------------------------
    # table column headers — section1_list & section2_list views
    # ------------------------------------------------------------------
    @property
    def list_headers(self) -> Dict[str, str]:
        """Column headers for section1 and section2 tables."""
        c = self.curr.get("short", "")
        n = self.next1.get("short", "")
        return {
            "actual_prev3": self.prev3.get("short", ""),
            "actual_prev2": self.prev2.get("short", ""),
            "actual_prev1": self.prev1.get("short", ""),
            "budget_estimate_curr": f"अर्थसंकल्पीय जमा अंदाज ({c})",
            "revised_estimate_curr": f"सुधारीत जमा अंदाज ({c})",
            "budget_estimate_next": f"अर्थसंकल्पीय जमा अंदाजपत्रक ({n})",
        }

    # ------------------------------------------------------------------
    # form labels — section1 edit form view
    # ------------------------------------------------------------------
    @property
    def form_labels(self) -> Dict[str, str]:
        """Map of logical field names → Marathi display labels with year."""
        c = self.curr.get("short", "")
        n = self.next1.get("short", "")
        return {
            "actual_prev3": f"प्रत्यक्ष जमा {self.prev3.get('short', '')}",
            "actual_prev2": f"प्रत्यक्ष जमा {self.prev2.get('short', '')}",
            "actual_prev1": f"प्रत्यक्ष जमा {self.prev1.get('short', '')}",
            "budget_estimate_curr": f"अर्थसंकल्पीय जमा अंदाज ({c})",
            "revised_estimate_curr": f"सुधारीत जमा अंदाज ({c})",
            "budget_estimate_next": f"अर्थसंकल्पीय जमा अंदाजपत्रक ({n})",
        }

    # ------------------------------------------------------------------
    # inline edit labels — section1 quick-edit form
    # ------------------------------------------------------------------
    @property
    def inline_edit_labels(self) -> Dict[str, str]:
        """Labels for the section1 inline quick-edit form fields."""
        c = self.curr.get("short", "")
        n = self.next1.get("short", "")
        return {
            "actual_prev3": self.prev3.get("short", ""),
            "actual_prev2": self.prev2.get("short", ""),
            "actual_prev1": self.prev1.get("short", ""),
            "budget_estimate_curr": f"अर्थसंकल्पीय जमा अंदाज ({c})",
            "revised_estimate_curr": f"सुधारीत जमा अंदाज ({c})",
            "budget_estimate_next": f"अर्थसंकल्पीय जमा अंदाजपत्रक ({n})",
        }
