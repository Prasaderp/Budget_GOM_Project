"""
Fiscal year label generator for scheme 7610 — Government Advances.

Converts a relative_years dict (from get_relative_fiscal_years) into
dynamic column header labels used in district expenditure list and
form views across all 4 sub-schemes:
  76100149, 76100158, 76100167, 76101871.

The s7610 expenditure table has 6 year columns:
  - 3 actual expenditure columns   (prev3, prev2, prev1)
  - Budget estimate (curr)
  - Revised estimate (curr, tagged "सुधारित")
  - Budget estimate next (next1)

Usage:
    from src.utils_fiscal_year import get_relative_fiscal_years
    ry = get_relative_fiscal_years("2025-26")
    labels = FiscalYearLabels7610(ry)
    labels.list_headers    # ordered header dict for table <th>
    labels.form_labels     # dict mapping form-field ids to display labels
"""
from __future__ import annotations

from typing import Dict


class FiscalYearLabels7610:
    """Immutable, zero-allocation label resolver for s7610 district expenditure views."""

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
    # table column headers — district_expenditure_list view
    # ------------------------------------------------------------------
    @property
    def list_headers(self) -> Dict[str, str]:
        """Column headers for the district expenditure list table."""
        c = self.curr.get("short", "")
        n = self.next1.get("short", "")
        return {
            "exp_prev3": self.prev3.get("short", ""),
            "exp_prev2": self.prev2.get("short", ""),
            "exp_prev1": self.prev1.get("short", ""),
            "budget_estimate_curr": f"अर्थसंकल्पीय अंदाज {c}",
            "revised_estimate_curr": f"सुधारित अंदाज {c}",
            "budget_estimate_next": f"अर्थसंकल्पीय अंदाज {n}",
        }

    # ------------------------------------------------------------------
    # form labels — district_expenditure_form view
    # ------------------------------------------------------------------
    @property
    def form_labels(self) -> Dict[str, str]:
        """Map of logical field names → Marathi display labels with year."""
        c = self.curr.get("short", "")
        n = self.next1.get("short", "")
        return {
            "exp_prev3": f"प्रत्यक्ष खर्च {self.prev3.get('short', '')}",
            "exp_prev2": f"प्रत्यक्ष खर्च {self.prev2.get('short', '')}",
            "exp_prev1": f"प्रत्यक्ष खर्च {self.prev1.get('short', '')}",
            "budget_estimate_curr": f"अर्थसंकल्पीय अंदाज {c}",
            "revised_estimate_curr": f"सुधारित अंदाज {c}",
            "budget_estimate_next": f"अर्थसंकल्पीय अंदाज {n}",
        }
