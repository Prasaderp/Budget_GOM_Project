"""Full database reset: drop everything, rebuild from migrations, seed only credentials.

What it does, in order:
  1. Drops and recreates schema `public` on the database `.env` currently points at.
  2. Imports `src.main`, whose bootstrap is the single source of truth for
     schema creation -- `Base.metadata.create_all()`, then the migration
     runner (core -> shared -> schemes, including the taluka dimension and
     every DATAINSERTION seed, all of which seed zeros), then the
     district-office twin backfill and the default fiscal year.
  3. Zeroes every numeric value column across all 78 scheme data tables.
     This step is NOT redundant with step 2: several DATAINSERTION files
     (the s2053/s2029/s2045 four-table families, s6245, s6401) seed real
     values -- sanctioned posts, basic pay, allowances, expenditures -- not
     zeros. The row skeleton from those files is what we want; the values
     are not. Reference data (pay_matrix), fiscal-year config, and the
     credential tables are untouched. Pass --no-zero to keep seeded values.
  4. Seeds the user/admin credentials with `force=True`, which is what the
     production startup path deliberately skips.
  5. Verifies the taluka invariant on the rebuilt database.

Guarded on purpose: it refuses to run unless `--db <name>` matches the database
name in DATABASE_URL, so a stale `.env` cannot wipe the wrong server.

    python scripts/reset_database.py --db Budget_GOM --yes
"""
import argparse
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Scheme data tables are exactly those whose name ends in the scheme or
# sub-scheme code (district_expenditure_2245, budget_post_details_20530019,
# sub_head_expenditure_2075, district_revenue_0029). Infrastructure tables
# (users, pay_matrix, fiscal_years, schema_migrations, ...) never match, so
# the zeroing pass structurally cannot touch credentials or reference data.
SCHEME_TABLE_RE = re.compile(r'_\d{4,8}$')

# `id` is the surrogate key, not a value.
NON_VALUE_COLUMNS = {'id'}

NUMERIC_TYPES = ('integer', 'bigint', 'numeric', 'double precision', 'real', 'smallint')


def zero_all_values(conn) -> tuple[int, int]:
    """Set every numeric value column in every scheme data table to 0.

    Returns (tables_touched, columns_zeroed).
    """
    from sqlalchemy import text

    tables = [
        r[0] for r in conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        ))
        if SCHEME_TABLE_RE.search(r[0])
    ]

    tables_touched = 0
    columns_zeroed = 0
    for tbl in tables:
        cols = [
            r[0] for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t "
                "AND data_type = ANY(:types) ORDER BY ordinal_position"
            ), {'t': tbl, 'types': list(NUMERIC_TYPES)})
            if r[0] not in NON_VALUE_COLUMNS
        ]
        if not cols:
            continue
        assignments = ', '.join(f'"{c}" = 0' for c in cols)
        conn.execute(text(f'UPDATE "{tbl}" SET {assignments}'))
        tables_touched += 1
        columns_zeroed += len(cols)

    return tables_touched, columns_zeroed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='database name, must match DATABASE_URL')
    parser.add_argument('--yes', action='store_true', help='confirm the destructive drop')
    parser.add_argument('--no-zero', action='store_true',
                        help='keep the values the DATAINSERTION files seed instead of zeroing them')
    args = parser.parse_args()

    from src.database import engine
    from sqlalchemy import text

    url = urlparse(engine.url.render_as_string(hide_password=True))
    db_name = (url.path or '/').lstrip('/')
    print(f"target: host={url.hostname} db={db_name} user={engine.url.username}")

    if db_name != args.db:
        print(f"ABORT: --db {args.db!r} does not match DATABASE_URL database {db_name!r}", file=sys.stderr)
        return 2
    if not args.yes:
        print("ABORT: pass --yes to confirm dropping every table in this database", file=sys.stderr)
        return 2

    with engine.begin() as conn:
        conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
        conn.execute(text('CREATE SCHEMA public AUTHORIZATION CURRENT_USER'))
    engine.dispose()
    print("schema dropped and recreated")

    os.environ['RUN_DB_CREATE_ALL'] = 'true'
    import src.main  # noqa: F401  -- bootstrap: create_all + migrations + twin backfill + fiscal year
    print("schema rebuilt and migrations applied")

    if args.no_zero:
        print("zeroing skipped (--no-zero): tables keep the values their DATAINSERTION files seed")
    else:
        from src.database import engine as live_engine
        with live_engine.begin() as conn:
            n_tables, n_cols = zero_all_values(conn)
        print(f"values zeroed: {n_cols} numeric column(s) across {n_tables} scheme table(s)")

    from src.database import SessionLocal
    from src.routers.auth import seed_users
    db = SessionLocal()
    try:
        seed_users(db, force=True)
        from src import models
        print(f"users seeded: {db.query(models.User).count()} users, "
              f"{db.query(models.AdminUser).count()} admin")
    finally:
        db.close()

    # `run`, not `main` -- main() re-parses sys.argv, which here still holds
    # this script's own --db/--yes flags.
    from scripts.check_taluka_invariant import run as check_invariant
    return check_invariant()


if __name__ == '__main__':
    sys.exit(main())
