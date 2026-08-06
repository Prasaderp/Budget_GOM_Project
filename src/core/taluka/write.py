"""Write redirection (Recipe R) and the natural-key lifecycle recipe
(Recipe D) -- docs/plan.md Phase 6 / section 6.

Read paths are never touched here; Phase 2's ORM filter already makes them
correct. Every mutating handler resolves its target row through this module
so a write never depends on the read filter that produced the id in the URL.
"""
import logging
from typing import Any, Dict, Type

from fastapi import HTTPException, Request
from sqlalchemy import event, inspect
from sqlalchemy.types import BigInteger, Float, Integer, Numeric

from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE, TOTAL_SPACE_FLAG
from src.core.taluka.consolidation import active_taluka_sums, consolidate_row
from src.core.taluka.models import natural_key_columns
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION
from src.database import SessionLocal
from src.utils_auth import get_auth_level, get_auth_unit
from src.utils_district import get_district_from_taluka, validate_access_control
from src.utils_taluka import is_taluka_allowed

logger = logging.getLogger(__name__)

_SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})
_LIFTED_ROWS = 'taluka_lifted_rows'


def _writable_taluka_value(db, district: str, level: str, unit: str) -> str:
    """The taluka value this caller may write for `district`. Never taken
    from the request body (section 5.1) -- always derived from the cookie.
    """
    if level == 'taluka' and unit:
        if get_district_from_taluka(unit) != district:
            raise HTTPException(status_code=403, detail="Access denied")
        if not is_taluka_allowed(db, unit):
            raise HTTPException(status_code=403, detail="Taluka is not active")
        return unit
    if level == 'district' and unit:
        return DISTRICT_OFFICE
    raise HTTPException(status_code=403, detail="Access denied")


