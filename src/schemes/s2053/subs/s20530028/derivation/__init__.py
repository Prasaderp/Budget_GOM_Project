"""Cross-form derivation primitives for sub-scheme 20530028."""
"""Form D propagation API and model-hook registration."""

from src.core.derivation.registry import register

from ..models import BudgetPostDetails
from .service import acquire_derivation_locks, derive_for_row, derive_from_form_d

register(BudgetPostDetails, derive_for_row)

__all__ = (
    "acquire_derivation_locks",
    "derive_for_row",
    "derive_from_form_d",
)
