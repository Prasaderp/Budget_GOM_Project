"""Taluka data-scoping and consolidation package.

Public surface is re-exported here so callers do not need to know the
internal module layout (`scope`, `models`, `constants`, ...).
"""
from src.core.taluka.constants import (
    DISTRICT_LEVEL,
    DISTRICT_OFFICE,
    RESERVED_TALUKA_VALUES,
    DISTRICT_OFFICE_LABEL_MR,
)
from src.core.taluka.models import TalukaScopedMixin, iter_scoped_models, natural_key_columns
from src.core.taluka.scope import (
    DataScope,
    CONSOLIDATED_SCOPE,
    resolve_scope_from_request,
    current_scope,
    scope_override,
)

__all__ = [
    "DISTRICT_LEVEL",
    "DISTRICT_OFFICE",
    "RESERVED_TALUKA_VALUES",
    "DISTRICT_OFFICE_LABEL_MR",
    "TalukaScopedMixin",
    "iter_scoped_models",
    "natural_key_columns",
    "DataScope",
    "CONSOLIDATED_SCOPE",
    "resolve_scope_from_request",
    "current_scope",
    "scope_override",
]
