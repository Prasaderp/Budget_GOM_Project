"""Roll-up recomputation (docs/plan.md Phase 6, sections 4.2 and 4.4).

consolidate_row() recomputes one natural-key row group -- the district-office
contribution plus every currently active taluka's contribution -- into the
consolidated (taluka='') row, upserting it if absent. Full recomputation,
never delta: idempotent, self-healing after any crash, immune to
double-application. Runs inside the caller's existing transaction; never
commits or rolls back.
"""
import logging
from typing import Any, Dict, List, Type

from sqlalchemy import inspect
from sqlalchemy.types import BigInteger, Float, Integer, Numeric

from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE
from src.core.taluka.models import natural_key_columns
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION

logger = logging.getLogger(__name__)

# Columns that identify a row rather than measure it. Copied, never summed
# or concatenated -- summing hra_rate ('X'/'Y'/'Z') or remarks would violate
# the table's own CHECK constraint or silently corrupt free text.
_IDENTITY_EXTRA_COLUMNS = frozenset({'id', 'scheme_code', 'sub_scheme_code'})


def _column_classes(model: Type) -> Dict[str, str]:
    key_cols = set(natural_key_columns(model))
    classes: Dict[str, str] = {}
    for col in inspect(model).columns:
        if col.name in ('id', 'taluka'):
            continue
        if col.name in key_cols or col.name in _IDENTITY_EXTRA_COLUMNS:
            classes[col.name] = 'identity'
        elif isinstance(col.type, (Integer, BigInteger, Float, Numeric)):
            classes[col.name] = 'additive'
        else:
            classes[col.name] = 'text'
    return classes


def _active_taluka_values(db, district: str) -> List[str]:
    """Talukas both currently selected by the district and flagged active in
    TalukaUserManagement -- a taluka deselected mid-session but not yet
    synced, or vice versa, must never be double-counted or dropped silently.
    """
    from src import models
    from src.utils_taluka import get_selected_talukas

    selected = set(get_selected_talukas(db, district))
    if not selected:
        return []
    active = {
        row.taluka_name
        for row in db.query(models.TalukaUserManagement)
        .filter(
            models.TalukaUserManagement.district == district,
            models.TalukaUserManagement.is_active == True,  # noqa: E712
        )
        .all()
    }
    return sorted(selected & active)


def consolidate_row(db, model: Type, district: str, fiscal_year: str, natural_key: Dict[str, Any]):
    """Recompute the consolidated (taluka='') row for one natural key.

    `natural_key` carries every natural-key column's value (district and
    fiscal_year included) except `taluka`.
    """
    key_cols = natural_key_columns(model)
    missing = [c for c in key_cols if c not in natural_key]
    if missing:
        raise ValueError(f"consolidate_row: natural_key missing {missing} for {model.__name__}")

    def _by_key(query):
        for col in key_cols:
            query = query.filter(getattr(model, col) == natural_key[col])
        return query

    consolidated = _by_key(
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(model.taluka == DISTRICT_LEVEL)
    ).with_for_update().first()

    contribution_values = [DISTRICT_OFFICE] + _active_taluka_values(db, district)
    contributions = _by_key(
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(model.taluka.in_(contribution_values))
    ).all()

    district_office_row = next((r for r in contributions if r.taluka == DISTRICT_OFFICE), None)
    values: Dict[str, Any] = dict(natural_key)
    for name, cls in _column_classes(model).items():
        if cls == 'identity':
            continue
        if cls == 'additive':
            values[name] = sum(getattr(r, name) or 0 for r in contributions)
        else:
            values[name] = getattr(district_office_row, name) if district_office_row else None

    if consolidated is None:
        consolidated = model(taluka=DISTRICT_LEVEL, **values)
        db.add(consolidated)
        db.flush()
    else:
        for name, value in values.items():
            setattr(consolidated, name, value)

    logger.debug(
        "taluka_consolidation table=%s district=%s natural_key=%s contributions=%d",
        model.__tablename__, district, natural_key, len(contributions),
    )
    return consolidated


def consolidate_district(db, model: Type, district: str, fiscal_year: str) -> int:
    """Recompute every natural key for `district`/`fiscal_year` that has at
    least one contribution row. Used after taluka activation/deactivation
    (Phase 7) to bring the whole district's rows back in sync in one pass.
    """
    key_cols = natural_key_columns(model)
    rows = (
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(
            model.district == district,
            model.fiscal_year == fiscal_year,
            model.taluka != DISTRICT_LEVEL,
        )
        .all()
    )
    seen = set()
    count = 0
    for row in rows:
        key = tuple(getattr(row, c) for c in key_cols)
        if key in seen:
            continue
        seen.add(key)
        consolidate_row(db, model, district, fiscal_year, {c: getattr(row, c) for c in key_cols})
        count += 1
    return count
