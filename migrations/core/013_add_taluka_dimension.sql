-- Migration: Add the `taluka` row-role dimension to every district-scoped table
-- Description: docs/plan.md section 2.2 — one new column defines a row's role:
--   ''                    consolidated district row (derived, never hand-edited)
--   '__district_office__' district office's own contribution
--   '<District> Taluka X'  that taluka's contribution
-- Version: 013
-- Created: 2026-08-06
--
-- NOTE ON TABLE COUNT: docs/plan.md section 3.1 states "78 tables" in its
-- summary arithmetic, but its own per-family breakdown (60 four-table-family
-- + 4 s2235 + 4 s7610 + 3 s2045-lightweight + 2 s6245/s6401 + 2 s2215/s2245
-- + 2 s0029/s2075) sums to 77, and that is what this migration's literal
-- table lists were built from — each name verified against the actual
-- __tablename__ in its model file (src/schemes/**/models.py) before being
-- written here. Autonomous correction per the plan's own directive in
-- section 3.2: "write the table list literally, do not derive it from
-- information_schema alone" — the same discipline applies to trusting a
-- summary count over the verified enumeration.
--
-- EXPLICITLY EXCLUDED: sub_head_expenditure_2075 (src/schemes/s2075/models.py)
-- has no `district` column — it is division-level, not district-level.
-- Adding taluka scoping here would filter every row out of every query.
--
-- ORDERING IS LOAD-BEARING, NOT STYLISTIC:
--   Block 1 (add column) must precede Block 2 (widen the unique constraint),
--   which must precede Block 3 (backfill twin rows). The twin row inserted
--   in Block 3 carries identical natural-key values to its source row
--   (only `taluka` differs) — against the pre-migration constraint, that
--   INSERT is a guaranteed duplicate-key violation. Widening the key first
--   (Block 2) is what makes the backfill legal.
--
-- IDEMPOTENT: every statement is IF NOT EXISTS / DROP...IF EXISTS / guarded
-- by an explicit NOT EXISTS check. A full re-run of this file is a no-op.
--
-- ROLLBACK (manual — not automated by this runner):
--   -- For each table <t> in the ARRAYs below:
--   -- DELETE FROM <t> WHERE taluka <> '';
--   -- ALTER TABLE <t> DROP CONSTRAINT <uq_name recovered from pg_constraint>;
--   -- ALTER TABLE <t> ADD CONSTRAINT <uq_name> UNIQUE (<original cols, without taluka>);
--   -- ALTER TABLE <t> DROP COLUMN taluka;
--   -- DROP VIEW IF EXISTS v_<t>_district;
--   -- (index drops are implied by DROP COLUMN taluka, which drops idx_<t>_scope with it)

-- ============================================================================
-- BLOCK 1: add the `taluka` column (idempotent) to all 77 district-scoped tables
-- ============================================================================
DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        -- 4-table family (60): budget_post_details_*, post_status_*, post_expenses_*, unit_expenditure_*
        'budget_post_details_20530019', 'post_status_20530019', 'post_expenses_20530019', 'unit_expenditure_20530019',
        'budget_post_details_20530028', 'post_status_20530028', 'post_expenses_20530028', 'unit_expenditure_20530028',
        'budget_post_details_20530153', 'post_status_20530153', 'post_expenses_20530153', 'unit_expenditure_20530153',
        'budget_post_details_20530162', 'post_status_20530162', 'post_expenses_20530162', 'unit_expenditure_20530162',
        'budget_post_details_20530233', 'post_status_20530233', 'post_expenses_20530233', 'unit_expenditure_20530233',
        'budget_post_details_20530242', 'post_status_20530242', 'post_expenses_20530242', 'unit_expenditure_20530242',
        'budget_post_details_20530304', 'post_status_20530304', 'post_expenses_20530304', 'unit_expenditure_20530304',
        'budget_post_details_20530313', 'post_status_20530313', 'post_expenses_20530313', 'unit_expenditure_20530313',
        'budget_post_details_20530378', 'post_status_20530378', 'post_expenses_20530378', 'unit_expenditure_20530378',
        'budget_post_details_20530387', 'post_status_20530387', 'post_expenses_20530387', 'unit_expenditure_20530387',
        'budget_post_details_20290037', 'post_status_20290037', 'post_expenses_20290037', 'unit_expenditure_20290037',
        'budget_post_details_20290046', 'post_status_20290046', 'post_expenses_20290046', 'unit_expenditure_20290046',
        'budget_post_details_20290182', 'post_status_20290182', 'post_expenses_20290182', 'unit_expenditure_20290182',
        'budget_post_details_20290262', 'post_status_20290262', 'post_expenses_20290262', 'unit_expenditure_20290262',
        'budget_post_details_20450091', 'post_status_20450091', 'post_expenses_20450091', 'unit_expenditure_20450091',
        -- standalone district-expenditure / district-revenue tables (17)
        'district_expenditure_22350311', 'district_expenditure_22350338',
        'district_expenditure_22353195', 'district_expenditure_22353408',
        'district_expenditure_76100149', 'district_expenditure_76100158',
        'district_expenditure_76100167', 'district_expenditure_76101871',
        'district_expenditure_20450182', 'district_expenditure_20450251', 'district_expenditure_20450262',
        'district_expenditure_62450017', 'district_expenditure_64010018',
        'district_expenditure_2215', 'district_expenditure_2245',
        'district_revenue_0029', 'district_expenditure_2075'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format(
            'ALTER TABLE %I ADD COLUMN IF NOT EXISTS taluka VARCHAR(100) NOT NULL DEFAULT %L',
            tbl, ''
        );
    END LOOP;
