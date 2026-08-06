"""Contribution-row provisioning on taluka activation and fiscal-year seeding
(docs/plan.md Phase 7).

Both functions clone from the consolidated (taluka='') row set, which the
Phase 3 migration guarantees exists for every natural key, via one
INSERT ... SELECT per table -- activating a 16-taluka district across ~78
tables must never become a per-row round trip. `ON CONFLICT DO NOTHING`
against the natural-key UNIQUE constraint (which includes `taluka`) makes
every call idempotent: re-activating an already-active taluka, or re-running
a lazy top-up, inserts nothing extra.
"""
import logging
from typing import Dict, List

from sqlalchemy import inspect, text
from sqlalchemy.types import BigInteger, Float, Integer, Numeric

from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE
from src.core.taluka.models import iter_scoped_models

logger = logging.getLogger(__name__)


def _clone_sql(model, target_taluka: str):
    """INSERT ... SELECT cloning `model`'s consolidated rows for one district
    and fiscal year into `target_taluka`'s contribution rows, numerics
    zeroed. Column plan mirrors clone_table_for_fiscal_year()
    (src/routers/fiscal_year.py) with `taluka` overridden instead of
    `fiscal_year`.
    """
    table = model.__tablename__
    clone_cols, zero_cols = [], []
    for col in inspect(model).columns:
        if col.name in ('id', 'taluka'):
            continue
        (zero_cols if isinstance(col.type, (Integer, BigInteger, Float, Numeric)) else clone_cols).append(col.name)

    select_parts = [f'"{c}"' for c in clone_cols] + [f"'{target_taluka}' AS taluka"] + [f'0 AS "{c}"' for c in zero_cols]
    insert_cols = ', '.join(f'"{c}"' for c in clone_cols + ['taluka'] + zero_cols)
    return text(f'''
        INSERT INTO {table} ({insert_cols})
        SELECT {', '.join(select_parts)}
        FROM {table}
        WHERE taluka = :src_taluka AND district = :district AND fiscal_year = :fiscal_year
        ON CONFLICT DO NOTHING
    ''')


def _clone_into(db, model, district: str, fiscal_year: str, target_taluka: str) -> int:
    result = db.execute(
        _clone_sql(model, target_taluka),
        {'src_taluka': DISTRICT_LEVEL, 'district': district, 'fiscal_year': fiscal_year},
    )
    return result.rowcount or 0


def provision_taluka_rows(db, district: str, taluka: str, fiscal_year: str) -> Dict[str, int]:
    """Clone contribution rows for a newly activated `taluka`, across every
    scoped table, for `fiscal_year`. Runs inside the caller's activation
    transaction (docs/plan.md section 4.1) -- never commits.
    """
    created: Dict[str, int] = {}
    for model in iter_scoped_models():
        count = _clone_into(db, model, district, fiscal_year, taluka)
        if count:
            created[model.__tablename__] = count
    logger.info(
        "taluka_provisioning district=%s taluka=%s fiscal_year=%s tables=%d rows_created=%d",
        district, taluka, fiscal_year, len(created), sum(created.values()),
    )
    return created


def ensure_contribution_rows(db, model, district: str, fiscal_year: str) -> int:
    """Idempotent top-up for one table: clone consolidated rows into the
    district-office row and every currently active taluka's row, for
    whichever are still missing. Used by fiscal-year seeders right after
    they seed the consolidated row, and by lazy provisioning when a taluka
    opens a form for a natural key it has no contribution row for yet.
    """
    from src.core.taluka.consolidation import _active_taluka_values

    targets: List[str] = [DISTRICT_OFFICE] + _active_taluka_values(db, district)
    return sum(_clone_into(db, model, district, fiscal_year, target) for target in targets)