def resolve_editable_row(db, model: Type, row_id: int, request: Request):
    """Recipe R. Step 1 deliberately bypasses the read filter (raw id,
    taluka_scope_all=True) -- the district ACL and the dispatch below are the
    only authorisation on this path, not defence in depth on top of a read
    filter that a district-assistant-originated id would fail anyway.

    A taluka caller always resolves to its own contribution row: it reads and
    writes exactly what it owns. A district caller works in *total* space --
    it reads the consolidated row (the figure its list page shows, taluka
    contributions included) and its writes land on the office contribution
    row lifted into that same space, which `consolidate_row()` rebases back
    down. Without this, a district assistant would be shown a form
    pre-filled with the office share of a total it had just seen on the list
    and every save would silently re-add the talukas' figures.
    """
    row = (
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(model.id == row_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")

    level, unit = get_auth_level(request), get_auth_unit(request)
    allowed, error = validate_access_control(row.district, level, unit, db)
    if not allowed:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    writable_value = _writable_taluka_value(db, row.district, level, unit)

    if writable_value != DISTRICT_OFFICE:
        if row.taluka == writable_value:
            return row
        if row.taluka == DISTRICT_LEVEL:
            return ensure_contribution_row(db, model, row, writable_value)
        raise HTTPException(status_code=403, detail="Access denied")

    if row.taluka not in (DISTRICT_LEVEL, DISTRICT_OFFICE):
        raise HTTPException(status_code=403, detail="Access denied")

    if request.method in _SAFE_METHODS:
        return row if row.taluka == DISTRICT_LEVEL else (_sibling(db, model, row, DISTRICT_LEVEL) or row)

    contribution = row if row.taluka == DISTRICT_OFFICE else ensure_contribution_row(db, model, row, DISTRICT_OFFICE)
    return _lift_to_total_space(db, model, contribution)


def _sibling(db, model: Type, row, taluka_value: str):
    key_cols = natural_key_columns(model)
    return (
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(model.taluka == taluka_value, *[getattr(model, c) == getattr(row, c) for c in key_cols])
        .first()
    )


def _lift_to_total_space(db, model: Type, contribution):
    """Present the office row to the handler in district-total space, and
    register it so the total is rebased to a share before the transaction
    ends -- by `consolidate_row()` on the normal path, by the commit-time
    backstop below on any path that forgets to call it.
    """
    if getattr(contribution, TOTAL_SPACE_FLAG, False):
        return contribution
    for name, reported in active_taluka_sums(db, model, contribution).items():
        setattr(contribution, name, (getattr(contribution, name) or 0) + reported)
    setattr(contribution, TOTAL_SPACE_FLAG, True)
    db.info.setdefault(_LIFTED_ROWS, []).append((model, contribution))
    return contribution


@event.listens_for(SessionLocal, "before_commit")
def _rebase_lifted_rows_before_commit(session):
    for model, row in session.info.pop(_LIFTED_ROWS, ()):
        if getattr(row, TOTAL_SPACE_FLAG, False) and row in session:
            session.flush()
            key_cols = natural_key_columns(model)
            consolidate_row(session, model, row.district, getattr(row, 'fiscal_year', None),
                            {c: getattr(row, c) for c in key_cols})


@event.listens_for(SessionLocal, "after_soft_rollback")
def _discard_lifted_rows(session, previous_transaction):
    session.info.pop(_LIFTED_ROWS, None)


def ensure_contribution_row(db, model: Type, consolidated_row, taluka_value: str):
    """Lazily create the sibling contribution row for `taluka_value`, sharing
    `consolidated_row`'s natural key with zeroed numerics. Idempotent -- an
    existence check plus the natural-key UNIQUE constraint as the backstop.
    """
    key_cols = natural_key_columns(model)
    natural_key = {c: getattr(consolidated_row, c) for c in key_cols}

    existing = _sibling(db, model, consolidated_row, taluka_value)
    if existing is not None:
        return existing

    values: Dict[str, Any] = {}
    for col in inspect(model).columns:
        if col.name in ('id', 'taluka') or col.name in key_cols:
            continue
        values[col.name] = 0 if isinstance(col.type, (Integer, BigInteger, Float, Numeric)) else getattr(consolidated_row, col.name)

    row = model(taluka=taluka_value, **natural_key, **values)
    db.add(row)
    db.flush()
    return row


def create_row_family(db, model: Type, values: Dict[str, Any], request: Request):
    """Recipe D create: stamps the district-office contribution row, then
    lets consolidate_row() materialise its consolidated twin so the family
    is never born with a consolidated row and no contribution behind it.
    """
    level, unit = get_auth_level(request), get_auth_unit(request)
    if level == 'taluka':
        raise HTTPException(status_code=403, detail="Taluka users cannot create records")

    district = values.get('district')
    if not district:
        raise HTTPException(status_code=400, detail="district is required")

    allowed, error = validate_access_control(district, level, unit, db)
    if not allowed:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    payload = {k: v for k, v in values.items() if k not in ('id', 'taluka')}
    contribution = model(taluka=DISTRICT_OFFICE, **payload)
    db.add(contribution)
    db.flush()

    key_cols = natural_key_columns(model)
    natural_key = {c: getattr(contribution, c) for c in key_cols}
    return consolidate_row(db, model, district, natural_key.get('fiscal_year'), natural_key)


def delete_row_family(db, model: Type, row_id: int, request: Request) -> int:
    """Recipe D delete: resolves the natural key from `row_id` (consolidated
    or contribution id, either works) and deletes the consolidated row and
    every contribution row for that key together, leaving no orphan.
    """
    level, unit = get_auth_level(request), get_auth_unit(request)
    if level == 'taluka':
        raise HTTPException(status_code=403, detail="Taluka users cannot delete records")

    row = (
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(model.id == row_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")

    allowed, error = validate_access_control(row.district, level, unit, db)
    if not allowed:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    key_cols = natural_key_columns(model)
    natural_key = {c: getattr(row, c) for c in key_cols}
    family = (
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(*[getattr(model, c) == v for c, v in natural_key.items()])
        .all()
    )
    for r in family:
        db.delete(r)
    db.flush()
    return len(family)
