"""Reconcile 20530028 Form D-derived values in Forms B and C.

Dry-run is the default and never persists ORM changes. ``--fix`` recomputes
each contribution space and commits once per district. The operation is a
full recomputation and is idempotent, so interrupted runs are safe to repeat.

Run this after a DA-rate change, a DESIGNATION_PAY_CLASS change, or any direct
SQL/bulk import that bypasses the request hooks. The DA-rate administration
endpoint should invoke the same reconciliation workflow when that integration
is added.
"""

import argparse
from collections import defaultdict
import logging
import os
from pathlib import Path
import sys

os.environ.setdefault("RUN_DB_CREATE_ALL", "false")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.main  # noqa: E402,F401  registers scheme models and derivation hooks

from src.core.taluka.constants import DISTRICT_LEVEL  # noqa: E402
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION  # noqa: E402
from src.database import SessionLocal  # noqa: E402
from src.schemes.s2053.subs.s20530028.config import (  # noqa: E402
    DERIVED_POST_EXPENSES_FIELDS,
    DERIVED_POST_STATUS_FIELDS,
)
from src.schemes.s2053.subs.s20530028.derivation.service import (  # noqa: E402
    derive_from_form_d,
)
from src.schemes.s2053.subs.s20530028.models import (  # noqa: E402
    BudgetPostDetails,
    PostExpenses,
    PostStatus,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reconcile_form_derivation")


def _unscoped(query):
    return query.execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})


def _target_snapshot(db, *, district, fiscal_year, category, taluka):
    values = {}
    expense_rows = (
        _unscoped(db.query(PostExpenses))
        .filter_by(
            district=district,
            fiscal_year=fiscal_year,
            category=category,
            taluka=taluka,
        )
        .all()
    )
    for row in expense_rows:
        target = f"FormB/class-{row.class_type}"
        for field in DERIVED_POST_EXPENSES_FIELDS:
            values[(target, field)] = getattr(row, field)

    status_rows = (
        _unscoped(db.query(PostStatus))
        .filter_by(
            district=district,
            fiscal_year=fiscal_year,
            category=category,
            taluka=taluka,
        )
        .all()
    )
    for row in status_rows:
        target = f"FormC/{row.class_type}/{row.status}"
        for field in DERIVED_POST_STATUS_FIELDS:
            values[(target, field)] = getattr(row, field)
    return values


def _diff(before, after):
    missing = "<missing>"
    return [
        (target, field, before.get((target, field), missing), after.get((target, field), missing))
        for target, field in sorted(set(before) | set(after))
        if before.get((target, field), missing) != after.get((target, field), missing)
    ]


def _source_groups(db, district=None, fiscal_year=None):
    query = _unscoped(
        db.query(
            BudgetPostDetails.district,
            BudgetPostDetails.fiscal_year,
            BudgetPostDetails.category,
            BudgetPostDetails.taluka,
        )
    ).filter(BudgetPostDetails.taluka != DISTRICT_LEVEL)
    if district:
        query = query.filter(BudgetPostDetails.district == district)
    if fiscal_year:
        query = query.filter(BudgetPostDetails.fiscal_year == fiscal_year)
    return [
        tuple(row)
        for row in query.distinct().order_by(
            BudgetPostDetails.district,
            BudgetPostDetails.fiscal_year,
            BudgetPostDetails.category,
            BudgetPostDetails.taluka,
        )
    ]


def _reconcile_group(db, group, *, fix):
    district, fiscal_year, category, taluka = group
    before = _target_snapshot(
        db,
        district=district,
        fiscal_year=fiscal_year,
        category=category,
        taluka=taluka,
    )
    savepoint = None if fix else db.begin_nested()
    try:
        result = derive_from_form_d(
            db,
            district=district,
            fiscal_year=fiscal_year,
            category=category,
            taluka=taluka,
        )
        db.flush()
        after = _target_snapshot(
            db,
            district=district,
            fiscal_year=fiscal_year,
            category=category,
            taluka=taluka,
        )
        return _diff(before, after), result
    finally:
        if savepoint is not None and savepoint.is_active:
            savepoint.rollback()


def run(*, district=None, fiscal_year=None, fix=False):
    db = SessionLocal()
    change_count = 0
    try:
        grouped = defaultdict(list)
        for group in _source_groups(db, district=district, fiscal_year=fiscal_year):
            grouped[group[0]].append(group)

        if not grouped:
            logger.info("OK: no Form D contribution spaces matched the filters")
            db.rollback()
            return 0

        for district_name, groups in sorted(grouped.items()):
            try:
                for group in groups:
                    changes, result = _reconcile_group(db, group, fix=fix)
                    _, year, category, taluka = group
                    for target, field, before, after in changes:
                        logger.warning(
                            "CHANGE district=%s taluka=%s fiscal_year=%s category=%s "
                            "target=%s field=%s before=%s after=%s",
                            district_name,
                            taluka,
                            year,
                            category,
                            target,
                            field,
                            before,
                            after,
                        )
                    change_count += len(changes)
                    logger.info(
                        "CHECKED district=%s taluka=%s fiscal_year=%s category=%s "
                        "rows_written=%s fields_changed=%s clamps=%s",
                        district_name,
                        taluka,
                        year,
                        category,
                        result.rows_written,
                        result.fields_changed,
                        result.clamps,
                    )
                db.commit() if fix else db.rollback()
            except Exception:
                db.rollback()
                logger.exception("FAILED district=%s", district_name)
                raise
    finally:
        db.close()

    mode = "fixed" if fix else "detected"
    logger.info("DONE: %s %d derived field change(s)", mode, change_count)
    return 1 if change_count and not fix else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report changes without saving (default)")
    mode.add_argument("--fix", action="store_true", help="Persist reconciled derived values")
    parser.add_argument("--district", help="Limit reconciliation to one district")
    parser.add_argument("--fiscal-year", help="Limit reconciliation to one fiscal year")
    args = parser.parse_args()
    raise SystemExit(
        run(district=args.district, fiscal_year=args.fiscal_year, fix=args.fix)
    )


if __name__ == "__main__":
    main()