END $$;

-- ============================================================================
-- BLOCK 2: widen each table's natural-key UNIQUE constraint to include `taluka`
-- ============================================================================
DO $$
DECLARE
    tbl TEXT;
    cname TEXT;
    coldef TEXT;
    tables TEXT[] := ARRAY[
        'budget_post_details_20530019', 'post_status_20530019', 'post_expenses_20530019', 'unit_expenditure_20530019',
        'budget_post_details_20530028', 'post_status_20530028', 'post_expenses_20530028', 'unit_expenditure_20530028',
        'budget_post_details_20530153', 'post_status_20530153', 'post_expenses_20530153', 'unit_expenditure_20530153',
        'budget_post_details_20530162', 'post_status_20530162', 'post_expenses_20530162', 'unit_expenditure_20530162',
        'budget_post_details_20530233', 'post_status_20530233', 'post_expenses_20530233', 'unit_expenditure_20530233',
        'budget_post_details_20530242', 'post_status_20530242', 'post_expenses_20530242', 'unit_expenditure_20530242',
        'budget_post_details_20530304', 'post_status_20530304', 'post_expenses_20530304', 'unit_expenditure_20530304',
        'budget_post_details_20530313', 'post_status_20530313', 'post_expenses_20530313', 'unit_expenditure_20530313',
        'budget_post_details_20530378', 'post_status_20530378', 'post_expenses_20530378', 'unit_expenditure_20530378',
        'budget_post_details_20530387', 'post_status_20530387', 'post_expenses_20530387', 'unit_expenditure_20530387',
        'budget_post_details_20290037', 'post_status_20290037', 'post_expenses_20290037', 'unit_expenditure_20290037',
        'budget_post_details_20290046', 'post_status_20290046', 'post_expenses_20290046', 'unit_expenditure_20290046',
        'budget_post_details_20290182', 'post_status_20290182', 'post_expenses_20290182', 'unit_expenditure_20290182',
        'budget_post_details_20290262', 'post_status_20290262', 'post_expenses_20290262', 'unit_expenditure_20290262',
        'budget_post_details_20450091', 'post_status_20450091', 'post_expenses_20450091', 'unit_expenditure_20450091',
        'district_expenditure_22350311', 'district_expenditure_22350338',
        'district_expenditure_22353195', 'district_expenditure_22353408',
        'district_expenditure_76100149', 'district_expenditure_76100158',
        'district_expenditure_76100167', 'district_expenditure_76101871',
        'district_expenditure_20450182', 'district_expenditure_20450251', 'district_expenditure_20450262',
        'district_expenditure_62450017', 'district_expenditure_64010018',
        'district_expenditure_2215', 'district_expenditure_2245',
        'district_revenue_0029', 'district_expenditure_2075'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        -- Every family was verified (docs/plan.md section 3.1) to carry
        -- exactly one natural-key UNIQUE constraint. Discovering it from
        -- pg_constraint rather than hardcoding the name keeps this block
        -- correct even if a constraint is ever renamed.
        SELECT con.conname INTO cname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = tbl AND con.contype = 'u';

        IF cname IS NULL THEN
            RAISE EXCEPTION 'taluka migration: no UNIQUE constraint found on table %, refusing to guess', tbl;
        END IF;

        -- Already widened by a prior partial run? Skip — re-adding would
        -- collide with the existing (correctly widened) constraint name.
        IF EXISTS (
            SELECT 1 FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
            WHERE rel.relname = tbl AND con.conname = cname AND att.attname = 'taluka'
        ) THEN
            CONTINUE;
        END IF;

        SELECT string_agg(quote_ident(att.attname), ', ' ORDER BY k.ord)
        INTO coldef
        FROM pg_constraint con
        JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
        JOIN pg_attribute att ON att.attnum = k.attnum AND att.attrelid = con.conrelid
        WHERE con.conname = cname;

        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', tbl, cname);
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I UNIQUE (%s, taluka)', tbl, cname, coldef);
    END LOOP;
END $$;

-- ============================================================================
-- BLOCK 3: backfill district-office contribution rows
--   Every existing row (taluka='') gets a twin with taluka='__district_office__'.
--   Column list is read from information_schema, minus 'id', with 'taluka'
--   overridden. Guarded by NOT EXISTS on the natural key so re-runs are no-ops.
-- ============================================================================
DO $$
DECLARE
    tbl TEXT;
    all_cols TEXT;
    cname TEXT;
    nk_cols TEXT[];
    nk_predicate TEXT;
    tables TEXT[] := ARRAY[
        'budget_post_details_20530019', 'post_status_20530019', 'post_expenses_20530019', 'unit_expenditure_20530019',
        'budget_post_details_20530028', 'post_status_20530028', 'post_expenses_20530028', 'unit_expenditure_20530028',
        'budget_post_details_20530153', 'post_status_20530153', 'post_expenses_20530153', 'unit_expenditure_20530153',
        'budget_post_details_20530162', 'post_status_20530162', 'post_expenses_20530162', 'unit_expenditure_20530162',
        'budget_post_details_20530233', 'post_status_20530233', 'post_expenses_20530233', 'unit_expenditure_20530233',
        'budget_post_details_20530242', 'post_status_20530242', 'post_expenses_20530242', 'unit_expenditure_20530242',
        'budget_post_details_20530304', 'post_status_20530304', 'post_expenses_20530304', 'unit_expenditure_20530304',
        'budget_post_details_20530313', 'post_status_20530313', 'post_expenses_20530313', 'unit_expenditure_20530313',
        'budget_post_details_20530378', 'post_status_20530378', 'post_expenses_20530378', 'unit_expenditure_20530378',
        'budget_post_details_20530387', 'post_status_20530387', 'post_expenses_20530387', 'unit_expenditure_20530387',
        'budget_post_details_20290037', 'post_status_20290037', 'post_expenses_20290037', 'unit_expenditure_20290037',
        'budget_post_details_20290046', 'post_status_20290046', 'post_expenses_20290046', 'unit_expenditure_20290046',
        'budget_post_details_20290182', 'post_status_20290182', 'post_expenses_20290182', 'unit_expenditure_20290182',
        'budget_post_details_20290262', 'post_status_20290262', 'post_expenses_20290262', 'unit_expenditure_20290262',
        'budget_post_details_20450091', 'post_status_20450091', 'post_expenses_20450091', 'unit_expenditure_20450091',
        'district_expenditure_22350311', 'district_expenditure_22350338',
        'district_expenditure_22353195', 'district_expenditure_22353408',
        'district_expenditure_76100149', 'district_expenditure_76100158',
        'district_expenditure_76100167', 'district_expenditure_76101871',
        'district_expenditure_20450182', 'district_expenditure_20450251', 'district_expenditure_20450262',
        'district_expenditure_62450017', 'district_expenditure_64010018',
        'district_expenditure_2215', 'district_expenditure_2245',
        'district_revenue_0029', 'district_expenditure_2075'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
        INTO all_cols
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = tbl
          AND column_name NOT IN ('id', 'taluka');

        SELECT con.conname INTO cname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = tbl AND con.contype = 'u';

        SELECT array_agg(att.attname ORDER BY k.ord)
        INTO nk_cols
        FROM pg_constraint con
        JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
        JOIN pg_attribute att ON att.attnum = k.attnum AND att.attrelid = con.conrelid
        WHERE con.conname = cname AND att.attname <> 'taluka';

        SELECT string_agg(format('t2.%1$I = t.%1$I', c), ' AND ')
        INTO nk_predicate
        FROM unnest(nk_cols) AS c;

        EXECUTE format(
            'INSERT INTO %1$I (%2$s, taluka)
             SELECT %2$s, %3$L FROM %1$I t
             WHERE t.taluka = %4$L
               AND NOT EXISTS (
                   SELECT 1 FROM %1$I t2
                   WHERE t2.taluka = %3$L AND %5$s
               )',
            tbl, all_cols, '__district_office__', '', nk_predicate
        );
    END LOOP;
END $$;

-- ============================================================================
-- BLOCK 4: index only the 60 four-table-family tables
--   Skipped for the 17 district-expenditure tables — they hold at most a
--   few hundred rows (7 districts x sections); an extra index is overhead.
-- ============================================================================
DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'budget_post_details_20530019', 'post_status_20530019', 'post_expenses_20530019', 'unit_expenditure_20530019',
        'budget_post_details_20530028', 'post_status_20530028', 'post_expenses_20530028', 'unit_expenditure_20530028',
        'budget_post_details_20530153', 'post_status_20530153', 'post_expenses_20530153', 'unit_expenditure_20530153',
        'budget_post_details_20530162', 'post_status_20530162', 'post_expenses_20530162', 'unit_expenditure_20530162',
        'budget_post_details_20530233', 'post_status_20530233', 'post_expenses_20530233', 'unit_expenditure_20530233',
        'budget_post_details_20530242', 'post_status_20530242', 'post_expenses_20530242', 'unit_expenditure_20530242',
        'budget_post_details_20530304', 'post_status_20530304', 'post_expenses_20530304', 'unit_expenditure_20530304',
        'budget_post_details_20530313', 'post_status_20530313', 'post_expenses_20530313', 'unit_expenditure_20530313',
        'budget_post_details_20530378', 'post_status_20530378', 'post_expenses_20530378', 'unit_expenditure_20530378',
        'budget_post_details_20530387', 'post_status_20530387', 'post_expenses_20530387', 'unit_expenditure_20530387',
        'budget_post_details_20290037', 'post_status_20290037', 'post_expenses_20290037', 'unit_expenditure_20290037',
        'budget_post_details_20290046', 'post_status_20290046', 'post_expenses_20290046', 'unit_expenditure_20290046',
        'budget_post_details_20290182', 'post_status_20290182', 'post_expenses_20290182', 'unit_expenditure_20290182',
        'budget_post_details_20290262', 'post_status_20290262', 'post_expenses_20290262', 'unit_expenditure_20290262',
        'budget_post_details_20450091', 'post_status_20450091', 'post_expenses_20450091', 'unit_expenditure_20450091'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON %I (fiscal_year, district, taluka)',
            'idx_' || tbl || '_scope', tbl
        );
    END LOOP;
END $$;

-- ============================================================================
-- BLOCK 5: read-only per-table views for the chatbot (docs/plan.md section 5.3)
--   Carries every column except `taluka`, pre-filtered to the consolidated
--   row. The LLM never sees a `taluka` column and structurally cannot
--   express a query that double-counts or leaks a taluka row.
-- ============================================================================
DO $$
DECLARE
    tbl TEXT;
    cols TEXT;
    tables TEXT[] := ARRAY[
        'budget_post_details_20530019', 'post_status_20530019', 'post_expenses_20530019', 'unit_expenditure_20530019',
        'budget_post_details_20530028', 'post_status_20530028', 'post_expenses_20530028', 'unit_expenditure_20530028',
        'budget_post_details_20530153', 'post_status_20530153', 'post_expenses_20530153', 'unit_expenditure_20530153',
        'budget_post_details_20530162', 'post_status_20530162', 'post_expenses_20530162', 'unit_expenditure_20530162',
        'budget_post_details_20530233', 'post_status_20530233', 'post_expenses_20530233', 'unit_expenditure_20530233',
        'budget_post_details_20530242', 'post_status_20530242', 'post_expenses_20530242', 'unit_expenditure_20530242',
        'budget_post_details_20530304', 'post_status_20530304', 'post_expenses_20530304', 'unit_expenditure_20530304',
        'budget_post_details_20530313', 'post_status_20530313', 'post_expenses_20530313', 'unit_expenditure_20530313',
        'budget_post_details_20530378', 'post_status_20530378', 'post_expenses_20530378', 'unit_expenditure_20530378',
        'budget_post_details_20530387', 'post_status_20530387', 'post_expenses_20530387', 'unit_expenditure_20530387',
        'budget_post_details_20290037', 'post_status_20290037', 'post_expenses_20290037', 'unit_expenditure_20290037',
        'budget_post_details_20290046', 'post_status_20290046', 'post_expenses_20290046', 'unit_expenditure_20290046',
        'budget_post_details_20290182', 'post_status_20290182', 'post_expenses_20290182', 'unit_expenditure_20290182',
        'budget_post_details_20290262', 'post_status_20290262', 'post_expenses_20290262', 'unit_expenditure_20290262',
        'budget_post_details_20450091', 'post_status_20450091', 'post_expenses_20450091', 'unit_expenditure_20450091',
        'district_expenditure_22350311', 'district_expenditure_22350338',
        'district_expenditure_22353195', 'district_expenditure_22353408',
        'district_expenditure_76100149', 'district_expenditure_76100158',
        'district_expenditure_76100167', 'district_expenditure_76101871',
        'district_expenditure_20450182', 'district_expenditure_20450251', 'district_expenditure_20450262',
        'district_expenditure_62450017', 'district_expenditure_64010018',
        'district_expenditure_2215', 'district_expenditure_2245',
        'district_revenue_0029', 'district_expenditure_2075'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
        INTO cols
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = tbl
          AND column_name <> 'taluka';

        EXECUTE format(
            'CREATE OR REPLACE VIEW %I AS SELECT %s FROM %I WHERE taluka = %L',
            'v_' || tbl || '_district', cols, tbl, ''
        );
    END LOOP;
END $$;
