"""Reconciliation checker and disaster-recovery tool for the taluka
consolidation invariant (docs/plan.md Phase 13):

    consolidated[taluka=''][numeric_col] == sum(active contributions)[numeric_col]

for every natural key on every district-scoped table. Also reports the two
shapes a mishandled API POST/DELETE produces (docs/plan.md section "Recipe
D"), which a pure value-equality check would miss entirely:

  - orphan:   a contribution row (district-office or taluka) with no
              taluka='' sibling for its natural key.
  - twinless: a taluka='' row with no '__district_office__' sibling for its
              natural key.

This is both the CI gate and the production disaster-recovery tool. Because
consolidate_row() is a full recomputation (never a delta), it is idempotent
and --fix is always safe to re-run. --fix cannot resurrect a genuinely
deleted district-office row (its money is gone); it only re-syncs whatever
is still computable from the rows that remain, so a twinless row may still
be reported after --fix -- that residual report is correct, not a bug.

Usage:
    python scripts/check_taluka_invariant.py
    python scripts/check_taluka_invariant.py --fix
    python scripts/check_taluka_invariant.py --district Thane
    python scripts/check_taluka_invariant.py --table budget_post_details_20530028
"""
import argparse
import logging
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Disaster-recovery / CI usage must never trigger the app's own bootstrap
# side effects (create_all, migrations, user/fiscal-year seeding) as a side
# effect of importing src.main to populate the SQLAlchemy model registry.
os.environ.setdefault("RUN_DB_CREATE_ALL", "false")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.main  # noqa: E402,F401  import side effect: registers every scheme model with Base.registry

from src.core.taluka import (  # noqa: E402
    DISTRICT_LEVEL,
    DISTRICT_OFFICE,
    iter_scoped_models,
    natural_key_columns,
)
from src.core.taluka.consolidation import _active_taluka_values, _column_classes, consolidate_row  # noqa: E402
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION  # noqa: E402
from src.database import SessionLocal  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("check_taluka_invariant")


def _group_by_natural_key(rows, key_cols: tuple) -> Dict[Tuple, list]:
    groups: Dict[Tuple, list] = defaultdict(list)
    for row in rows:
        groups[tuple(getattr(row, c) for c in key_cols)].append(row)
    return groups


def _check_table(db, model, district_filter: Optional[str], fix: bool) -> List[dict]:
    key_cols = natural_key_columns(model)
    query = db.query(model).execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
    if district_filter:
        query = query.filter(model.district == district_filter)
    rows = query.all()
    if not rows:
        return []

    additive_cols = [c for c, cls in _column_classes(model).items() if cls == 'additive']
    violations: List[dict] = []
    to_fix: List[Tuple[str, str, dict]] = []

    for key, members in _group_by_natural_key(rows, key_cols).items():
        natural_key = dict(zip(key_cols, key))
        district, fiscal_year = natural_key.get('district'), natural_key.get('fiscal_year')
        by_taluka = {r.taluka: r for r in members}
        consolidated, office = by_taluka.get(DISTRICT_LEVEL), by_taluka.get(DISTRICT_OFFICE)
        contribution_rows = [r for r in members if r.taluka != DISTRICT_LEVEL]
        needs_fix = False

        if consolidated is not None and office is None:
            violations.append({'type': 'twinless', 'table': model.__tablename__, 'natural_key': natural_key})
        if contribution_rows and consolidated is None:
            violations.append({
                'type': 'orphan', 'table': model.__tablename__, 'natural_key': natural_key,
                'orphan_talukas': [r.taluka for r in contribution_rows],
            })
            needs_fix = True
        if consolidated is not None and district and fiscal_year:
            active = set(_active_taluka_values(db, district))
            expected_contributors = [r for r in contribution_rows if r.taluka == DISTRICT_OFFICE or r.taluka in active]
            for col in additive_cols:
                expected = sum(getattr(r, col) or 0 for r in expected_contributors)
                actual = getattr(consolidated, col) or 0
                if expected != actual:
                    violations.append({
                        'type': 'mismatch', 'table': model.__tablename__, 'natural_key': natural_key,
                        'column': col, 'expected': expected, 'actual': actual,
                    })
                    needs_fix = True

        if fix and needs_fix and district and fiscal_year:
            to_fix.append((district, fiscal_year, natural_key))

    for district, fiscal_year, natural_key in to_fix:
        consolidate_row(db, model, district, fiscal_year, natural_key)

    return violations


def run(district: Optional[str] = None, table: Optional[str] = None, fix: bool = False) -> int:
    db = SessionLocal()
    total_violations = 0
    try:
        target_models = sorted(
            (m for m in iter_scoped_models() if not table or m.__tablename__ == table),
            key=lambda m: m.__tablename__,
        )
        for model in target_models:
            violations = _check_table(db, model, district_filter=district, fix=fix)
            for v in violations:
                extra = {k: val for k, val in v.items() if k not in ('type', 'table', 'natural_key')}
                logger.warning("VIOLATION type=%s table=%s natural_key=%s %s", v['type'], v['table'], v['natural_key'], extra)
            total_violations += len(violations)
        db.commit() if fix else db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if total_violations == 0:
        logger.info("OK: 0 violations across %d table(s)", len(target_models))
    else:
        logger.error("FAIL: %d violation(s) across %d table(s)%s", total_violations, len(target_models), " (fix applied)" if fix else "")
    return 0 if total_violations == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fix', action='store_true', help="Recompute every mismatched/orphan natural key found")
    parser.add_argument('--district', default=None, help="Limit the check to one district")
    parser.add_argument('--table', default=None, help="Limit the check to one table name")
    args = parser.parse_args()
    sys.exit(run(district=args.district, table=args.table, fix=args.fix))


if __name__ == '__main__':
    main()
