"""
Fiscal year label generator for scheme 2215 — Water Scarcity.

Converts a relative_years dict (from get_relative_fiscal_years) into
dynamic column header labels used in the index and totals views.

The s2215 expenditure table has 6 year columns:
  - 3 actual expenditure columns   (prev3, prev2, prev1)
  - Budget estimate (curr)
  - Revised demand  (curr, tagged "सुधारीत")
  - Budget estimate next (next1)

Usage:
    from src.utils_fiscal_year import get_relative_fiscal_years
    ry = get_relative_fiscal_years("2025-26")
    labels = FiscalYearLabels2215(ry)
    labels.expenditure_headers   # ordered header list for table <th>
    labels.form_labels           # dict mapping form-field ids to display labels
"""
from __future__ import annotations

from typing import Dict, List


class FiscalYearLabels2215:
    """Immutable, zero-allocation label resolver for s2215 expenditure views."""

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
    # table column headers  (ordered list matching the 6 <th> slots)
    # ------------------------------------------------------------------
    @property
    def expenditure_headers(self) -> List[str]:
        """Column headers for the expenditure table in display order."""
        return [
            self.prev3.get("short", ""),   # actual expenditure col 1
            self.prev2.get("short", ""),   # actual expenditure col 2
            self.prev1.get("short", ""),   # actual expenditure col 3
            self.curr.get("short", ""),    # budget estimate
            self.curr.get("short", ""),    # revised demand (same FY)
            self.next1.get("short", ""),   # budget estimate next year
        ]

    # ------------------------------------------------------------------
    # quick-edit form labels
    # ------------------------------------------------------------------
    @property
    def form_labels(self) -> Dict[str, str]:
        """Map of logical field names → Marathi display labels with year."""
        c = self.curr.get("short", "")
        n = self.next1.get("short", "")
        return {
            "expenditure_prev3": self.prev3.get("short", ""),
            "expenditure_prev2": self.prev2.get("short", ""),
            "expenditure_prev1": self.prev1.get("short", ""),
            "budget_estimate":   f"अर्थसंकल्पीय अंदाजपत्रक ({c})",
            "revised_demand":    f"सुधारीत अंदाजपत्रक मागणी ({c})",
            "budget_next":       f"अर्थसंकल्पीय अंदाजपत्रक ({n})",
        }
