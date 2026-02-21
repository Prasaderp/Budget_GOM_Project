"""
Fiscal year label generator for scheme 2245 — Natural Calamity Relief.

Converts a relative_years dict (from get_relative_fiscal_years) into
dynamic column header labels used in section1, section2, and section3
views.

The s2245 expenditure table has 6 year columns:
  - 3 actual expenditure columns   (prev3, prev2, prev1)
  - Budget estimate (curr)
  - Revised estimate (curr, tagged "सुधारीत")
  - Budget estimate next (next1)

Usage:
    from src.utils_fiscal_year import get_relative_fiscal_years
    ry = get_relative_fiscal_years("2025-26")
    labels = FiscalYearLabels2245(ry)
    labels.list_headers    # ordered header dict for table <th>
    labels.form_labels     # dict mapping form-field ids to display labels
    labels.modal_labels    # dict for section3 edit modal labels
"""
from __future__ import annotations

from typing import Dict


class FiscalYearLabels2245:
    """Immutable, zero-allocation label resolver for s2245 expenditure views."""

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
    # table column headers — section1_list, section2_list, section3_list
    # ------------------------------------------------------------------
    @property
    def list_headers(self) -> Dict[str, str]:
        """Column headers for all section tables."""
        n = self.next1.get("short", "")
        return {
            "exp_prev3": self.prev3.get("short", ""),
            "exp_prev2": self.prev2.get("short", ""),
            "exp_prev1": self.prev1.get("short", ""),
            "budget_estimate_curr": "अर्थसंकल्पीय अंदाजपत्रक",
            "revised_estimate_curr": "सुधारीत अंदाजपत्रक",
            "budget_estimate_next": f"अर्थसंकल्पीय अंदाजपत्रक ({n})",
        }

    # ------------------------------------------------------------------
    # form labels — section1 edit form
    # ------------------------------------------------------------------
    @property
    def form_labels(self) -> Dict[str, str]:
        """Map of logical field names → Marathi display labels with year."""
        n = self.next1.get("short", "")
        return {
            "exp_prev3": f"प्रत्यक्ष खर्च {self.prev3.get('short', '')}",
            "exp_prev2": f"प्रत्यक्ष खर्च {self.prev2.get('short', '')}",
            "exp_prev1": f"प्रत्यक्ष खर्च {self.prev1.get('short', '')}",
            "budget_estimate_curr": "अर्थसंकल्पीय अंदाजपत्रक",
            "revised_estimate_curr": "सुधारीत अंदाजपत्रक",
            "budget_estimate_next": f"अर्थसंकल्पीय अंदाजपत्रक ({n})",
        }

    # ------------------------------------------------------------------
    # modal labels — section3 inline-edit modal
    # ------------------------------------------------------------------
    @property
    def modal_labels(self) -> Dict[str, str]:
        """Labels for the section3 edit modal fields."""
        n = self.next1.get("short", "")
        return {
            "exp_prev3": f"प्रत्यक्ष रक्कमा (खर्च) - {self.prev3.get('short', '')}",
            "exp_prev2": f"प्रत्यक्ष रक्कमा (खर्च) - {self.prev2.get('short', '')}",
            "exp_prev1": f"प्रत्यक्ष रक्कमा (खर्च) - {self.prev1.get('short', '')}",
            "budget_estimate_curr": "अर्थसंकल्पीय अंदाजपत्रक",
            "revised_estimate_curr": "सुधारीत अंदाजपत्रक",
            "budget_estimate_next": f"अर्थसंकल्पीय अंदाजपत्रक ({n})",
        }
