# Taluka-Owned Budget Data and District Consolidation

Technical Design Document (TDD)  
Status: implementation plan only; zero application implementation in this document  
Complexity: **L**  
Target architecture: the existing FastAPI/SQLAlchemy/PostgreSQL modular monolith

## Executive decision

Taluka activation and budget ownership are separate concerns and must remain separate in code:

- Activation creates or re-enables three taluka users. A real inactive-to-active transition resets each role to its documented default password. Saving an already-active selection does not reset credentials.
- A budget row keeps `district` as its geographical/reporting district and gains nullable `taluka_name`. `taluka_name IS NULL` means a direct district-owned row; a non-null value means a physical taluka source row.
- A taluka user reads and writes only `(district, taluka_name)` matching its authoritative database identity.
- A district/FY with participation rows reads a virtual, read-only projection of its included taluka rows. Its legacy `taluka_name IS NULL` rows remain preserved but are excluded. Participation is snapshotted per fiscal year, so a current activation does not rewrite historical totals.
- A district/FY without participation, Mumbai City, and DCO Staff continue to use direct rows.
- DCO, reports, exports, completion, and chatbot apply the same effective-source rule independently for every district. Direct and taluka rows are never added together.
- District aggregates are calculated at read time. No synthetic aggregate row or synthetic writable ID is stored.

This is the smallest design that preserves source truth, avoids stale roll-ups, retains legacy data, and fits the present modular monolith. It does not introduce a microservice, Redis, a queue, or cloud infrastructure. One narrowly scoped dependency, `sqlglot==30.13.0`, is added so chatbot-generated SQL is parsed into a server-owned query plan instead of being secured with regex/string rewriting.

---

## 1. MISSING CONTEXT

**Context sufficient.** The required documents and the relevant application, schema, authentication, scheme, fiscal-year, export, completion, cache, audit, notification, and chatbot paths were inspected.

Evidence boundary:

- The configured development database was inspected read-only. It is PostgreSQL 17.6, contains fiscal years `2025-26` and `2026-27`, 77 district-keyed budget tables, and 11,163 budget rows.
- It contains nine active taluka users for three active Thane talukas. No taluka user has a NULL, empty, or non-bcrypt password hash. The screenshot account `thane_ambarnath_o2` verifies against the documented `officer2@123` default. Eight of nine users still use their role default; one has a valid customized password.
- The screenshot's blank password input is therefore not evidence of a blank stored password. `templates/taluka_selection.html:96-114` deliberately leaves a password field empty, and `src/routers/ui_taluka_selection.py:252-264` treats an empty submission as “keep current.” This secure behavior stays.
- The configured database cannot be proven to be the exact Render database shown in the screenshot. Before deployment, record the deployed commit SHA and run the preflight queries in Phase 1 against that deployment.
- No test suite currently exists. The execution plan creates `unittest` coverage without adding pytest/httpx.

Implementation gates, not missing code context:

1. Take a database backup and retain the Phase 1 ownership/password audit output.
2. Confirm PostgreSQL `server_version_num >= 150000`; `NULLS NOT DISTINCT` requires PostgreSQL 15+. The inspected database is compatible.
3. Product owner acknowledges the cutover rule: legacy district totals cannot be truthfully divided among talukas. Creating the first participation row for a district/FY preserves but excludes the direct rows and starts taluka rows at zero. No automatic allocation is permitted. Prefer first cutover in a newly created FY; an in-progress FY requires an explicit acknowledgement and checksum report.
4. Budget domain owner approves the field-policy matrix below. Conflicting non-additive values must be shown, never silently summed or discarded.
5. Run schema changes in a controlled write-drain window. Migration preflight must show no long-running transaction holding a conflicting lock; a five-second lock timeout fails the deployment without an automatic migration retry.

---

## 2. COMPLEXITY ASSESSMENT

**L — cross-module schema and authorization change.**

Why L, not XL:

- It changes shared schema semantics, auth/session trust, CRUD scope, 77 budget tables, completion, fiscal-year cloning, exports, and chatbot behavior.
- It does not create a new deployable service, database, cache cluster, queue, or infrastructure component.
- It remains a modular monolith and uses the pinned FastAPI, SQLAlchemy 2.0.48, psycopg2, passlib, bcrypt, and PostgreSQL stack in `requirements.txt:1-53`.

Sections 3–6 therefore apply.

---

## 3. BLAST RADIUS

### 3.1 Current flow and confirmed defects

1. `src/utils_district.py:33-61,76-94` explicitly maps a taluka user to its parent district and authorizes that district's physical row.
2. `src/core/secure_crud.py:106-180` applies that district-only rule to shared CRUD. Several UI/API modules also query by `district` directly.
3. New taluka users already receive role defaults in `src/utils_taluka_user_management.py:9-20,74-83`. Existing users are only marked active at `src/utils_taluka_user_management.py:68-72`; their password is not reset. That is the credential defect.
4. The role hash cache at `src/utils_taluka_user_management.py:9-20` reuses the same bcrypt hash/salt for every user of a role. Each reset must generate a fresh bcrypt hash.
5. Authorization context is currently read from editable cookies in `src/utils_auth.py:27-66` and set as unsigned values in `src/routers/auth.py:86-98`. This cannot protect cross-taluka rows.
6. Chatbot fast SQL executes before SQL policy enforcement at `src/chatbot/main.py:91-117`; response/semantic cache keys omit user scope at `src/chatbot/main.py:91-95` and `src/chatbot/core/query_classifier.py:189-218`.
7. Multiple scheme mutations import `invalidate_district_status_cache`, but no such function exists. Two cache services reference nonexistent `memory_cache._cache` rather than `_store`: `src/schemes/s2053/subs/s20530313/shared/services/cache_service.py:20-26` and `src/schemes/s2053/subs/s20530387/shared/services/cache_service.py:20-26`.
8. Fiscal-year creation at `src/routers/fiscal_year.py:162-214` is split between a four-table loop and a partial hard-coded family list; it omits some implemented simple families.
9. Completion is unique only by district/subscheme/FY in `src/models.py:207-220` and is restricted to district assistants in `src/routers/completion_status.py:43-155`.

Credential transition contract, anchored to `logincredentials.txt:3-5,10-42` and the existing role map at `src/utils_taluka_user_management.py:9-20`:

| Role | Default on first creation or real reactivation |
|---|---|
| `officer1` | `officer1@123` |
| `officer2` | `officer2@123` |
| `assistant` | `assistant@123` |

The password is freshly bcrypt-hashed per user; it is never stored/displayed as plaintext. An active→active save does not reset it. Deactivation revokes sessions and disables login but retains the hash/data; the subsequent inactive→active transition resets to the role default and requires a first-login change. The blank password input in the screenshot remains blank because it means “keep/reset by lifecycle,” not “stored password is blank.”

### 3.2 Target ownership and read contract

`taluka_name` is the only new ownership column on budget tables:

| Principal/read mode | Physical rows admitted | Write permission | Result shape |
|---|---|---|---|
| Taluka assistant | exact parent `district` and exact `taluka_name`; management row active and FY participation included | exact physical rows only while timing allows | existing editable rows |
| Taluka officers | same exact source | none | existing read-only rows |
| Direct district | `district = unit AND taluka_name IS NULL` | assistant only, timing window applies | existing rows |
| Taluka-backed district/FY | included fiscal-year participation rows for the district; direct row excluded | none | virtual consolidated rows plus authorized drill-down |
| DCO | per district/FY: direct row when no participation exists; included talukas otherwise; DCO Staff direct | none | current division/report projections |
| System task | explicit named system scope only | task-specific | never implicit/unscoped |

`src/core/data_scope.py` **[NEW]** owns this contract. It is resolved from an authenticated database `User`, never from `auth_level`, `auth_role`, or `auth_unit` cookies. `district` remains the reporting parent, satisfying the internal-identifier invariants in `docs/DYNAMIC_FISCAL_YEAR_REFACTORING_GUIDE.md:496-538`.

`TalukaFiscalYearParticipation` **[NEW]** is explicit. The existence of any row for `(fiscal_year, district)` means that district/FY has cut over, even when every row is excluded; this prevents the legacy district total from unexpectedly reappearing after the last taluka is deactivated. It is never inferred from the selection JSON because `src/utils_taluka.py:31-40` currently treats an empty saved list as “all talukas.”

Account activation remains global, but inclusion is fiscal-year-specific. The "designated current FY" follows the lexicographically highest active `FiscalYear.year_range` semantics of `src/utils_fiscal_year.py:get_default_fiscal_year`, but mutations use a new uncached `get_current_fiscal_year_for_update(db)` after taking the shared lock; the 300-second cache and selection-page cookie are never authoritative. Fiscal-year creation and selection mutation take the same PostgreSQL transaction advisory lock before resolving/rechecking that value, so a concurrent new FY cannot receive a stale participation snapshot:

- a selection change locks and updates the designated current FY participation only;
- historical FY participation is immutable through the selection UI;
- fiscal-year creation snapshots then-active management rows into the new FY;
- deactivation disables login globally and excludes the taluka from the current FY only; prior FY inclusion remains historical truth;
- reactivation reuses retained source data and re-includes the taluka in the current FY;
- `20530387` (DCO Staff), Mumbai City, and every registry entry marked non-taluka-compatible always use direct rows and never receive participation or taluka seeds.

Canonical effective-source predicate for each owned row `r` (implemented with bound/correlated SQLAlchemy expressions, not string SQL):

```text
taluka principal:
  r.fiscal_year = :fy AND r.district = :district AND r.taluka_name = :taluka
  AND included_participation(:fy, :district, :taluka)

district/DCO projection per r:
  (EXISTS included participation p matching r.fiscal_year/r.district/r.taluka_name)
  OR
  (NOT EXISTS any participation p for r.fiscal_year/r.district AND r.taluka_name IS NULL)
```

The second branch is deliberately `NOT EXISTS any participation`, not “no included participation.” Thus an all-excluded FY produces an empty consolidated total rather than resurrecting preserved legacy rows. Registry direct-only predicates bypass participation and require `taluka_name IS NULL`.

### 3.3 Aggregation policy

The registry in `src/core/budget_data_registry.py` **[NEW]** stores, per model, the natural dimensions, additive expressions, non-additive presentation rules, seed columns, and whether a row subtype is taluka-compatible. The registry is anchored to `BaseSchemeConfig.forms` at `src/core/base_config.py:27-49` and model lookup at `src/utils_scheme.py:178-209`.

Rules:

| Family/fields | District projection rule | Existing anchor |
|---|---|---|
| Sanctioned, filled, vacant, working, and status counts | `SUM` by reporting natural key | `src/schemes/s2053/subs/s20530028/ui_budget_summary.py:189-215` |
| Budget post numeric pay/allowance components | calculate any rate-derived value per physical source row, then `SUM`; do not calculate HRA from an already-summed base | `src/schemes/s2053/subs/s20530028/excel_export/populators/budget_post_details.py:96-140` |
| `hra_rate` and other categorical rate attributes | `CONSENSUS`; return the common value, otherwise a read-only `mixed` marker and owner drill-down | validation at `src/schemes/s2053/subs/s20530028/schemas.py:8-22` |
| Post-expense filled/vacant counts | `SUM` by `(category,class_type)` across physical owners | category/class-specific writes at `src/schemes/s2053/subs/s20530019/ui_post_expenses.py:175-187` |
| Post-expense monetary fields repeated across category/class rows | `MAX_PER_OWNER_THEN_SUM_ACROSS_OWNERS`; scope bulk sync by owner before reducing; differing repeated values for one owner emit conflict metadata/drill-down | owner-wide sync at `src/schemes/s2053/subs/s20530019/ui_post_expenses.py:188-216` |
| Post status monetary/count fields | `SUM` by category/class/status | `src/schemes/s2045/common/services/post_status_service.py:249-357` |
| Unit expenditure and all simple expenditure/revenue numeric fields | `SUM` by the existing natural dimensions | representative `src/schemes/s2235/subs/s22350311/models.py:16-37` |
| `remarks` | no numeric aggregation; expose ordered `{taluka_name, remark}` drill-down and a bounded display summary | representative `src/schemes/s2215/subs/s2215/models.py:21-53` |
| Post-level details | taluka/direct rows inherit ownership from the physical budget-post ID; district projection groups by level name, pay stage, pay level, and HRA rate and has no writable ID | `src/schemes/common/post_levels/models.py:13-51` |

If a field is absent from the registry, consolidated reading fails closed with a configuration error and logs the model/field. It must never default to `SUM` merely because the SQL type is numeric.

Exact four-table registry field sets, anchored to `src/schemes/s2053/subs/s20530028/models.py:9-105`:

- Budget post `SUM`: `sanctioned_posts_prev1`, `sanctioned_posts_curr`, `special_pay`, `basic_pay`, `grade_pay`, `local_supplementary_allowance`, `vehicle_allowance`, `washing_allowance`, `cash_allowance`, `footwear_allowance_other`; `hra_rate` is `CONSENSUS`.
- Post status `SUM`: `posts`, `salary`, `grade_pay`, `special_pay`, `dearness_allowance`, `local_supplementary_allowance`, `house_rent_allowance`, `travel_allowance`, `other`.
- Post expenses `SUM` by `(category,class_type)`: `filled_posts`, `vacant_posts`. `MAX_PER_OWNER_THEN_SUM_ACROSS_OWNERS`: `medical_expenses`, `festival_advance`, `swagram_maharashtra_darshan`, `seventh_pay_commission_difference_nps`, `nps`, `seventh_pay_commission_difference`, `other`. The per-owner maximum is taken across that owner's repeated category/class rows before owners are summed, preventing synchronized amounts from being counted more than once; if one owner's repeated non-null values differ, the DTO still uses max but marks a conflict and exposes the source values rather than silently concealing drift. Nullable values use zero only for arithmetic and become non-null totals in aggregate DTOs.
- Unit expenditure `SUM`: `expenditure_prev4`, `expenditure_prev3`, `expenditure_prev2`, `budget_prev1`, `forecast_prev1`, `budget_curr_estimating_officer`, `budget_curr_controlling_officer`, `budget_curr_admin_dept`, `budget_curr_finance_dept`.

For simple tables the registry lists the six explicit measures from each existing model rather than using type introspection: s2045 factory at `src/schemes/s2045/common/district_expenditure/base_models.py:48-73`; 0029 at `src/schemes/s0029/subs/s0029/models.py:19-25`; 2215 at `src/schemes/s2215/subs/s2215/models.py:25-38`; 2235 representative at `src/schemes/s2235/subs/s22350311/models.py:17-23`; 2245 at `src/schemes/s2245/subs/s2245/models.py:19-27`; 6245/6401 representative at `src/schemes/s6245/subs/s62450017/models.py:18-26`; 7610 representative at `src/schemes/s7610/subs/s76100149/models.py:18-26`; and district 2075 at `src/schemes/s2075/models.py:53-62`. IDs, scheme codes, natural dimensions, owner fields, timestamps, and remarks are never summed.

### 3.4 Schema changes and exact migration SQL

#### [NEW] `migrations/core/013_add_migration_checksums.sql`

The checksum table is separate so the existing `schema_migrations` shape at `src/utils_migrations.py:235-249` remains backward-compatible. When 013 first succeeds, the serialized runner hashes the exact bytes of every already-recorded migration, inserts that baseline with `ON CONFLICT DO NOTHING`, and prints it in preflight evidence. Every later run rejects a version whose file hash differs.

```sql
SET LOCAL lock_timeout = '5s';

CREATE TABLE schema_migration_checksums (
    version VARCHAR PRIMARY KEY
        REFERENCES schema_migrations (version) ON DELETE CASCADE,
    checksum CHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### [NEW] `migrations/core/014_add_taluka_data_ownership.sql`

The migration is transactional under the existing runner at `src/utils_migrations.py:260-332`. It is backward-compatible with the old application because `taluka_name` is nullable and omitted old inserts remain direct-district rows. Before and after execution, the runner compares columns, types, nullability, index predicates, foreign-key targets/actions, and `pg_get_constraintdef` output to the migration manifest; matching an object name alone is not accepted as proof of schema equivalence.

```sql
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '300s';

ALTER TABLE district_taluka_selection
    ADD COLUMN IF NOT EXISTS selection_revision INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS taluka_fiscal_year_participation (
    fiscal_year VARCHAR NOT NULL
        REFERENCES fiscal_years (year_range) ON UPDATE CASCADE ON DELETE RESTRICT,
    district VARCHAR(100) NOT NULL,
    taluka_name VARCHAR(100) NOT NULL,
    is_included BOOLEAN NOT NULL DEFAULT TRUE,
    included_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    excluded_at TIMESTAMPTZ,
    changed_by VARCHAR(50) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (fiscal_year, district, taluka_name),
    CONSTRAINT fk_taluka_fy_management
        FOREIGN KEY (district, taluka_name)
        REFERENCES taluka_user_management (district, taluka_name)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

ALTER TABLE sub_schema_completions
    ADD COLUMN IF NOT EXISTS taluka_name VARCHAR(100);

ALTER TABLE sub_schema_completions
    DROP CONSTRAINT IF EXISTS uq_completion_district_scheme_year;
ALTER TABLE sub_schema_completions
    DROP CONSTRAINT IF EXISTS uq_completion_district_scheme_year_owner;
ALTER TABLE sub_schema_completions
    ADD CONSTRAINT uq_completion_district_scheme_year_owner
    UNIQUE NULLS NOT DISTINCT (district, sub_scheme_code, fiscal_year, taluka_name);

ALTER TABLE sub_schema_completions
    DROP CONSTRAINT IF EXISTS fk_completion_taluka_owner;
ALTER TABLE sub_schema_completions
    ADD CONSTRAINT fk_completion_taluka_owner
    FOREIGN KEY (district, taluka_name)
    REFERENCES taluka_user_management (district, taluka_name)
    ON UPDATE CASCADE ON DELETE RESTRICT NOT VALID;

DO $$
DECLARE
    code TEXT;
    table_name TEXT;
    constraint_name TEXT;
    r RECORD;
    all_tables TEXT[] := ARRAY[
        'budget_post_details_20530019','post_status_20530019','post_expenses_20530019','unit_expenditure_20530019',
        'budget_post_details_20530028','post_status_20530028','post_expenses_20530028','unit_expenditure_20530028',
        'budget_post_details_20530153','post_status_20530153','post_expenses_20530153','unit_expenditure_20530153',
        'budget_post_details_20530162','post_status_20530162','post_expenses_20530162','unit_expenditure_20530162',
        'budget_post_details_20530233','post_status_20530233','post_expenses_20530233','unit_expenditure_20530233',
        'budget_post_details_20530242','post_status_20530242','post_expenses_20530242','unit_expenditure_20530242',
        'budget_post_details_20530304','post_status_20530304','post_expenses_20530304','unit_expenditure_20530304',
        'budget_post_details_20530313','post_status_20530313','post_expenses_20530313','unit_expenditure_20530313',
        'budget_post_details_20530378','post_status_20530378','post_expenses_20530378','unit_expenditure_20530378',
        'budget_post_details_20530387','post_status_20530387','post_expenses_20530387','unit_expenditure_20530387',
        'budget_post_details_20290037','post_status_20290037','post_expenses_20290037','unit_expenditure_20290037',
        'budget_post_details_20290046','post_status_20290046','post_expenses_20290046','unit_expenditure_20290046',
        'budget_post_details_20290182','post_status_20290182','post_expenses_20290182','unit_expenditure_20290182',
        'budget_post_details_20290262','post_status_20290262','post_expenses_20290262','unit_expenditure_20290262',
        'budget_post_details_20450091','post_status_20450091','post_expenses_20450091','unit_expenditure_20450091',
        'district_expenditure_20450182','district_expenditure_20450251','district_expenditure_20450262',
        'district_expenditure_22350311','district_expenditure_22350338','district_expenditure_22353195','district_expenditure_22353408',
        'district_expenditure_76100149','district_expenditure_76100158','district_expenditure_76100167','district_expenditure_76101871',
        'district_expenditure_62450017','district_expenditure_64010018','district_expenditure_2075',
        'district_revenue_0029','district_expenditure_2215','district_expenditure_2245'
    ];
BEGIN
    FOREACH table_name IN ARRAY all_tables LOOP
        EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS taluka_name VARCHAR(100)', table_name);
    END LOOP;

    FOREACH code IN ARRAY ARRAY[
        '20530019','20530028','20530153','20530162','20530233','20530242','20530304','20530313','20530378','20530387',
        '20290037','20290046','20290182','20290262','20450091'
    ] LOOP
        table_name := format('budget_post_details_%s', code);
        constraint_name := format('uq_bpd_%s_natural_key', code);
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', table_name, constraint_name);
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I UNIQUE NULLS NOT DISTINCT (fiscal_year,district,category,class_type,designation,taluka_name)', table_name, constraint_name);

        table_name := format('post_status_%s', code);
        constraint_name := format('uq_ps_%s_natural_key', code);
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', table_name, constraint_name);
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I UNIQUE NULLS NOT DISTINCT (fiscal_year,district,category,class_type,status,taluka_name)', table_name, constraint_name);

        table_name := format('post_expenses_%s', code);
        constraint_name := format('uq_pe_%s_natural_key', code);
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', table_name, constraint_name);
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I UNIQUE NULLS NOT DISTINCT (fiscal_year,district,category,class_type,taluka_name)', table_name, constraint_name);

        table_name := format('unit_expenditure_%s', code);
        constraint_name := format('uq_ue_%s_natural_key', code);
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', table_name, constraint_name);
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I UNIQUE NULLS NOT DISTINCT (fiscal_year,district,unit_account,taluka_name)', table_name, constraint_name);
    END LOOP;

    FOR r IN SELECT * FROM (VALUES
        ('district_expenditure_20450182','uq_district_expenditure_20450182_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_20450251','uq_district_expenditure_20450251_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_20450262','uq_district_expenditure_20450262_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_22350311','uq_district_exp_22350311_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_22350338','uq_district_exp_22350338_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_22353195','uq_district_exp_22353195_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_22353408','uq_district_exp_22353408_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_76100149','uq_district_exp_76100149_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_76100158','uq_district_exp_76100158_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_76100167','uq_district_exp_76100167_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_76101871','uq_district_exp_76101871_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_62450017','uq_district_exp_62450017_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_64010018','uq_district_exp_64010018_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_expenditure_2075','uq_district_exp_2075_natural_key','fiscal_year,sub_scheme_code,district,taluka_name'),
        ('district_revenue_0029','uq_district_rev_0029_natural_key','fiscal_year,sub_scheme_code,table_section_code,district,taluka_name'),
        ('district_expenditure_2215','uq_district_exp_2215_natural_key','fiscal_year,sub_scheme_code,account_head_code,district,taluka_name'),
        ('district_expenditure_2245','uq_district_exp_2245_natural_key','fiscal_year,sub_scheme_code,table_section_code,district,taluka_name')
    ) AS v(table_name,constraint_name,key_columns) LOOP
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', r.table_name, r.constraint_name);
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I UNIQUE NULLS NOT DISTINCT (%s)', r.table_name, r.constraint_name, r.key_columns);
    END LOOP;

    FOREACH table_name IN ARRAY all_tables LOOP
        EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (fiscal_year,district,taluka_name)', 'idx_' || table_name || '_scope', table_name);
        constraint_name := 'fk_' || table_name || '_taluka';
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = constraint_name
              AND conrelid = to_regclass(table_name)
        ) THEN
            EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (district,taluka_name) REFERENCES taluka_user_management(district,taluka_name) ON UPDATE CASCADE ON DELETE RESTRICT NOT VALID', table_name, constraint_name);
        END IF;
        EXECUTE format('ALTER TABLE %I VALIDATE CONSTRAINT %I', table_name, constraint_name);
    END LOOP;
END $$;

ALTER TABLE sub_schema_completions VALIDATE CONSTRAINT fk_completion_taluka_owner;
```

The SQL checks every dynamic FK by name/table before creation and validates all 77 inside the same transaction after the read-only orphan preflight passes. The new participation table starts empty: migration alone cannot hide any legacy district data. `sub_head_expenditure_2075` is intentionally excluded because `src/schemes/s2075/models.py:13-41` documents it as DCO-only, not district/taluka data.

#### [NEW] `migrations/core/015_add_verified_user_sessions.sql`

```sql
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '300s';

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_taluka_unit_role
    ON users (unit, role)
    WHERE level = 'taluka';

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT * FROM (VALUES
        ('fk_tum_officer1_user', 'officer1_user_id'),
        ('fk_tum_officer2_user', 'officer2_user_id'),
        ('fk_tum_assistant_user', 'assistant_user_id')
    ) AS v(constraint_name, column_name) LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = r.constraint_name
              AND conrelid = 'taluka_user_management'::regclass
        ) THEN
            EXECUTE format(
                'ALTER TABLE taluka_user_management ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES users(id) ON DELETE RESTRICT NOT VALID',
                r.constraint_name,
                r.column_name
            );
        END IF;
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS user_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    admin_user_id INTEGER REFERENCES admin_users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    csrf_token CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    ip_address VARCHAR(45),
    user_agent VARCHAR(200),
    CONSTRAINT ck_user_sessions_one_principal CHECK (
        (user_id IS NOT NULL AND admin_user_id IS NULL)
        OR (user_id IS NULL AND admin_user_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_active
    ON user_sessions (user_id, expires_at)
    WHERE revoked_at IS NULL AND user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_sessions_admin_active
    ON user_sessions (admin_user_id, expires_at)
    WHERE revoked_at IS NULL AND admin_user_id IS NOT NULL;

ALTER TABLE taluka_user_management VALIDATE CONSTRAINT fk_tum_officer1_user;
ALTER TABLE taluka_user_management VALIDATE CONSTRAINT fk_tum_officer2_user;
ALTER TABLE taluka_user_management VALIDATE CONSTRAINT fk_tum_assistant_user;
```

Existing users retain `must_change_password = FALSE`; no migration mass-resets a valid password. At the first authoritative post-cutover login, a taluka user row is locked before bcrypt verification. If the submitted password is that role's documented default, login atomically sets `must_change_password = TRUE` and issues only a restricted session; a customized password remains unaffected. Newly created users and real reactivation resets set the flag directly. This closes the existing-active/default-password case without guessing from bcrypt hashes in a migration.

### 3.5 Model metadata files

`taluka_name = Column(String(100), nullable=True, index=False)` is added by `SchemeModelMixin` in `src/core/base_models.py:6-23`; each natural constraint below adds it with `postgresql_nulls_not_distinct=True`, which SQLAlchemy 2.0 supports and the pinned 2.0.48 already contains.

`src/models.py:64-87,207-220` additionally maps `DistrictTalukaSelection.selection_revision`, `TalukaFiscalYearParticipation` **[NEW]**, and completion ownership. The participation model uses `(fiscal_year, district, taluka_name)` as its primary key and is the sole consolidation-mode authority; management `is_active` controls login/current selection, not historical FY interpretation.

Four-table model files to modify:

- `src/schemes/s2053/subs/s20530019/models.py`
- `src/schemes/s2053/subs/s20530028/models.py`
- `src/schemes/s2053/subs/s20530153/models.py`
- `src/schemes/s2053/subs/s20530162/models.py`
- `src/schemes/s2053/subs/s20530233/models.py`
- `src/schemes/s2053/subs/s20530242/models.py`
- `src/schemes/s2053/subs/s20530304/models.py`
- `src/schemes/s2053/subs/s20530313/models.py`
- `src/schemes/s2053/subs/s20530378/models.py`
- `src/schemes/s2053/subs/s20530387/models.py`
- `src/schemes/s2029/subs/s20290037/models.py`
- `src/schemes/s2029/subs/s20290046/models.py`
- `src/schemes/s2029/subs/s20290182/models.py`
- `src/schemes/s2029/subs/s20290262/models.py`
- `src/schemes/s2045/subs/s20450091/models.py`

Simple-family model files to modify:

- `src/schemes/s2045/common/district_expenditure/base_models.py`
- `src/schemes/s2235/subs/s22350311/models.py`
- `src/schemes/s2235/subs/s22350338/models.py`
- `src/schemes/s2235/subs/s22353195/models.py`
- `src/schemes/s2235/subs/s22353408/models.py`
- `src/schemes/s7610/subs/s76100149/models.py`
- `src/schemes/s7610/subs/s76100158/models.py`
- `src/schemes/s7610/subs/s76100167/models.py`
- `src/schemes/s7610/subs/s76101871/models.py`
- `src/schemes/s6245/subs/s62450017/models.py`
- `src/schemes/s6401/subs/s64010018/models.py`
- `src/schemes/s2075/models.py` (district class only)
- `src/schemes/s0029/subs/s0029/models.py`
- `src/schemes/s2215/subs/s2215/models.py`
- `src/schemes/s2245/subs/s2245/models.py`

`src/models.py` also changes for selection state, completion ownership, credential state, and `UserSession`.

### 3.6 Runtime files

Core ownership/authentication:

- `src/core/data_scope.py` **[NEW]**
- `src/core/budget_data_registry.py` **[NEW]**
- `src/core/aggregation.py` **[NEW]**
- `src/core/secure_crud.py`
- `src/core/base_router.py`
- `src/core/templates.py`
- `src/core/template_context.py`
- `src/database.py`
- `src/utils_district.py`
- `src/utils_auth.py`
- `src/utils_taluka.py`
- `src/utils_fiscal_year.py`
- `src/utils_cache.py`
- `src/security/session_service.py` **[NEW]**
- `src/routers/auth.py`
- `src/routers/admin.py`
- `templates/change_password.html` **[NEW]**
- `templates/admin_users.html`
- `templates/scheme_selection.html`
- `src/routers/ui_scheme_selection.py`
- `src/main.py`

Activation/completion/FY:

- `src/utils_taluka_user_management.py`
- `src/routers/ui_taluka_selection.py`
- `templates/taluka_selection.html`
- `src/notification_service.py`
- `src/audit_service.py`
- `src/routers/completion_status.py`
- `templates/base.html`
- `src/routers/fiscal_year.py`

Shared data paths:

- `src/schemes/common/post_levels/api_router.py`
- `src/schemes/common/post_levels/repository.py`
- `src/schemes/common/post_levels/service.py`
- `src/schemes/s2045/common/district_expenditure/base_router.py`
- `src/schemes/s2045/common/district_expenditure/base_helpers.py`
- `src/schemes/s2053/subs/s20530028/budget_post_details/repositories/budget_post_repository.py`
- `src/schemes/s2053/subs/s20530028/budget_post_details/services/budget_post_service.py`
- `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py`
- `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/api_controller.py`
- `src/routers/ui_consolidated_budget.py` **[NEW]**
- `templates/consolidated_budget.html` **[NEW]**
- bulk-seed helpers: `src/schemes/s0029/subs/s0029/helpers.py`, `src/schemes/s2215/subs/s2215/helpers.py`, `src/schemes/s2245/subs/s2245/helpers.py`, `src/schemes/s6245/subs/s62450017/helpers.py`, `src/schemes/s6401/subs/s64010018/helpers.py`, all four `src/schemes/s7610/subs/*/helpers.py`, and all four `src/schemes/s2235/subs/*/helpers.py`

Simple UI/API rollout files:

- `src/schemes/s0029/subs/s0029/router_ui.py`, `src/schemes/s0029/subs/s0029/router_api.py`
- `src/schemes/s2215/subs/s2215/router_ui.py`, `src/schemes/s2215/subs/s2215/router_api.py`
- `src/schemes/s2245/subs/s2245/router_ui.py`, `src/schemes/s2245/subs/s2245/router_api.py`
- `src/schemes/s2075/router_ui.py`, `src/schemes/s2075/router_api.py`
- `src/schemes/s2235/subs/s22350311/router_ui.py`, `src/schemes/s2235/subs/s22350311/router_api.py`
- `src/schemes/s2235/subs/s22350338/router_ui.py`, `src/schemes/s2235/subs/s22350338/router_api.py`
- `src/schemes/s2235/subs/s22353195/router_ui.py`, `src/schemes/s2235/subs/s22353195/router_api.py`
- `src/schemes/s2235/subs/s22353408/router_ui.py`, `src/schemes/s2235/subs/s22353408/router_api.py`
- `src/schemes/s7610/subs/s76100149/router_ui.py`, `src/schemes/s7610/subs/s76100149/router_api.py`
- `src/schemes/s7610/subs/s76100158/router_ui.py`, `src/schemes/s7610/subs/s76100158/router_api.py`
- `src/schemes/s7610/subs/s76100167/router_ui.py`, `src/schemes/s7610/subs/s76100167/router_api.py`
- `src/schemes/s7610/subs/s76101871/router_ui.py`, `src/schemes/s7610/subs/s76101871/router_api.py`
- `src/schemes/s6245/subs/s62450017/router_ui.py`, `src/schemes/s6245/subs/s62450017/router_api.py`
- `src/schemes/s6401/subs/s64010018/router_ui.py`, `src/schemes/s6401/subs/s64010018/router_api.py`

The session-level criterion selects the correct physical sources, but it does not pretend that arbitrary legacy readers aggregate correctly. The registry/test manifest covers these verified-existing files for each consolidatable four-table base below:

- bases: `src/schemes/s2053/subs/s20530019`, `s20530028`, `s20530153`, `s20530162`, `s20530233`, `s20530242`, `s20530304`, `s20530313`, `s20530378`; `src/schemes/s2029/subs/s20290037`, `s20290046`, `s20290182`, `s20290262`; and `src/schemes/s2045/subs/s20450091`;
- physical editor suffixes: `ui_budget_details.py`, `api_budget_details.py`, `ui_post_status.py`, `ui_post_expenses.py`, and `ui_unit_expenditure.py` (the refactored `s20530028` equivalents are its four controller packages);
- existing reducer suffixes: `ui_budget_summary.py`, `ui_category_info.py`, and `ui_abstract.py`;
- export suffixes: `excel_export/template_export_service.py` and `excel_export/populators/{budget_post_details,post_status,post_expenses,unit_expenditure}.py`.

The physical editors are registered `PHYSICAL_EXACT`: taluka/direct users retain them; aggregate users are routed to the new canonical projection. The legacy `ui_budget_summary.py`, `ui_category_info.py`, and `ui_abstract.py` reducers are also classified `CANONICAL_AGGREGATE` for aggregate principals and receive canonical policy-reduced data; their existing physical behavior remains available only to exact taluka/direct principals. A legacy reducer may be reclassified `AGGREGATION_SAFE` only after an explicit all-14 route-level golden test proves its rendered values and conflict metadata. Export populators become `AGGREGATION_SAFE` only after their all-14-scheme workbook tests. The direct-only `src/schemes/s2053/subs/s20530387` tree is registered direct and is explicitly tested never to admit taluka rows. Shared reducers at `src/schemes/s2053/common/services/abstract_service.py:73-305`, `src/schemes/s2045/common/services/abstract_service.py:104-314`, `src/schemes/s2045/common/services/post_status_service.py:261-384`, and `src/schemes/s2045/common/services/category_info_service.py:57-71` receive the same scoped session.

Phases 37.0A–37.0H update every current `export_with_throttle` caller so a request session never crosses into its thread-pool callback. Simple-family reducers that currently risk last-row-wins behavior are explicit targets in Phases 37.1–37.5, including `src/schemes/s0029/subs/s0029/excel_export/arthsankalpiy_jilah.py` and `src/schemes/s2235/excel_export/populators/s2235_populator.py`. Phases 37.6A–37.6S explicitly wire every consolidatable four-table populator listed above to policy-reduced rows; a scoped session alone cannot prevent last-row-wins or repeated-expense double counting. Any raw SQL or manual `SessionLocal()` consumer that bypasses the scoped session must be changed or fail closed. The regression suite enumerates all 15 four-table sub-schemes and all export pipelines described at `docs/ARCHITECTURE.md:863-894`; no wildcard discovery is accepted as proof of coverage.

Chatbot:

- `src/routers/api_assistant.py`
- `src/chatbot/main.py`
- `src/chatbot/security/policies.py`
- `src/chatbot/core/query_classifier.py`
- `src/chatbot/core/query_plan.py` **[NEW]**
- `src/chatbot/core/sql_validator.py`
- `src/chatbot/core/schema_engine.py`
- `src/chatbot/processors/query_execution.py`

Operational correctness/docs:

- `src/routers/training.py`
- `src/audit_middleware.py`
- `src/schemes/s2053/subs/s20530313/shared/services/cache_service.py`
- `src/schemes/s2053/subs/s20530387/shared/services/cache_service.py`
- `src/utils_migrations.py`
- `scripts/migrate.py` **[NEW]**
- `tests/db_harness.py` **[NEW]**
- `tests/fixtures/pre_taluka_schema.sql` **[NEW]**
- `docs/ARCHITECTURE.md`
- `docs/CHATBOT_ARCHITECTURE_PLAN.md`
- `docs/DYNAMIC_FISCAL_YEAR_REFACTORING_GUIDE.md`

### 3.7 Dependency changes

One dependency is added: `sqlglot==30.13.0` in `requirements.txt`.

- Keep `SQLAlchemy==2.0.48`; the required PostgreSQL `postgresql_nulls_not_distinct` option exists in SQLAlchemy 2.0.16+.
- Keep `passlib==1.7.4` and `bcrypt==4.3.0` for this feature; bcrypt rounds remain 12 as configured at `src/routers/auth.py:20`.
- Do not add Redis despite `redis==7.3.0`; no Redis server/configuration is part of the current local architecture.
- `sqlglot==30.13.0` parses one PostgreSQL `SELECT` into an AST so the server can reject unsupported syntax and compile a registry-owned scoped query. It is not used to “sanitize” arbitrary SQL and does not expand the accepted grammar.
- `requirements.txt` is the only pinned dependency manifest; no lockfile exists. Pin the exact version there and verify the installed version in the chatbot boundary test.
- Require PostgreSQL 15+ at startup/migration time.

Primary-source validation: PostgreSQL documents `NULLS NOT DISTINCT` uniqueness and PostgreSQL 15+ support; SQLAlchemy documents `postgresql_nulls_not_distinct` and its ORM execution event for global access-control criteria; PostgreSQL row locks last until transaction end; OWASP recommends synchronizer tokens for stateful CSRF protection and never storing plaintext passwords. SQLGlot 30.13.0 was released on 2026-07-20. Sources: [PostgreSQL unique indexes](https://www.postgresql.org/docs/17/indexes-unique.html), [PostgreSQL explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html), [SQLAlchemy ORM query events](https://docs.sqlalchemy.org/en/20/orm/events.html), [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [SQLGlot release](https://pypi.org/project/sqlglot/).

---

## 4. DATA & RESILIENCE

### 4.1 Transaction boundaries

Taluka selection mutation is one transaction:

1. Take `pg_advisory_xact_lock(hashtextextended('fiscal-year-membership', 0))`, resolve/recheck the designated current FY, then take the exclusive district/FY mode lock. Insert the district selection row with `ON CONFLICT DO NOTHING`, then lock it with `SELECT ... FOR UPDATE`.
2. Validate/deduplicate against `src/utils_taluka.py:12-29`, rejecting unknown/duplicate values. If desired management plus participation state already equals the locked state, return the idempotent no-op even with a stale form; otherwise compare `expected_revision` and return 409 when stale. “Same active management set but no participation yet” is not equal state and remains a first cutover.
3. Lock affected `User` rows in ascending ID order. Apply inactive-to-active and active-to-inactive transitions, validate all three role-user links, fresh password hashes for real reactivations, session revocation, current-FY participation inclusion/exclusion, selection revision, and strict sanitized audit events.
4. Commit.
5. Only after commit, invoke the existing best-effort notification path with an immutable recipient snapshot. Current pre-commit notification calls at `src/utils_taluka_user_management.py:136-140,173-177` move out of the transaction; no queue is introduced.

Budget mutation takes `pg_advisory_xact_lock_shared(hashtextextended('budget-mode:' || district || ':' || fiscal_year, 0))` before its exact-owner load, then performs validation, row change, and audit in one transaction. Multiple ordinary writes may coexist, while a selection cutover takes the exclusive form of the same lock and waits for all prior writes before recomputing its legacy checksum; no direct write can commit across the mode switch. Existing payload `district` fields remain accepted temporarily for compatibility, but a supplied value that differs from the authoritative principal is rejected and the stored owner is always server-overwritten. `AuditService` receives that same session in strict mode; an audit insert failure rolls back the budget mutation instead of being swallowed or written through a later `SessionLocal()`. Aggregation is a read projection and creates no second write. Repository methods such as `src/schemes/common/post_levels/repository.py:67-170` must stop committing internally; the route/service transaction owns commit.

Completion mutation first `INSERT ... ON CONFLICT DO NOTHING`, then locks the now-existing exact `(district,taluka_name,subscheme,FY)` row with `SELECT ... FOR UPDATE`, sets the requested state, commits, and makes the derived district status immediately observable. A missing row therefore cannot bypass serialization.

### 4.2 Lazy seeding and cutover

Activation must not clone all tables. Live sizing shows that one Thane `2026-27` clone would create 706 rows across 68 compatible tables per taluka: about 2,118 rows for the current three and about 14,120 at the allowed maximum of 20.

`ensure_owner_seeded()` in `src/core/data_scope.py` **[NEW]** lazily clones only the opened model/form/FY after verifying an included participation row:

- source: the preserved direct district structural rows;
- destination: same district plus exact `taluka_name`;
- numeric measures: zero;
- dimensions/codes: copied unchanged;
- excluded: IDs, audit timestamps, derived fields, and direct-only row subtypes;
- statement: PostgreSQL `INSERT ... SELECT ... ON CONFLICT DO NOTHING` against the owner-aware unique constraint;
- transaction: same request transaction after the shared district/FY mode lock and a fresh inclusion recheck; safe under concurrent first access and unable to seed across an exclusion/cutover commit.

The named system scope is `OWNER_SEED(model,district,taluka,fiscal_year)`: it can read only the matching direct template and insert only the exact destination owner. A central `PHYSICAL_EXACT` GET hook in `src/main.py`, driven by the route/model registry, invokes it before the registered editor opens; arbitrary reads, aggregate routes, excluded talukas, failed mutations, and direct-only subtypes never seed. The initial taluka seed does **not** copy `PostLevelDetail` children, because those rows are user-owned salary detail rather than required form dimensions; a taluka creates its own levels beneath its seeded parent.

`FISCAL_YEAR_ADMIN(fiscal_year)` may read the source FY, active management rows, and registered/auxiliary source rows; it may write only the target `FiscalYear`, the 77 registered tables, the three auxiliary FY tables, and target participation. Delete is limited to that exact FY. It cannot read or mutate users, sessions, messages, chat history, or unrelated application tables.

Migration 014 creates no participation rows. Existing FYs therefore remain direct after deployment. The safest first cutover is fiscal-year creation, which snapshots active management rows and starts their numeric source rows at zero. An in-progress-FY cutover is a deliberate selection action: the UI submits `expected_legacy_checksum`, `expected_nonzero_count`, and `acknowledge_cutover=true` after displaying the backup/checksum impact. Under the exclusive mode lock the server recomputes both values and returns 409 on mismatch. Direct values remain stored and auditable but are excluded. They are not copied, divided, or assigned to a selected taluka.

Deployment is expand-then-cutover. Migrations and new code may be rolled back while participation remains empty and no taluka-owned rows exist. After the first taluka seed, old application code is semantically unsafe because it filters only by district and would see direct plus taluka rows. Post-cutover rollback therefore means restore the verified pre-cutover database backup together with the old code, or keep the new code and roll forward; merely deleting participation rows is not a valid old-code rollback.

Deactivation is non-destructive: data, messages, chat history, and completion history remain. The taluka is excluded from the current FY while prior FY participation stays unchanged; reactivation restores its retained current-FY source data and resets only credentials. Password reset never implies budget-data deletion.

If a deselected taluka has non-zero current-FY values or completed subschemes, the selection page reports the affected form/completion counts and requires a second explicit confirmation. The operation remains allowed because it is reversible and does not delete data; silently excluding contributed data is not allowed.

### 4.3 Concurrency

- Lock order is fixed: global fiscal-year-membership lock (FY/selection operations only) → sorted district/FY mode lock(s) → district selection row → sorted user IDs → exact budget row. Budget writes take only the shared mode lock then exact row. Selection updates use the exclusive mode lock, revalidate the displayed direct-row checksum/non-zero/completion impact inside it, and serialize on the district selection row. No retry occurs for validation, lock-timeout, or uniqueness failures. A transaction deadlock/serialization failure may be retried once with 50–150 ms jitter around the whole selection transaction; all other errors return a deterministic failure.
- Writes to different taluka rows do not contend because uniqueness includes `taluka_name`.
- Update/delete locks the exact physical row. Cross-owner IDs are filtered by the scoped session before lookup and return 404.
- Effective aggregate queries run as one SQL statement wherever possible, giving one PostgreSQL statement snapshot. Before dispatching CPU work, Excel export captures an immutable verified scope/FY. The worker creates and closes its own scoped SQLAlchemy session—request sessions are never shared across threads—and opens one read-only `REPEATABLE READ` transaction so all workbook sheets use one participation/data snapshot.
- Selection revision increments exactly once per committed current-FY membership/cutover change and is included with the FY in scope fingerprints. A DCO fingerprint is a stable digest over every ordered `(district,FY,mode,selection_revision)` tuple in its requested scope, not one district's revision.

### 4.4 Caching

Correctness precedes caching for mutable budget data.

- Disable the `ttl_cache` result cache for DB-backed budget summaries and chatbot result rows. Its current key includes a `Session` string at `src/utils_cache.py:171-185`, making hits unreliable, and invalidation is already broken.
- Retain only static/schema/FY caches: `schema:{subscheme}:{schema_version}` TTL 3600 s; `fy:list` and `fy:default` TTL 300 s; training metadata TTL 300 s but responses are `private, no-store`.
- Classifier/SQL-plan cache key: `chat-plan:{subscheme}:{fy}:{scope_fingerprint}:{normalized_question_hash}` TTL 300 s. It stores no result rows/answer text.
- Invalidation is exact: registry/schema-version change makes old `schema:*` keys unreachable; fiscal-year create/update/delete clears `fy:list` and `fy:default`; participation change increments `selection_revision`, changing `scope_fingerprint` and therefore the chat-plan key. Budget mutations require no plan-cache invalidation because plans contain neither result rows nor answer text.
- If the in-process cache fails, static/schema/FY/plan callers recompute from PostgreSQL/code and do not retry; cache failure never widens scope or fails a budget mutation.
- Completion cache is removed initially; its indexed query is cheap and membership-sensitive.
- No cross-process invalidation claim is made. If shared caching is later introduced, that is a separate production-infrastructure TDD.
- All authenticated API/UI GET responses become `private, no-store`; current public API caching at `src/main.py:464-473` is unsafe for user-scoped data.

### 4.5 Failure handling

| Failure | Required behavior |
|---|---|
| PostgreSQL unavailable | rollback; 503 for auth/read dependencies and generic 500/503 UI; never fall back to unscoped data or stale cached result |
| Lazy seed constraint race | `ON CONFLICT DO NOTHING`, then re-read exact scope |
| Aggregation registry missing/invalid | fail closed, 500 with stable public message; ERROR log includes model/subscheme/FY, never row values |
| Rate/attribute conflict | successful read with `mixed` marker and owner drill-down; warning count logged; no arbitrary value |
| Notification/SMTP failure | committed activation remains valid; WARNING log and UI success with “notification pending/failed”; no rollback |
| OpenAI/LLM failure | safe chatbot unavailable/fallback response; no retry that broadens scope |
| Generated SQL fails validation | one regeneration attempt with validator feedback; then safe refusal; never execute unscoped SQL |
| Export generation failure | rollback read transaction, remove partial temp output, ERROR with scope fingerprint/export type |

### 4.6 Idempotency

- Reposting the same selected set is a no-op only after participation already exists. If active management rows predate migration 014 but participation is absent, the first same-set save is a real acknowledged cutover: it creates participation and increments revision without resetting already-active credentials.
- Inactive-to-active resets each role password once and revokes prior sessions once.
- Lazy seed is idempotent through the database natural constraint and `ON CONFLICT DO NOTHING`.
- Replace completion toggle with explicit `PUT {"is_complete": true|false}`; setting the same desired state is a no-op. This is the idempotency strategy for completion.
- Selection submits a desired canonical set, password reset is tied to a locked inactive→active transition, lazy create uses the owner-aware natural key, and updates set explicit values. These state-based keys make a generic idempotency-key table unnecessary for the current synchronous local UI.

---

## 5. SECURITY & OBSERVABILITY

### 5.1 Input validation

- Username: trim; ASCII `[A-Za-z0-9_.-]`; 3–50 characters, matching `src/routers/auth.py:27-38`. Apply the same rule to taluka credential editing; reject rather than truncate.
- Password: 8–72 UTF-8 bytes for bcrypt; no truncation. Defaults in `logincredentials.txt` satisfy this. Never return, prefill, email, audit, or log plaintext/hash.
- District: exact member of `DISTRICTS` in `src/config.py`; DCO Staff handled as its dedicated identifier.
- Taluka: exact member of the parent list in `src/utils_taluka.py:12-29`, maximum 100 characters, and exact active management row for budget access.
- Selection: deduplicated set, maximum 20 after deduplication, with no minimum-three gate because the requested one/two-taluka workflow must work. With no existing participation, an empty set is a direct-mode no-op and a set of 1–20 is an acknowledged first cutover. After cutover, 0–20 is valid; zero produces an explicit all-excluded/pending state and never restores direct rows.
- Fiscal year: existing `YYYY-YY` validator and database lookup; the request scope resolves one authorized FY before the mode lock. A legacy payload FY may remain for compatibility only when it exactly matches that resolved value and is then server-overwritten; selection lifecycle itself always targets the uncached current FY.
- Numeric budget fields: existing non-negative Pydantic/DB checks; owner is server-only. Existing schemas may continue accepting `district` for compatibility, but it must equal the authoritative principal and is always overwritten before persistence; no client field chooses an owner.
- Chat question: preserve current 2,000-character bound. SQLGlot parses exactly one PostgreSQL `SELECT`; reject CTE, UNION/set operations, subqueries, comments, multi-statements, DML/DDL, any generated `taluka_name`/session predicate, unregistered tables/columns/metrics, and joins outside an explicit registry entry. Requested district/FY filters are allowed only as typed dimensions and are intersected with the authoritative scope; an out-of-scope request is refused, never broadened. Limit is clamped to `1..100` before compilation.

### 5.2 Authentication and authorization

`src/security/session_service.py` **[NEW]** creates 256-bit random opaque session tokens with `secrets.token_urlsafe`, stores only SHA-256 token hashes, and sets one `HttpOnly`, `SameSite=Lax`, production-`Secure` cookie. Session lifetime is 12 hours absolute; no sliding extension.

`src/main.py` middleware resolves token → unrevoked/unexpired session → active `User` or existing `AdminUser`, then puts an immutable typed principal on `request.state`. `src/utils_auth.py` reads that state. Display cookies may temporarily remain for client rendering but never authorize a server operation, including `/admin`.

For a taluka user, principal resolution joins the user ID to the role-specific management column (`officer1_user_id`, `officer2_user_id`, or `assistant_user_id`) and revalidates `level='taluka'`, the expected role, exact `User.unit == TalukaUserManagement.taluka_name`, and active management/user state. The unit value is never reconstructed with a new delimiter: `src/utils_taluka.py:12-29` and `src/utils_taluka_user_management.py:31-33,79` are the canonical producer/storage path (currently `"{district} Taluka {taluka}"`). Preflight rejects swapped roles, reused IDs, cross-unit links, missing links, and one user linked to multiple management rows. Username/unit cookies are never used to locate the management row. FY participation is deliberately absent from session authentication; budget, completion, export, and chatbot `DataScope` resolution checks participation for the requested FY so an authenticated user may still reach password/settings/messages while excluded from budget data.

Taluka selection/credential lifecycle endpoints require an active `level='district', role='assistant', unit=<that district>` principal; district officers, taluka principals, another district, and display-cookie-only requests are denied. This preserves the existing product ownership of the “Taluka Nivda” page while replacing its trust source.

State-changing form/API requests require the session CSRF token in a hidden field or `X-CSRF-Token`; login is protected by SameSite plus origin validation. CORS allows the configured origins only and permits the CSRF header.

New/reactivated taluka users can authenticate with the documented default, but `must_change_password` restricts them to change-password/logout until they choose a non-default password. Login, reset, password change, and deactivation lock affected user rows before validating/changing password state and issuing/revoking sessions, preventing a concurrent login from creating a surviving session after revocation. Self-change verifies the current password, rejects every documented role default, clears the flag, revokes old sessions, and issues one replacement session atomically. Admin reset uses a fresh hash, applies the same 8–72 UTF-8-byte bound, sets `must_change_password`, and revokes sessions; username-only edits do not reset a password.

Every owned ORM class is enumerated from `src/core/budget_data_registry.py`; the design does not assume a shared inheritance marker because several simple models inherit `Base` directly. SQLAlchemy session events, anchored to `src/database.py:25-66`, enforce the resolved scope centrally:

- `do_orm_execute` adds exact/effective-source criteria to ORM `SELECT`, `UPDATE`, and `DELETE`, including aliases and known bulk `Query.update()` paths;
- `before_flush` server-derives `district`/`taluka_name` for new rows and rejects changes to either ownership field on persistent rows;
- aggregate/DCO principals cannot mutate owned models; explicit named system scopes are operation-limited;
- sessions without an explicit principal/system scope fail closed for every owned-model read or write.

The final custom scoped `Session` rejects legacy `bulk_save_objects`, `bulk_insert_mappings`, and `bulk_update_mappings` for registered owned models. That rejection is enabled only in Phase 20.6, after every current helper is converted in Phases 20.1–20.5; Phase 16.2 inventories and instruments the temporary compatibility surface without breaking intermediate builds. `do_orm_execute` rejects Core/text INSERT/UPDATE/DELETE targeting owned tables unless the operation is the exact `OWNER_SEED(...)` or `FISCAL_YEAR_ADMIN(fiscal_year)` scope. No event hook is claimed to secure APIs that bypass ORM flush events.

The same session boundary provides the canonical strict audit for every registered owned mutation: `before_flush` adds a redacted audit row for normal ORM inserts/updates/deletes, while `do_orm_execute` records scoped statement UPDATE/DELETE metadata and affected-row count. Both use the caller transaction and audit insertion failure aborts the mutation. Existing route-local best-effort `AuditService.log_*` calls are supplemental legacy events only; swallowing one cannot replace or suppress the canonical event. The static route manifest includes every legacy `api_budget_details.py` and UI mutation route, and the closure test fails any protected mutation that can commit without one canonical same-transaction audit row.

This is necessary because duplicated scheme routes do not all delegate to `src/core/secure_crud.py`. Route checks and canonical aggregate endpoints remain defense in depth.

### 5.3 Chatbot authorization

`src/routers/api_assistant.py` loads the active DB principal and passes an immutable scope to `src/chatbot/main.py`. Both fast and LLM paths pass through the same sequence:

1. parse one SQLGlot PostgreSQL AST and convert only the accepted subset to a typed `QueryPlan` (table, registered dimensions/metrics, filters, order, bounded limit);
2. reject generated taluka/session predicates, authorize/intersect requested district/FY dimensions, and resolve every requested metric/operator from `budget_data_registry`—the model cannot request raw `SUM` over an unregistered expression;
3. compile SQLAlchemy from a server-built effective-source subquery so district/taluka filtering happens **before** aggregation, then bind all values;
4. execute only the compiled statement in `src/chatbot/processors/query_execution.py`;
5. format only scoped rows.

Fast paths at `src/chatbot/core/query_classifier.py:62-169` no longer execute before policy and produce the same typed plan. Prompts describe ownership for SQL quality, but prompting is never the security boundary. Taluka scope is exact; district/DCO scope uses the same fiscal-year-participation predicate as ORM reads. Cache keys include the FY and scope fingerprint/revision. Golden cases cover repeated monetary expenses, filled/vacant category counts, derive-then-sum HRA, consensus/mixed rates, and labelled remarks.

### 5.4 Structured logging

Use existing Python logging configuration; no observability dependency is added.

| Level | Event/context |
|---|---|
| INFO | `taluka_selection_changed`: actor ID, district, added/removed counts, revision; no password |
| INFO | `taluka_user_reactivated`: target user ID, role, district/taluka, `password_reset=true`, sessions revoked count |
| INFO | `budget_scope_resolved`: sampled; principal ID/level, district, mode, active owner count, revision |
| INFO | `budget_aggregate_read`: scheme/subscheme/form/FY, source row count, output row count, duration ms, conflict count |
| INFO | `budget_export`: actor ID, export type, scope fingerprint, FY, row count, duration/result |
| WARNING | inactive user/session, scope denial, aggregation conflict, notification failure, generated SQL rejection |
| ERROR | DB failure, registry gap, migration orphan, export/chatbot execution failure; include correlation/session ID and exception class |

Audit events are written in the same transaction for activation, deactivation, credential reset/change, consolidation enablement, and budget mutation. `AuditService` gains a strict request-session path using its existing allowed action values (for example `UPDATE`) plus structured event metadata; protected mutations stop using asynchronous helper sessions and must roll back if strict audit insertion fails. `AuditService.serialize_values()` at `src/audit_service.py:32-47` must redact `password_hash`, session token/hash, and CSRF token globally before identity models are audited.

### 5.5 Metrics to measure

Initially emit these as structured numeric log fields; production metrics infrastructure is deferred:

- selection transaction count/failure/retry/duration;
- included talukas per district/FY and selection revision;
- session validation failures and revoked-session attempts;
- scope-denied reads/writes by level and endpoint;
- lazy-seed rows/duration/conflicts;
- aggregate source/output row count, duration, and non-additive conflicts by form;
- completion pending/complete taluka counts;
- export duration/failure/row count;
- chatbot validation rejection, fast/LLM execution duration, and zero-row rate;
- any query that attempts an unscoped owned-model session (must remain zero).

---

## 6. EXECUTION PHASES

Each phase is deliberately limited to at most three files. A phase is complete only when its verification passes and all earlier tests still pass. `BULK_BATCH`, `OWNERSHIP_TARGETS`, and `EXPORT_BATCH` values name the newly completed checkpoint, but each harness expands that checkpoint to the named files **plus every target completed in earlier phases**; `all` remains the final full manifest. A batch command therefore cannot hide a regression in an earlier rollout.

For every router/service rollout below, “exact-owner writes” also means: acquire the shared district/FY mode lock before loading the row, accept legacy `district`/`fiscal_year` fields only when they match the authoritative scope, overwrite owner/FY fields server-side, use the request transaction's strict `AuditService`, and remove any asynchronous `SessionLocal()` audit call. This shared requirement is not repeated in every file bullet.

Database-backed test commands use `tests/db_harness.py` and require `TEST_DATABASE_URL`. On PowerShell, set it once with `$env:TEST_DATABASE_URL='postgresql://<test-user>:<password>@localhost:5432/budgetmaking_taluka_test'`. The harness refuses a missing URL, a database name not ending in `_test`, or a URL equal to the application's configured `DATABASE_URL`; it applies migrations and resets only deterministic test fixtures. No test command silently loads `.env` as its database target.

### Phase 0: Safe migration and test foundation

Scope: 3 files, ~350 LOC
Verify: `python -m compileall -q src/utils_migrations.py scripts/migrate.py tests/db_harness.py`

#### [MODIFY] `src/utils_migrations.py`

- What: Accept an explicit SQLAlchemy `Engine`; serialize the runner with `pg_advisory_lock`, record SHA-256 migration checksums, reject a changed already-applied migration, apply the five-second lock timeout, and compare exact catalog definitions before/after migrations rather than names only. Remove the module-level `engine` import from `src.database` so importing this module cannot silently bind `.env`.
- Pattern: Existing transactional discovery/runner at `src/utils_migrations.py:239-332,335-420`.
- System design: one process owns the migration lock; lock timeout/schema drift fails without retry. The application does not run migrations concurrently at import.

#### [CREATE] `scripts/migrate.py`

- What: One-shot local/deployment entry point that parses `--database-url-env`, validates that environment value, constructs its own `Engine`, and injects it into the migration runner before importing application database state. It takes the migration lock, runs pending migrations, validates postconditions, and exits before application workers start. `--database-url-env TEST_DATABASE_URL` is mandatory in test verification; omission uses the explicitly configured application URL only for operator-run local/deployment migration. Explicit `--bootstrap-empty` is allowed only when catalog inspection proves no application tables exist: it imports the complete registry model set, runs `Base.metadata.create_all(bind=the_explicit_engine)` once under the lock, asserts the table manifest, then applies/validates migrations. It refuses every nonempty database; normal upgrades never call `create_all()`.
- Pattern: Delegate to the runner in `src/utils_migrations.py:260-332`; do not duplicate SQL or call `Base.metadata.create_all()`.

#### [CREATE] `tests/db_harness.py`

- What: Fail-closed `TEST_DATABASE_URL` validation, explicit empty-database bootstrap, pre-feature schema-fixture restore for upgrade tests, migration application, deterministic data fixtures, and helpers shared by every DB-backed test. Validate the test URL and set `DATABASE_URL` from it before any import of `src.database`; pass the constructed test engine explicitly to migration helpers.
- Pattern: Use the configured engine shape in `src/database.py:9-29` but never import its `.env` URL as the test target.

### Phase 0.1: Checksum schema and remove import-time mutation

Scope: 3 files, ~200 LOC
Verify: `python scripts/migrate.py --database-url-env TEST_DATABASE_URL --bootstrap-empty; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m unittest tests.test_bootstrap -v`

#### [CREATE] `migrations/core/013_add_migration_checksums.sql`

- What: Apply the exact Section 3.4 checksum-table migration; after it commits, the runner records one baseline hash for every previously applied migration and thereafter rejects drift.
- Pattern: Existing tracking table at `src/utils_migrations.py:235-249`.

#### [MODIFY] `src/main.py`

- What: Remove import-time `Base.metadata.create_all()` and `run_database_migrations()`; startup performs a read-only required-migration/checksum check and fails with an operator-facing instruction to run `python scripts/migrate.py`.
- Pattern: Replace current startup mutation at `src/main.py:569-570`.

#### [CREATE] `tests/test_bootstrap.py`

- What: Prove the test-URL guard, PostgreSQL-version guard, empty-only bootstrap/refusal on nonempty catalogs, complete model import, existing-migration checksum baseline, later drift rejection, serialized concurrent runner, exact schema checks, and that importing `src.main` performs no DDL.
- Pattern: Exercise `src/utils_migrations.py:239-332` through `scripts/migrate.py` **[NEW]**.

### Phase 1: Preflight and passing current-behavior characterization

Scope: 3 files, ~300 LOC plus normalized schema fixture
Verify: `python scripts/preflight_taluka_ownership.py --check --database-url-env TEST_DATABASE_URL --compare-schema-fixture tests/fixtures/pre_taluka_schema.sql; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m unittest tests.test_taluka_activation_contract -v`

#### [CREATE] `tests/test_taluka_activation_contract.py`

- What: Characterize only current passing invariants: new-user role defaults verify, stored hashes are nonblank bcrypt values, blank credential input means keep-current, active-save preserves a customized password, and no secret is emitted. Phase 18.1 explicitly modifies this file to enable the new reactivation/session expectations after their implementation exists.
- Pattern: Use the lifecycle at `src/utils_taluka_user_management.py:23-179` and login verification at `src/routers/auth.py:108-180`.

#### [CREATE] `scripts/preflight_taluka_ownership.py`

- What: Read-only report of PostgreSQL version, table/column/constraint/index definitions, duplicate natural keys, exact role/unit/level management-link correctness, reused/swapped/orphan IDs, password hash shape/default match counts, non-zero legacy rows, long transactions/lock blockers, auxiliary FY tables, and estimated lazy-seed fan-out. Print no hashes or secrets. Accept the same explicit `--database-url-env` selector as the migration tool so tests cannot hit `.env`; schema-fixture comparison normalizes/excludes migration-metadata tables, owners, and ACLs.
- Pattern: Follow migration discovery safety at `src/utils_migrations.py:335-420`.

#### [CREATE] `tests/fixtures/pre_taluka_schema.sql`

- What: Deterministic PostgreSQL schema-only snapshot of the pre-feature model plus the exact full relative path and checksum row for **every** migration currently applied in core, shared, and scheme migration trees (including core migration 012); strip owners, ACLs, environment names, and all business/user data. This prevents the upgrade proof from replaying legacy scheme migrations against an already materialized snapshot. It is the authoritative upgrade-test starting point, not a runtime bootstrap path.
- Pattern: Generate from the current pre-change model/database verified in Section 1 and compare catalog definitions with `scripts/preflight_taluka_ownership.py`; never hand-maintain inferred DDL.

### Phase 2: Ownership schema and core models

Scope: 3 files, ~300 LOC plus migration manifest
Verify: `python scripts/migrate.py --database-url-env TEST_DATABASE_URL; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m compileall -q src/models.py src/core/base_models.py`

#### [CREATE] `migrations/core/014_add_taluka_data_ownership.sql`

- What: Apply the exact Section 3.4 ownership/consolidation/completion migration and validate all table/FK names against the preflight inventory.
- Pattern: Transactional migration runner at `src/utils_migrations.py:260-332`.
- System design: Nullable `taluka_name` preserves old inserts; `UNIQUE NULLS NOT DISTINCT` prevents duplicate direct rows.

#### [MODIFY] `src/models.py`

- What: Map selection revision, `TalukaFiscalYearParticipation`, completion `taluka_name`, and the owner-aware completion constraint exactly to migration 014.
- Pattern: Existing selection/management/completion models at `src/models.py:63-87,207-220`.

#### [MODIFY] `src/core/base_models.py`

- What: Add nullable `taluka_name` to `SchemeModelMixin` without renaming `district` or fiscal-year fields.
- Pattern: `SchemeModelMixin` at `src/core/base_models.py:6-23`.

### Phase 2.1: Ownership migration upgrade proof

Scope: 1 file, ~140 LOC
Verify: `python -m unittest tests.test_bootstrap -v`

#### [MODIFY] `tests/test_bootstrap.py`

- What: Restore `tests/fixtures/pre_taluka_schema.sql`, apply migrations 013–014 through the serialized runner, and assert exact owner columns/constraints/FKs, zero participation rows, preserved direct-row checksums, no duplicate NULL owner, and a legacy-shaped raw insert that omits `taluka_name`.
- Pattern: Use the Phase 0 harness and exact Section 3.4 migration postconditions.

### Phase 3: Four-table metadata batch A

Scope: 3 files, ~30 LOC
Verify: `python -m compileall -q src/schemes/s2053/subs/s20530019 src/schemes/s2053/subs/s20530028 src/schemes/s2053/subs/s20530153`

#### [MODIFY] `src/schemes/s2053/subs/s20530019/models.py`

- What: Add `taluka_name` to all four natural constraints with PostgreSQL NULL-equality metadata.
- Pattern: Four-table constraints at `src/schemes/s2053/subs/s20530019/models.py:28-104`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/models.py`

- What: Add `taluka_name` to all four natural constraints with PostgreSQL NULL-equality metadata.
- Pattern: Four-table constraints at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2053/subs/s20530153/models.py`

- What: Add `taluka_name` to all four natural constraints with PostgreSQL NULL-equality metadata.
- Pattern: Representative constraints at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

### Phase 4: Four-table metadata batch B

Scope: 3 files, ~30 LOC
Verify: `python -m compileall -q src/schemes/s2053/subs/s20530162 src/schemes/s2053/subs/s20530233 src/schemes/s2053/subs/s20530242`

#### [MODIFY] `src/schemes/s2053/subs/s20530162/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2053/subs/s20530233/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2053/subs/s20530242/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

### Phase 5: Four-table metadata batch C

Scope: 3 files, ~30 LOC
Verify: `python -m compileall -q src/schemes/s2053/subs/s20530304 src/schemes/s2053/subs/s20530313 src/schemes/s2053/subs/s20530378`

#### [MODIFY] `src/schemes/s2053/subs/s20530304/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2053/subs/s20530313/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2053/subs/s20530378/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

### Phase 6: Four-table metadata batch D

Scope: 3 files, ~30 LOC
Verify: `python -m compileall -q src/schemes/s2053/subs/s20530387 src/schemes/s2029/subs/s20290037 src/schemes/s2029/subs/s20290046`

#### [MODIFY] `src/schemes/s2053/subs/s20530387/models.py`

- What: Add schema/constraint parity while marking all four models direct-only in the registry; never create a non-null owner row.
- Pattern: Existing four-table constraints at `src/schemes/s2053/subs/s20530387/models.py:28-104` and DCO identifier at `src/config.py:13-21`.

#### [MODIFY] `src/schemes/s2029/subs/s20290037/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2029/subs/s20290046/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

### Phase 7: Four-table metadata batch E

Scope: 3 files, ~30 LOC
Verify: `python -m compileall -q src/schemes/s2029/subs/s20290182 src/schemes/s2029/subs/s20290262 src/schemes/s2045/subs/s20450091`

#### [MODIFY] `src/schemes/s2029/subs/s20290182/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2029/subs/s20290262/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

#### [MODIFY] `src/schemes/s2045/subs/s20450091/models.py`

- What: Add owner-aware natural constraints to the four forms.
- Pattern: Use the verified four-table constraint pattern at `src/schemes/s2053/subs/s20530028/models.py:28-104`.

### Phase 8: Simple metadata batch A

Scope: 3 files, ~45 LOC
Verify: `python -m compileall -q src/schemes/s2045/common/district_expenditure src/schemes/s2235/subs/s22350311 src/schemes/s2235/subs/s22350338`

#### [MODIFY] `src/schemes/s2045/common/district_expenditure/base_models.py`

- What: Add the ownership column and owner-aware natural constraint to the factory, covering 20450182/20450251/20450262.
- Pattern: Factory constraint/model dictionary at `src/schemes/s2045/common/district_expenditure/base_models.py:31-66`.

#### [MODIFY] `src/schemes/s2235/subs/s22350311/models.py`

- What: Add the ownership column and owner-aware simple natural key.
- Pattern: Existing constraint at `src/schemes/s2235/subs/s22350311/models.py:25-37`.

#### [MODIFY] `src/schemes/s2235/subs/s22350338/models.py`

- What: Add the ownership column and owner-aware simple natural key.
- Pattern: Use the sibling constraint at `src/schemes/s2235/subs/s22350311/models.py:25-37`.

### Phase 9: Simple metadata batch B

Scope: 3 files, ~40 LOC
Verify: `python -m compileall -q src/schemes/s2235/subs/s22353195 src/schemes/s2235/subs/s22353408 src/schemes/s7610/subs/s76100149`

#### [MODIFY] `src/schemes/s2235/subs/s22353195/models.py`

- What: Add `taluka_name` to the simple model and natural key.
- Pattern: Use the explicit 2235 constraint at `src/schemes/s2235/subs/s22350311/models.py:25-37`.

#### [MODIFY] `src/schemes/s2235/subs/s22353408/models.py`

- What: Add `taluka_name` to the simple model and natural key.
- Pattern: Use the explicit 2235 constraint at `src/schemes/s2235/subs/s22350311/models.py:25-37`.

#### [MODIFY] `src/schemes/s7610/subs/s76100149/models.py`

- What: Add `taluka_name` to the simple model and natural key.
- Pattern: Existing natural constraint at `src/schemes/s7610/subs/s76100149/models.py:28-40`.

### Phase 10: Simple metadata batch C

Scope: 3 files, ~40 LOC
Verify: `python -m compileall -q src/schemes/s7610/subs/s76100158 src/schemes/s7610/subs/s76100167 src/schemes/s7610/subs/s76101871`

#### [MODIFY] `src/schemes/s7610/subs/s76100158/models.py`

- What: Add `taluka_name` to the simple model and natural key.
- Pattern: Use the sibling constraint at `src/schemes/s7610/subs/s76100149/models.py:28-40`.

#### [MODIFY] `src/schemes/s7610/subs/s76100167/models.py`

- What: Add `taluka_name` to the simple model and natural key.
- Pattern: Use the sibling constraint at `src/schemes/s7610/subs/s76100149/models.py:28-40`.

#### [MODIFY] `src/schemes/s7610/subs/s76101871/models.py`

- What: Add `taluka_name` to the simple model and natural key.
- Pattern: Use the sibling constraint at `src/schemes/s7610/subs/s76100149/models.py:28-40`.

### Phase 11: Simple metadata batch D

Scope: 3 files, ~40 LOC
Verify: `python -m compileall -q src/schemes/s6245/subs/s62450017 src/schemes/s6401/subs/s64010018 src/schemes/s2075`

#### [MODIFY] `src/schemes/s6245/subs/s62450017/models.py`

- What: Add `taluka_name` to the loan model and natural key.
- Pattern: Existing constraint at `src/schemes/s6245/subs/s62450017/models.py:28-40`.

#### [MODIFY] `src/schemes/s6401/subs/s64010018/models.py`

- What: Add `taluka_name` to the loan model and natural key.
- Pattern: Existing constraint at `src/schemes/s6401/subs/s64010018/models.py:28-40`.

#### [MODIFY] `src/schemes/s2075/models.py`

- What: Add ownership only to district-keyed classes; leave DCO-only `SubHeadExpenditure2075` unchanged.
- Pattern: The two distinct s2075 classes are documented at `src/schemes/s2075/models.py:13-71`.

### Phase 12: Section metadata batch

Scope: 3 files, ~45 LOC
Verify: `python -m compileall -q src/schemes/s0029/subs/s0029 src/schemes/s2215/subs/s2215 src/schemes/s2245/subs/s2245`

#### [MODIFY] `src/schemes/s0029/subs/s0029/models.py`

- What: Add ownership after the existing section natural dimension.
- Pattern: Existing section key at `src/schemes/s0029/subs/s0029/models.py:27-40`.

#### [MODIFY] `src/schemes/s2215/subs/s2215/models.py`

- What: Add ownership after the existing account-head natural dimension.
- Pattern: Existing account-head key at `src/schemes/s2215/subs/s2215/models.py:40-53`.

#### [MODIFY] `src/schemes/s2245/subs/s2245/models.py`

- What: Add ownership after each existing section/account-head natural dimension. Mark s2245 special direct-only row types in the later registry rather than inferring parents from composite labels.
- Pattern: Natural keys at `src/schemes/s0029/subs/s0029/models.py:27-40`, `src/schemes/s2215/subs/s2215/models.py:40-53`, and `src/schemes/s2245/subs/s2245/models.py:29-42`.

### Phase 12.1: Fresh ownership-schema bootstrap equivalence

Scope: 1 file, ~100 LOC
Verify: `python -m unittest tests.test_bootstrap -v`

#### [MODIFY] `tests/test_bootstrap.py`

- What: After every ownership model constraint is mapped, bootstrap an empty test database explicitly and compare the complete migration-014 ownership/participation/completion catalog with the upgraded pre-feature fixture catalog.
- Pattern: Use catalog normalization/assertions from Phase 2.1; differences in column type/nullability, natural-key order, NULL semantics, FK action, or index predicate fail.

### Phase 13: Scope and registry foundation

Scope: 3 files, ~650 LOC
Verify: `python -m unittest tests.test_data_scope_contract -v`

#### [CREATE] `src/core/data_scope.py`

- What: Immutable principal/read scope, exact management-ID principal resolution, fiscal-year-participation SQLAlchemy expressions, shared/exclusive district/FY mode-lock helpers, exact-owner write checks, the named `OWNER_SEED`/`FISCAL_YEAR_ADMIN` scopes, central physical-GET seeding contract, and scope fingerprint/revision.
- Pattern: Replace helpers in `src/utils_district.py:10-109`; use `with_for_update` pattern from `src/routers/completion_status.py:107-135`.
- System design: fail closed without scope; `ON CONFLICT DO NOTHING`; no result cache.

#### [CREATE] `src/core/budget_data_registry.py`

- What: Exact 77-table model registry with natural dimensions, seed fields, aggregation policies, direct-only row predicates, and every legacy route classified as `PHYSICAL_EXACT`, `AGGREGATION_SAFE`, or `CANONICAL_AGGREGATE`.
- Pattern: `BaseSchemeConfig.forms` at `src/core/base_config.py:27-49` and `get_scheme_models` at `src/utils_scheme.py:178-209`.
- System design: a missing model, field, or route classification fails closed in aggregate mode. `20530387`, Mumbai City, and s2245 physical rows where `table_section_code IN ('22450093','22452185') AND (district LIKE '%|DC' OR district LIKE '%|ZP')` can never seed or aggregate taluka rows; `SUBTOTAL`, `DIVISION`, and `GRAND_TOTAL` are virtual helper rows and are never registry/persistence owners.

#### [CREATE] `tests/test_data_scope_contract.py`

- What: Encode the direct/taluka/aggregate/DCO Staff/Mumbai City predicate matrix with explicit participation fixtures, all-excluded anti-resurrection, shared/exclusive mode locks and seed-vs-exclusion serialization, exact management-ID principal, route classification, restricted system scopes, scope fingerprints, and no direct-plus-taluka double count. Selection-route cutover behavior is enabled only in Phase 18.1.
- Pattern: Replace the parent-district behavior at `src/utils_district.py:33-94`.

### Phase 13.1: Aggregation policy contract

Scope: 1 file, ~220 LOC
Verify: `python -m unittest tests.test_aggregation_policies -v`

#### [CREATE] `tests/test_aggregation_policies.py`

- What: Verify the registry's `SUM`, filled/vacant by category/class, repeated-monetary max-per-owner-then-sum with intra-owner conflict metadata, derive-then-sum HRA, consensus/mixed, remarks drill-down, exact s2245 direct-only predicate, and registry completeness for all 77 owned tables.
- Pattern: Existing calculations at `src/schemes/s2053/subs/s20530028/ui_budget_summary.py:182-215` and export populator at `.../excel_export/populators/budget_post_details.py:96-140`.

### Phase 14: Aggregation service and consolidated UI

Scope: 3 files, ~600 LOC
Verify: `python -m unittest tests.test_data_scope_contract -v`

#### [CREATE] `src/core/aggregation.py`

- What: Build virtual read DTOs, owner drill-down, conflict metadata, pagination after grouping, and source/output counts.
- Pattern: Existing summary grouping in `src/schemes/s2053/common/services/abstract_service.py:73-148`.

#### [CREATE] `src/routers/ui_consolidated_budget.py`

- What: Registry-driven canonical HTML and JSON read-only aggregate endpoints; taluka drill-down is district/DCO-only and physical routes remain canonical for exact taluka/direct editing.
- Pattern: Scheme/template registry usage at `src/core/base_router.py:19-74`.

#### [CREATE] `templates/consolidated_budget.html`

- What: Present the same internal field keys with human labels, totals, mixed markers, and optional taluka drill-down; no aggregate edit controls or fabricated IDs.
- Pattern: Existing scheme table/template hierarchy at `docs/ARCHITECTURE.md:639-718`.

### Phase 14.1: Aggregate DTO policy verification

Scope: 1 file, ~140 LOC
Verify: `python -m unittest tests.test_aggregation_policies -v`

#### [MODIFY] `tests/test_aggregation_policies.py`

- What: Enable concrete DTO/source-row tests only now that `src/core/aggregation.py` exists, including pagination-after-grouping, mixed metadata, all-excluded empty output, and labelled remarks.
- Pattern: Exercise the policy declarations proven in Phase 13.1 through `src/core/aggregation.py` **[NEW]**.

### Phase 15: Verified session schema, mapping, and service

Scope: 3 files, ~500 LOC
Verify: `python scripts/migrate.py --database-url-env TEST_DATABASE_URL; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m compileall -q src/models.py src/security/session_service.py`

#### [CREATE] `migrations/core/015_add_verified_user_sessions.sql`

- What: Apply the exact Section 3.4 credential/session migration after exact management-link and schema-drift preflight.
- Pattern: Serialized transactional migration runner from Phase 0.

#### [MODIFY] `src/models.py`

- What: Map `User.must_change_password`, `password_changed_at`, and typed user/admin `UserSession` exactly to migration 015 before any service imports the mapping.
- Pattern: Existing `User` at `src/models.py:13-27`.

#### [CREATE] `src/security/session_service.py`

- What: Issue/hash/validate/revoke typed user/admin opaque tokens, 12-hour expiry, CSRF token, active-principal resolution, row-lock helpers, and must-change restriction.
- Pattern: Current cookie creation/deletion at `src/routers/auth.py:86-105`.
- System design: no cache/retry; one indexed DB lookup; store no raw session token.

### Phase 15A: Session migration upgrade/bootstrap proof

Scope: 1 file, ~100 LOC
Verify: `python -m unittest tests.test_bootstrap -v`

#### [MODIFY] `tests/test_bootstrap.py`

- What: Restore the pre-feature fixture and apply migrations 013–015, then compare it with explicit fresh bootstrap after final session mappings: exact user columns, management FKs/role index, `user_sessions` checks/indexes, checksum rows, and unchanged user hashes/data. Existing users remain `must_change_password=FALSE`; first-login default detection is tested at the auth layer.
- Pattern: Extend the Phase 12.1 normalized catalog comparison to migration 015.

### Phase 15.1: Session service contract

Scope: 1 file, ~260 LOC
Verify: `python -m unittest tests.test_session_auth -v`

#### [CREATE] `tests/test_session_auth.py`

- What: Test token hashing, typed principal separation, expiry/revocation, active-user checks, row-lock issuance/revocation ordering, and restricted-session state. Middleware/CSRF assertions are added only in the phases that implement them.
- Pattern: Exercise `src/security/session_service.py` **[NEW]** against the Phase 0 test harness.

### Phase 15.2: Strict transactional audit foundation

Scope: 2 files, ~180 LOC
Verify: `python -m unittest tests.test_session_auth -v`

#### [MODIFY] `src/audit_service.py`

- What: Add a caller-session strict audit API, global secret-field redaction, and structured event metadata while preserving existing allowed action values. Strict insertion errors propagate to the owning transaction; a legacy best-effort event may remain temporarily as supplemental telemetry but is never the sole/canonical audit for a protected identity or budget mutation.
- Pattern: Existing serialization/action surface at `src/audit_service.py:32-97,166-201`.

#### [MODIFY] `tests/test_session_auth.py`

- What: Prove strict audit shares the caller transaction, redacts password/session/CSRF fields, and causes rollback on insertion failure; keep notification behavior out of this test.
- Pattern: Exercise the new strict API before auth/admin/selection routes depend on it.

### Phase 16: User dual issuance and credential lifecycle

Scope: 3 files, ~500 LOC
Verify: `python -m unittest tests.test_session_auth -v`

#### [MODIFY] `src/routers/auth.py`

- What: After locked bcrypt verification, issue the opaque user session while temporarily retaining display cookies for rendering. Detect a submitted documented taluka default and atomically set must-change; implement self-change and CSRF-ready `POST /auth/logout`, reject defaults, and replace all old sessions with one new session. Remove the state-changing `GET /auth/logout`; a GET is 405 or a non-mutating redirect to the login page.
- Pattern: Current bcrypt/login flow at `src/routers/auth.py:20-180`.
- System design: a bounded per-process login limiter keys normalized username plus source address; forwarded addresses are trusted only from configured proxies. No distributed-rate-limit claim is made.

#### [CREATE] `templates/change_password.html`

- What: CSRF-ready current/new/confirm form with no default/password echo; the CSRF field is populated in Phase 16.3 through the central template context.
- Pattern: Login form/base rendering at `templates/login_base.html`.

#### [MODIFY] `tests/test_session_auth.py`

- What: Enable user login issuance, existing-active default detection, customized-password preservation, concurrent login/revocation, self-change replacement, default rejection, and change-template rendering.
- Pattern: Extend the Phase 15.1 service cases through `src/routers/auth.py` and its new template.

### Phase 16A: Admin dual issuance and credential reset

Scope: 2 files, ~260 LOC
Verify: `python -m unittest tests.test_session_auth -v`

#### [MODIFY] `src/routers/admin.py`

- What: Issue the same typed admin session while the legacy display cookie remains temporarily usable only until Phase 16.1; password updates enforce 8–72 UTF-8 bytes, fresh hashes, user row locks, must-change, session revocation, and strict audit. Username-only updates do not reset credentials.
- Pattern: Current login/guards/mutations at `src/routers/admin.py:38-99,128-179,189-301`.

#### [MODIFY] `tests/test_session_auth.py`

- What: Enable admin typed issuance, user reset, username-only-update, cross-principal token, and concurrent reset/login cases.
- Pattern: Extend the Phase 16 user-session cases through `src/routers/admin.py`.

### Phase 16.1: Authoritative session cutover and route boundary

Scope: 3 files, ~420 LOC
Verify: `python -m unittest tests.test_session_auth tests.test_data_scope_contract -v`

#### [MODIFY] `src/main.py`

- What: Resolve verified principal before UI/API auth, attach request state, enforce must-change, make authenticated responses private/no-store, register the consolidated router, and enforce registry route classification. The `PHYSICAL_EXACT` GET boundary calls exact lazy seed for an included taluka; aggregate HTML redirects, aggregate API GET returns 409 with canonical URL, aggregate mutation returns 403, and an unregistered owned-data route fails closed. CSRF enforcement remains disabled until Phase 16.4.
- Pattern: Existing middleware stack at `src/main.py:425-498,546-567`.

#### [MODIFY] `src/utils_auth.py`

- What: Read principal from request state; selected scheme/FY and display cookies remain non-authorizing preferences only.
- Pattern: Existing getter surface at `src/utils_auth.py:27-98`.

#### [MODIFY] `tests/test_session_auth.py`

- What: Enable forged user/admin display-cookie rejection, must-change route restriction, logout, and route-boundary tests now that middleware exists.
- Pattern: Replace current cookie trust at `src/utils_auth.py:27-66`.

### Phase 16.2: Central ORM scope enforcement

Scope: 2 files, ~400 LOC
Verify: `python -m unittest tests.test_data_scope_contract -v`

#### [MODIFY] `src/database.py`

- What: Attach registry-enumerated scope to request sessions; before yielding a session for any registered owned mutation, acquire the shared district/FY mode lock so duplicated handlers cannot omit it; enforce criteria for ORM SELECT/UPDATE/DELETE and aliases; derive/lock new-row ownership; reject owner changes; emit a canonical redacted same-transaction audit for flush and statement mutations; reject Core/text DML except exact named system scopes. Instrument and inventory the known legacy owned bulk APIs but defer their final rejection to Phase 20.6 so intermediate phases remain runnable.
- Pattern: Session factory/lifecycle at `src/database.py:25-66`.
- System design: missing scope fails closed; no implicit DCO/unrestricted fallback.

#### [MODIFY] `tests/test_data_scope_contract.py`

- What: Enable registered-mutation pre-handler shared-lock assertions plus direct `db.query`, `Session.execute(select/update/delete)`, bulk `Query.update`, temporary known bulk compatibility, Core/text DML, forged inserts, dirty owner changes, aliases, relationship loads, narrow system-scope cases, and canonical audit rollback. Enumerate every legacy `api_budget_details.py`/UI mutation route and prove a swallowed supplemental audit cannot permit a commit without the central strict event.
- Pattern: Exercise SQLAlchemy events through the custom session in `src/database.py`.

### Phase 16.3: Global CSRF propagation

Scope: 3 files, ~190 LOC
Verify: `python -m compileall -q src/core/templates.py; python -m unittest tests.test_session_auth -v`

#### [MODIFY] `src/core/templates.py`

- What: Inject only the current session's public CSRF token into authenticated template context; never expose session/token hashes.
- Pattern: Central render wrapper at `src/core/templates.py:1-13`.

#### [MODIFY] `templates/base.html`

- What: Add the rendered token to every non-GET same-origin form and mutating fetch request.
- Pattern: Existing form/fetch surfaces at `templates/base.html:1829-1844,1980-2133,2314-2396`.

#### [MODIFY] `templates/scheme_selection.html`

- What: Add the hidden token to this standalone authenticated POST form, which does not inherit `base.html`.
- Pattern: Existing standalone form at `templates/scheme_selection.html:414`.

### Phase 16.3A: CSRF propagation contract

Scope: 1 file, ~90 LOC
Verify: `python -m unittest tests.test_session_auth -v`

#### [MODIFY] `tests/test_session_auth.py`

- What: Render base-derived and standalone scheme-selection forms and prove their non-GET forms/fetch helpers carry only the current session's public CSRF token before enforcement is enabled.
- Pattern: Exercise all three Phase 16.3 targets.

### Phase 16.3B: Standalone admin CSRF propagation

Scope: 2 files, ~110 LOC
Verify: `python -m unittest tests.test_session_auth -v`

#### [MODIFY] `templates/admin_users.html`

- What: Add the rendered CSRF token to standalone admin update/logout fetches and preserve GET filters as read-only.
- Pattern: Current update/logout calls at `templates/admin_users.html:315-374`.

#### [MODIFY] `tests/test_session_auth.py`

- What: Render admin user management with a verified admin session and prove every mutating request carries only that session's public token.
- Pattern: Extend the Phase 16.3A propagation contract to the admin template.

### Phase 16.4: Enforce CSRF and remove mutating GET

Scope: 3 files, ~220 LOC
Verify: `python -m unittest tests.test_session_auth -v`

#### [MODIFY] `src/main.py`

- What: Enable session-token CSRF checks for every authenticated state-changing request; login uses SameSite plus exact configured-origin validation.
- Pattern: Extend Phase 16.1 middleware after every form has propagation.

#### [MODIFY] `src/routers/ui_scheme_selection.py`

- What: Convert `/clear` from state-changing GET to CSRF-protected POST; leave read-only selection GET unchanged.
- Pattern: Current cookie-mutating routes at `src/routers/ui_scheme_selection.py:83-112`.

#### [MODIFY] `tests/test_session_auth.py`

- What: Enable hidden/header CSRF success, missing/mismatch rejection before handler execution, standalone scheme-selection POST, clear-GET rejection, `GET /auth/logout` non-mutation/rejection, CSRF-protected logout POST, origin checks, and CORS-header cases.
- Pattern: Exercise the Phase 16.4 middleware and route.

### Phase 17: Uncached current-FY mutation resolver

Scope: 2 files, ~120 LOC
Verify: `python -m unittest tests.test_data_scope_contract -v`

#### [MODIFY] `src/utils_fiscal_year.py`

- What: Add `get_current_fiscal_year_for_update(db)`, which performs an uncached descending active-year query after the caller takes the shared advisory lock and fails if no active FY exists. Read-only preference helpers retain the 300-second cache.
- Pattern: Existing cached default/validation at `src/utils_fiscal_year.py:10-45`.

#### [MODIFY] `tests/test_data_scope_contract.py`

- What: Prove mutation resolution ignores stale `fy_default` cache/cookies, chooses the deterministic highest active value, and fails closed with no active FY.
- Pattern: Contrast the new mutation helper with current cached `get_default_fiscal_year` behavior.

### Phase 18: Taluka transition correctness

Scope: 3 files, ~450 LOC
Verify: `python -m unittest tests.test_data_scope_contract -v`

#### [MODIFY] `src/utils_taluka_user_management.py`

- What: Keep one role-default map matching `logincredentials.txt`; resolve management-linked users and revalidate `(level,unit,role)` using exact `User.unit == management.taluka_name`; lock IDs in ascending order; fresh-hash only on inactive→active; preserve customized username; revoke sessions; remove the shared hash cache. For the existing credential-edit utility, resolve by exact management row plus role column, enforce optional passwords at 8–72 UTF-8 bytes, fresh-hash/set must-change/revoke sessions only when a password is supplied, and preserve the password on username-only edits. No stored password may be NULL/blank.
- Pattern: Current create/activate/deactivate/sync at `src/utils_taluka_user_management.py:23-179,273-294`.
- System design: no commits, audit sessions, or notifications inside the utility; caller owns one transaction.

#### [MODIFY] `src/routers/ui_taluka_selection.py`

- What: Require the exact active district-assistant principal; use the shared FY advisory lock; call `get_current_fiscal_year_for_update`; take the exclusive district/FY mode lock; lock the district row; validate the desired 0–20 state; return an exact-state no-op before stale-revision checking, otherwise reject stale `expected_revision`; recompute/compare displayed checksum/impact; require in-progress-FY acknowledgement and non-zero/completion deselection confirmation; update only current-FY participation; increment revision once; strict-audit atomically; commit before notification; reject a historical preference cookie. Secure the existing `/update-user` endpoint by exact management ID owned by the assistant's district and exact role-column user ID; apply the same password/username semantics, row lock, session revocation, and strict audit as the utility.
- Pattern: Current one-commit route at `src/routers/ui_taluka_selection.py:157-216`.

#### [MODIFY] `src/utils_taluka.py`

- What: Remove persisted-empty-means-all, provide exact canonical membership validation, remove the minimum-three gate, and keep Mumbai City explicit no-taluka. Participation—not this map—decides consolidation.
- Pattern: Current static mapping/fallback at `src/utils_taluka.py:12-40`.

### Phase 18.1: Taluka transition contract

Scope: 2 files, ~220 LOC
Verify: `python -m unittest tests.test_taluka_activation_contract tests.test_session_auth -v`

#### [MODIFY] `tests/test_taluka_activation_contract.py`

- What: Enable inactive→active reset, active→active no-op, fresh per-user hashes, exact management-ID credential edit, 8–72-byte bound, password reset/must-change/session revocation, username-only password preservation, cross-district/role-ID rejection, 1/2/0-taluka rules, first same-set cutover, stale-revision/checksum 409, budget-write-vs-cutover serialization, historical-FY rejection, and exact role-link validation.
- Pattern: Extend Phase 1 only after the transition implementation exists.

#### [MODIFY] `tests/test_session_auth.py`

- What: Add deterministic login-vs-deactivation race coverage and prove no unrevoked session survives a committed deactivation.
- Pattern: Exercise user row locking shared by auth and transition paths.

### Phase 19: Taluka selection UX and strict sanitized audit

Scope: 3 files, ~280 LOC
Verify: `python -m unittest tests.test_taluka_activation_contract tests.test_session_auth -v`

#### [MODIFY] `templates/taluka_selection.html`

- What: Keep blank password inputs, explain reset-on-reactivation, display consolidation/cutover impact and non-zero legacy count, include CSRF/revision, and show transition result without plaintext.
- Pattern: Current selection and credential panels at `templates/taluka_selection.html:33-123`.

#### [MODIFY] `src/audit_service.py`

- What: Add the exact sanitized taluka identity/consolidation event builders on top of Phase 15.2; protected writes use the existing strict caller-session API and never a best-effort asynchronous session.
- Pattern: Serialization/action logging at `src/audit_service.py:32-97,166-201`.

#### [MODIFY] `src/notification_service.py`

- What: Send post-commit activation/deactivation notifications using immutable captured recipients; include no password and fix deactivation notification suppression after the user becomes inactive.
- Pattern: Taluka alerts at `src/notification_service.py:221-339`.

### Phase 19.1: Secret/audit failure contract

Scope: 1 file, ~100 LOC
Verify: `python -m unittest tests.test_taluka_activation_contract -v`

#### [MODIFY] `tests/test_taluka_activation_contract.py`

- What: Enable log/audit/notification secret-leak assertions and prove strict audit failure rolls back the protected transition while post-commit notification failure does not.
- Pattern: Exercise the three Phase 19 targets together.

### Phase 20: Central CRUD scope and write ownership

Scope: 3 files, ~400 LOC
Verify: `python -m unittest tests.test_data_scope_contract -v`

#### [MODIFY] `src/utils_district.py`

- What: Delegate principal, district, edit, and predicate decisions to `src/core/data_scope.py`; preserve compatible function names only as thin adapters and delete taluka→shared-district write authorization.
- Pattern: Replace current collapse at `src/utils_district.py:33-109`.

#### [MODIFY] `src/core/secure_crud.py`

- What: Server-derive/validate district and taluka owner, exact-owner ID lookup, call the named lazy seed only for a registered physical GET, aggregate list response for aggregate principals, read-only derived mode, and same-session strict audit/commit.
- Pattern: Existing secured factory at `src/core/secure_crud.py:89-180`.

#### [MODIFY] `src/core/base_router.py`

- What: Apply the same principal/scope checks or delegate all active use to `secure_crud`; do not leave an unscoped future factory.
- Pattern: Current unscoped endpoints at `src/core/base_router.py:36-154`.

### Phase 20.0: Bulk-write bypass test harness

Scope: 1 file, ~150 LOC
Verify: `python -m unittest tests.test_bulk_write_scope -v`

#### [CREATE] `tests/test_bulk_write_scope.py`

- What: Explicitly inventory every current owned `bulk_save_objects` helper. Before conversion, prove only the frozen known-site compatibility path remains observable and scope-bound while unknown/no-scope legacy bulk plus owned Core/text bypasses fail closed. `BULK_BATCH` checkpoints later include converted helper groups cumulatively; final bulk-API rejection is intentionally deferred to Phase 20.6.
- Pattern: Use the exact `rg -l "bulk_save_objects" src` inventory and custom session from Phase 16.2.

### Phase 20.1: Remove legacy bulk seed bypass A

Scope: 3 files, ~180 LOC
Verify: `$env:BULK_BATCH='20.1'; python -m unittest tests.test_bulk_write_scope -v`

#### [MODIFY] `src/schemes/s0029/subs/s0029/helpers.py`

- What: Replace `bulk_save_objects` with owner-safe ORM/Core inserts; physical taluka seeding delegates to `OWNER_SEED`, direct/FY structural work requires `FISCAL_YEAR_ADMIN`.
- Pattern: Existing seed helper and Section 4.2 owner-seed contract.

#### [MODIFY] `src/schemes/s2215/subs/s2215/helpers.py`

- What: Apply the identical narrow-scope replacement while preserving account-head dimensions.
- Pattern: Existing helper plus registry dimensions from `src/schemes/s2215/subs/s2215/models.py:40-53`.

#### [MODIFY] `src/schemes/s2245/subs/s2245/helpers.py`

- What: Replace bulk inserts and enforce the exact section-3 DC/ZP direct-only predicate; virtual subtotal/division rows are never inserted as taluka owners.
- Pattern: Current physical key builder at `src/schemes/s2245/subs/s2245/helpers.py:36-71`.

### Phase 20.2: Remove legacy bulk seed bypass B

Scope: 3 files, ~150 LOC
Verify: `$env:BULK_BATCH='20.2'; python -m unittest tests.test_bulk_write_scope -v`

#### [MODIFY] `src/schemes/s2235/subs/s22350311/helpers.py`
- What: Replace owned `bulk_save_objects` with narrow-scope inserts preserving natural dimensions.
- Pattern: Use the central registry/seed contract from Phase 13.

#### [MODIFY] `src/schemes/s2235/subs/s22350338/helpers.py`
- What: Apply the proven 22350311 seed boundary.
- Pattern: Sibling helper above.

#### [MODIFY] `src/schemes/s2235/subs/s22353195/helpers.py`
- What: Apply the proven 22350311 seed boundary.
- Pattern: Sibling helper above.

### Phase 20.3: Remove legacy bulk seed bypass C

Scope: 3 files, ~150 LOC
Verify: `$env:BULK_BATCH='20.3'; python -m unittest tests.test_bulk_write_scope -v`

#### [MODIFY] `src/schemes/s2235/subs/s22353408/helpers.py`
- What: Complete the 2235 owner-safe seed conversion.
- Pattern: Phase 20.2 sibling helpers.

#### [MODIFY] `src/schemes/s7610/subs/s76100149/helpers.py`
- What: Replace owned bulk insertion with narrow-scope inserts preserving loan dimensions.
- Pattern: Registry seed fields from Phase 13.

#### [MODIFY] `src/schemes/s7610/subs/s76100158/helpers.py`
- What: Apply the 76100149 seed boundary.
- Pattern: Sibling helper above.

### Phase 20.4: Remove legacy bulk seed bypass D

Scope: 3 files, ~150 LOC
Verify: `$env:BULK_BATCH='20.4'; python -m unittest tests.test_bulk_write_scope -v`

#### [MODIFY] `src/schemes/s7610/subs/s76100167/helpers.py`
- What: Complete owner-safe seed conversion for this 7610 sibling.
- Pattern: Phase 20.3 7610 helper.

#### [MODIFY] `src/schemes/s7610/subs/s76101871/helpers.py`
- What: Complete owner-safe seed conversion for this 7610 sibling.
- Pattern: Phase 20.3 7610 helper.

#### [MODIFY] `src/schemes/s6245/subs/s62450017/helpers.py`
- What: Replace loan-table bulk seed with narrow-scope inserts.
- Pattern: Registry natural key in `src/schemes/s6245/subs/s62450017/models.py:28-40`.

### Phase 20.5: Remove remaining legacy bulk seed bypasses

Scope: 2 files, ~140 LOC
Verify: `$env:BULK_BATCH='20.5'; python -m unittest tests.test_bulk_write_scope -v`

#### [MODIFY] `src/schemes/s6401/subs/s64010018/helpers.py`
- What: Replace loan-table bulk seed with narrow-scope inserts.
- Pattern: Sibling 6245 conversion from Phase 20.4.

#### [MODIFY] `src/schemes/s2045/common/district_expenditure/base_helpers.py`
- What: Replace the factory's bulk path and asynchronous audit session with scoped insert plus same-session strict audit.
- Pattern: Existing common helper architecture at `docs/ARCHITECTURE.md:419-461`.

### Phase 20.6: Bulk-write closure and enforcement

Scope: 2 files, ~240 LOC
Verify: `$env:BULK_BATCH='all'; python -m unittest tests.test_bulk_write_scope -v`

#### [MODIFY] `src/database.py`

- What: Remove the temporary known-site bulk compatibility path and enable unconditional rejection of owned `bulk_save_objects`, `bulk_insert_mappings`, and `bulk_update_mappings`; retain the strict canonical audit and named system scopes from Phase 16.2.
- Pattern: Close the explicitly instrumented compatibility boundary introduced in Phase 16.2 only after the static helper inventory is empty.

#### [MODIFY] `tests/test_bulk_write_scope.py`

- What: Enable `BULK_BATCH=all`: enumerate every former site, prove exact direct/taluka/FY ownership, reject each forbidden bulk/Core/text bypass, and statically assert zero owned `bulk_save_objects` calls remain.
- Pattern: Drive the registry and the custom session from Phases 13 and 16.2; do not depend on wildcard route discovery.

### Phase 21: s20530028 vertical slice

Scope: 3 files, ~350 LOC
Verify: `python -m unittest tests.test_s20530028_ownership -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/budget_post_details/repositories/budget_post_repository.py`

- What: Exact scoped physical reads/writes and no internal commit.
- Pattern: Existing layered repository structure documented at `docs/ARCHITECTURE.md:211-361`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/budget_post_details/services/budget_post_service.py`

- What: Lazy owner seeding, exact-owner mutation, virtual aggregate service call, and post-level limit checks on physical source only.
- Pattern: Current update flow at `src/schemes/s2053/subs/s20530028/budget_post_details/services/budget_post_service.py:130-227`.

#### [CREATE] `tests/test_s20530028_ownership.py`

- What: Test only the repository/service slice implemented in this phase: parent exact-owner load/update, lazy seed, read-only aggregate DTO, derive-then-sum HRA, split post-expense policies, and no legacy double count. Controller/post-level/export assertions are enabled in their later phases.
- Pattern: Exercise the representative layered flow documented at `docs/ARCHITECTURE.md:211-361` and calculations at `src/schemes/s2053/subs/s20530028/ui_budget_summary.py:182-215`.

### Phase 22: s20530028 controller surface

Scope: 3 files, ~320 LOC
Verify: `python -m unittest tests.test_s20530028_ownership -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py`

- What: Use authoritative scope, block derived writes, and route aggregate users to the consolidated view. Preserve existing export behavior at this phase; worker/session changes are deferred to Phase 37 after the common export boundary exists.
- Pattern: Existing list/edit paths at `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py:73-123,293-303`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/api_controller.py`

- What: Use the authoritative principal, exact-owner mutations, and canonical aggregate JSON endpoint.
- Pattern: Follow the secured controller/service boundary in `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py:73-123,293-303`.

#### [MODIFY] `tests/test_s20530028_ownership.py`

- What: Enable physical/aggregate UI and API controller cases, including aggregate mutation denial and canonical redirect/409 behavior.
- Pattern: Extend the Phase 21 service contract through both modified controllers.

### Phase 23: Post-level ownership and transaction repair

Scope: 3 files, ~420 LOC
Verify: `python -m unittest tests.test_s20530028_ownership -v`

#### [MODIFY] `src/schemes/common/post_levels/api_router.py`

- What: Validate parent ownership on every endpoint, including currently unchecked aggregates at `:355-380`; derived projections are read-only and have no fake ID.
- Pattern: Existing access callback at `src/schemes/common/post_levels/api_router.py:45-77,114-180`.

#### [MODIFY] `src/schemes/common/post_levels/repository.py`

- What: Remove internal commits, require parent physical budget-post scope for every get/update/delete/count/reorder.
- Pattern: Current repository at `src/schemes/common/post_levels/repository.py:15-188`.

#### [MODIFY] `src/schemes/common/post_levels/service.py`

- What: Owner-safe projection and apply-aggregate only to physical source parent.
- Pattern: Calculation/apply flow at `src/schemes/common/post_levels/service.py:182-294`.

### Phase 23.1: Post-level ownership contract

Scope: 1 file, ~120 LOC
Verify: `python -m unittest tests.test_s20530028_ownership -v`

#### [MODIFY] `tests/test_s20530028_ownership.py`

- What: Enable parent isolation for every child endpoint, no taluka child cloning on first seed, level-limit/reorder transaction rollback, derived read-only projection, and no fabricated aggregate child ID.
- Pattern: Exercise all three Phase 23 files only after their transaction repair exists.

### Phase 24: Shared lightweight scheme factory

Scope: 3 files, ~350 LOC
Verify: `python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s2045/common/district_expenditure/base_router.py`

- What: Apply scope-aware direct/taluka/aggregate lists and exact-owner writes to the three factory-backed schemes; fix the existing API PUT no-op while touching this path.
- Pattern: Common-layer route factory at `src/schemes/s2045/common/district_expenditure/base_router.py:157-225,312-355`.

#### [MODIFY] `src/schemes/s2045/common/district_expenditure/base_helpers.py`

- What: Scope-aware direct/taluka/aggregate lists and exact-owner writes for 20450182/20450251/20450262; lazy seed and no asynchronous audit with an unscoped session.
- Pattern: Common-layer architecture at `docs/ARCHITECTURE.md:419-461`.

#### [CREATE] `tests/test_simple_scheme_ownership.py`

- What: Reusable conformance suite parameterized over explicit `OWNERSHIP_TARGETS`; with no variable it tests only the three completed factory tables, and `OWNERSHIP_TARGETS=all` is enabled only after all rollouts. Each rollout command names only fully implemented targets.
- Pattern: Parameterize from the 17-table registry in `src/core/budget_data_registry.py` **[NEW]** and representative CRUD at `src/schemes/s2235/subs/s22350311/router_ui.py:34-317`.

### Phase 25: Simple scheme rollout A

Scope: 3 files, ~350 LOC
Verify: `python -m compileall -q src/schemes/s2075/router_api.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; $env:OWNERSHIP_TARGETS='0029'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s0029/subs/s0029/router_ui.py`

- What: Route aggregate reads through the shared projection and make direct/taluka writes exact-owner only.
- Pattern: Current direct district UI filters at `src/schemes/s0029/subs/s0029/router_ui.py:47-138,256-344`.

#### [MODIFY] `src/schemes/s0029/subs/s0029/router_api.py`

- What: Enforce the same owner/source contract for JSON reads and mutations; ignore client ownership fields.
- Pattern: Mirror the verified UI scope boundary at `src/schemes/s0029/subs/s0029/router_ui.py:47-138,256-344`.

#### [MODIFY] `src/schemes/s2075/router_api.py`

- What: Shared scope/aggregation, owner-safe mutation, and correct direct-only 20750249 behavior.
- Pattern: Current direct district filters at `src/schemes/s0029/subs/s0029/router_ui.py:47-138,256-344` and `src/schemes/s2075/router_api.py:103-105`.

### Phase 26: Simple scheme rollout B

Scope: 3 files, ~350 LOC
Verify: `$env:OWNERSHIP_TARGETS='2075,2215'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s2075/router_ui.py`

- What: Aggregate only district sub-scheme 20750294; preserve sub-head 20750249 as DCO/direct and enforce exact-owner mutations.
- Pattern: Current split UI flows at `src/schemes/s2075/router_ui.py:78-117,209-241,300-346`.

#### [MODIFY] `src/schemes/s2215/subs/s2215/router_ui.py`

- What: Add aggregate/direct UI behavior and exact-owner writes by account head.
- Pattern: Current routes at `src/schemes/s2215/subs/s2215/router_ui.py:43-108,133-198,266-340`.

#### [MODIFY] `src/schemes/s2215/subs/s2215/router_api.py`

- What: Aggregate/direct UI behavior and exact-owner writes.
- Pattern: Representative routes at `src/schemes/s2215/subs/s2215/router_ui.py:43-108,133-198,266-340`.

### Phase 27: Simple scheme rollout C

Scope: 3 files, ~400 LOC
Verify: `python -m compileall -q src/schemes/s2235/subs/s22350311/router_ui.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; $env:OWNERSHIP_TARGETS='2245'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s2245/subs/s2245/router_ui.py`

- What: Route normal district sections through the owner-aware projection while keeping special composite/DC/ZP rows direct-only.
- Pattern: Existing section branches at `src/schemes/s2245/subs/s2245/router_ui.py:40-114,278-437,480-635`.

#### [MODIFY] `src/schemes/s2245/subs/s2245/router_api.py`

- What: Enforce the same section subtype policy and exact-owner mutations for JSON routes.
- Pattern: Use the subtype boundaries in `src/schemes/s2245/subs/s2245/router_ui.py:278-437,480-635`.

#### [MODIFY] `src/schemes/s2235/subs/s22350311/router_ui.py`

- What: Establish the owner-aware simple 2235 UI pattern with aggregate read-only and exact taluka/direct writes.
- Pattern: Current 22350311 UI CRUD at `src/schemes/s2235/subs/s22350311/router_ui.py:34-317`.

### Phase 28: Simple scheme rollout D

Scope: 3 files, ~330 LOC
Verify: `$env:OWNERSHIP_TARGETS='22350311,22350338'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s2235/subs/s22350311/router_api.py`

- What: Apply the 22350311 scope contract to JSON CRUD and reject owner fields from clients.
- Pattern: Current API CRUD at `src/schemes/s2235/subs/s22350311/router_api.py:95-153`.

#### [MODIFY] `src/schemes/s2235/subs/s22350338/router_ui.py`

- What: Apply the proven 22350311 aggregate/direct UI contract.
- Pattern: Use the sibling UI flow at `src/schemes/s2235/subs/s22350311/router_ui.py:34-317`.

#### [MODIFY] `src/schemes/s2235/subs/s22350338/router_api.py`

- What: Apply the proven 22350311 exact-owner JSON contract.
- Pattern: Use the sibling API CRUD at `src/schemes/s2235/subs/s22350311/router_api.py:95-153`.

### Phase 29: Simple scheme rollout E

Scope: 3 files, ~330 LOC
Verify: `python -m compileall -q src/schemes/s2235/subs/s22353408/router_ui.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; $env:OWNERSHIP_TARGETS='22353195'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s2235/subs/s22353195/router_ui.py`

- What: Apply aggregate/direct read and exact-owner write semantics.
- Pattern: Use the proven sibling UI at `src/schemes/s2235/subs/s22350311/router_ui.py:34-317`.

#### [MODIFY] `src/schemes/s2235/subs/s22353195/router_api.py`

- What: Apply exact-owner JSON CRUD and canonical aggregate responses.
- Pattern: Use the proven sibling API at `src/schemes/s2235/subs/s22350311/router_api.py:95-153`.

#### [MODIFY] `src/schemes/s2235/subs/s22353408/router_ui.py`

- What: Apply aggregate/direct read and exact-owner write semantics.
- Pattern: Use the proven sibling UI at `src/schemes/s2235/subs/s22350311/router_ui.py:34-317`.

### Phase 30: Simple scheme rollout F

Scope: 3 files, ~330 LOC
Verify: `$env:OWNERSHIP_TARGETS='22353408,76100149'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s2235/subs/s22353408/router_api.py`

- What: Complete exact-owner JSON CRUD for the 2235 family.
- Pattern: Use the proven sibling API at `src/schemes/s2235/subs/s22350311/router_api.py:95-153`.

#### [MODIFY] `src/schemes/s7610/subs/s76100149/router_ui.py`

- What: Establish the 7610 aggregate/direct UI and exact-owner write pattern.
- Pattern: Current direct filters at `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

#### [MODIFY] `src/schemes/s7610/subs/s76100149/router_api.py`

- What: Establish exact-owner JSON CRUD and canonical aggregate output for 7610.
- Pattern: Mirror the UI scope boundary at `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

### Phase 31: Simple scheme rollout G

Scope: 3 files, ~330 LOC
Verify: `python -m compileall -q src/schemes/s7610/subs/s76100167/router_ui.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; $env:OWNERSHIP_TARGETS='76100158'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s7610/subs/s76100158/router_ui.py`

- What: Apply the proven 76100149 aggregate/direct UI contract.
- Pattern: Use `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

#### [MODIFY] `src/schemes/s7610/subs/s76100158/router_api.py`

- What: Apply the proven 76100149 exact-owner API contract.
- Pattern: Mirror the scope boundary in `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

#### [MODIFY] `src/schemes/s7610/subs/s76100167/router_ui.py`

- What: Apply the proven 76100149 aggregate/direct UI contract.
- Pattern: Use `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

### Phase 32: Simple scheme rollout H

Scope: 3 files, ~330 LOC
Verify: `$env:OWNERSHIP_TARGETS='76100167,76101871'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s7610/subs/s76100167/router_api.py`

- What: Apply the proven 76100149 exact-owner API contract.
- Pattern: Mirror the scope boundary in `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

#### [MODIFY] `src/schemes/s7610/subs/s76101871/router_ui.py`

- What: Complete aggregate/direct UI behavior for 7610.
- Pattern: Use `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

#### [MODIFY] `src/schemes/s7610/subs/s76101871/router_api.py`

- What: Complete exact-owner JSON CRUD for 7610.
- Pattern: Mirror the scope boundary in `src/schemes/s7610/subs/s76100149/router_ui.py:61-79,212-214`.

### Phase 33: Loan scheme rollout

Scope: 3 files, ~300 LOC
Verify: `python -m compileall -q src/schemes/s6401/subs/s64010018/router_ui.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; $env:OWNERSHIP_TARGETS='62450017'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `src/schemes/s6245/subs/s62450017/router_ui.py`

- What: Add aggregate/direct UI and exact-owner writes for the 6245 loan table.
- Pattern: Follow the existing loan route shape documented at `docs/ARCHITECTURE.md:575-598`.

#### [MODIFY] `src/schemes/s6245/subs/s62450017/router_api.py`

- What: Add exact-owner JSON CRUD and canonical aggregate reads for 6245.
- Pattern: Follow the existing loan route shape documented at `docs/ARCHITECTURE.md:575-598`.

#### [MODIFY] `src/schemes/s6401/subs/s64010018/router_ui.py`

- What: Add aggregate/direct UI and exact-owner writes for the 6401 loan table.
- Pattern: Reuse the 6245 route structure documented at `docs/ARCHITECTURE.md:575-598`, retaining 6401 fields/config.

### Phase 34: Loan API completion and global template context

Scope: 3 files, ~250 LOC
Verify: `$env:OWNERSHIP_TARGETS='64010018'; python -m unittest tests.test_simple_scheme_ownership tests.test_aggregation_policies -v`

#### [MODIFY] `src/schemes/s6401/subs/s64010018/router_api.py`

- What: Complete exact-owner JSON CRUD and canonical aggregate reads for 6401.
- Pattern: Reuse the sibling route structure documented at `docs/ARCHITECTURE.md:575-598`.

#### [MODIFY] `src/core/template_context.py`

- What: Expose only verified principal, FY participation mode, can-edit, and authorized drill-down to templates.
- Pattern: Current global context at `src/core/template_context.py:7-25`.

#### [MODIFY] `templates/base.html`

- What: Expose verified scope/FY-participation mode to all templates, default taluka-backed district assistants to consolidated read view, and expose authorized drill-down only.
- Pattern: Current template context at `src/core/template_context.py:7-25` and taluka/completion UI logic at `templates/base.html:2357-2405`.

### Phase 34.1: Full simple-family conformance gate

Scope: 1 file, ~120 LOC
Verify: `$env:OWNERSHIP_TARGETS='all'; python -m unittest tests.test_simple_scheme_ownership -v`

#### [MODIFY] `tests/test_simple_scheme_ownership.py`

- What: Make the default/full manifest assert all 17 simple tables and every associated UI/API mutation/read path now that every rollout is present; assert same-session audit rollback as well as owner isolation.
- Pattern: Reuse the explicit registry manifest from `src/core/budget_data_registry.py`; no wildcard discovery.

### Phase 35: Completion ownership and derivation

Scope: 3 files, ~400 LOC
Verify: `python -m unittest tests.test_completion_ownership -v`

#### [MODIFY] `src/routers/completion_status.py`

- What: Replace toggle with idempotent explicit desired state; take the shared district/FY mode lock, upsert then lock the exact owner row; taluka/direct-district completion; derived AND where every included taluka must have an explicit true row; missing is pending/false; zero included talukas is `not_applicable/pending`, never vacuously true and never direct fallback; aggregate district cannot mutate; DCO breakdown uses effective state.
- Pattern: Existing lock and cache at `src/routers/completion_status.py:29-155`.

#### [MODIFY] `templates/base.html`

- What: Show editable completion to exact-owner taluka assistants and direct-district assistants, read-only derived status to consolidated districts, and send CSRF-protected `PUT {"is_complete": desired}` instead of POST-toggle.
- Pattern: Current district-only POST-toggle client at `templates/base.html:2372-2396`.

#### [CREATE] `tests/test_completion_ownership.py`

- What: Test upsert/absent-row concurrency, activation pending, missing-row false, deactivation exclusion without deletion, all-excluded not-applicable, direct/Mumbai City, FY isolation, aggregate mutation denial, and the taluka/direct/aggregate UI contract.
- Pattern: Extend the existing completion lock/status flow at `src/routers/completion_status.py:29-155`.

### Phase 35.1: Completion selection-page projection

Scope: 2 files, ~140 LOC
Verify: `python -m unittest tests.test_completion_ownership -v`

#### [MODIFY] `src/routers/ui_taluka_selection.py`

- What: Derive district status from owner-aware completion and revision without stale in-memory cache, preserving explicit all-excluded/pending semantics.
- Pattern: Existing district status aggregation at `src/routers/ui_taluka_selection.py:45-92`.

#### [MODIFY] `tests/test_completion_ownership.py`

- What: Enable the selection-page district/DCO status assertions only after this projection exists.
- Pattern: Reuse the exact owner completion fixtures from Phase 35.

### Phase 36: Fiscal-year ownership

Scope: 2 files, ~350 LOC
Verify: `python -m unittest tests.test_fiscal_year_ownership -v`

#### [MODIFY] `src/routers/fiscal_year.py`

- What: Under the same FY advisory lock and uncached resolver contract from Phase 17, replace partial lists with the 77-table registry plus an explicit auxiliary-FY manifest for `post_level_details`, direct-only `sub_head_expenditure_2075`, and `sub_schema_completions`. Clone canonical direct parent templates, build old→new budget-post IDs, and clone only direct structural post-level rows. Preserve `level_name`, positive `level_order`, `pay_stage`, `pay_level`, `hra_rate`, ownership identifiers, and the remapped parent ID; zero only `special_pay`, `basic_pay`, `grade_pay`, `local_supplementary_allowance`, `vehicle_allowance`, `washing_allowance`, `cash_allowance`, and `footwear_allowance_other`. Clone/zero the direct-only 2075 template, snapshot active management rows into new-FY participation, and lazily seed taluka parents later without child copying. Delete removes post-level children before parents, then all 77 owned rows, direct-only sub-head, completions, participation, and FY atomically.
- Pattern: Current clone/delete at `src/routers/fiscal_year.py:115-215,231-319`.
- System design: run only as the exact `FISCAL_YEAR_ADMIN(fiscal_year)` capability defined in Section 4.2; no generic unrestricted session. After the global FY lock, acquire exclusive district/FY mode locks in sorted district order before clone/delete so budget writes cannot cross the lifecycle boundary. Re-resolve the highest active FY before releasing the lock.

#### [CREATE] `tests/test_fiscal_year_ownership.py`

- What: All 77 owned plus three auxiliary FY tables covered; deterministic highest-active selection; concurrent selection/create and budget-write/delete serialization with fixed lock order; parent-ID remap; exact post-level preserve/zero allowlists with `level_order > 0`; direct-only 2075 clone/delete; no eager taluka fan-out/child copy; historical participation immutability; delete order/completeness; no duplicate direct NULL owner.
- Pattern: Characterize current clone/delete behavior at `src/routers/fiscal_year.py:115-215,231-319`.

### Phase 37: Export authorization and snapshot tests

Scope: 3 files, ~350 LOC
Verify: `python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/common/excel_export.py`

- What: Accept immutable verified scope/FY, create/close a worker-local scoped session inside the existing thread-pool callback, open one read-only repeatable-read transaction, and log scope/row count; never capture a request `Session` or request context across threads. Retain the existing local concurrency limiter.
- Pattern: Existing export concurrency at `src/schemes/common/excel_export.py:62-68`.

#### [MODIFY] `src/audit_middleware.py`

- What: Cover scheme-specific export paths and record actual result/scope without payload secrets.
- Pattern: Existing path/action handling at `src/audit_middleware.py:13-20,49-91`.

#### [CREATE] `tests/test_export_scope.py`

- What: Generic explicit-manifest export harness. `EXPORT_BATCH=common` initially proves worker-local scoped session ownership, repeatable-read snapshot, authorization, no request-session cross-thread use, no full-workbook fallthrough, and partial-file cleanup. Every later checkpoint adds its reducers/populators to all previously completed targets; `EXPORT_BATCH=all` is deferred to Phase 37.7.
- Pattern: Exercise the representative unscoped export path at `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py:395-480` and reducer at `src/schemes/s2053/subs/s20530028/excel_export/populators/budget_post_details.py:90-173`.

Every `export_with_throttle` caller must synchronously extract immutable scope/FY from the request session, then pass that value and a callback that accepts the worker-created session; its existing route-facing function may retain a `db` parameter for compatibility, but capturing or dereferencing that request `Session` in the worker closure is forbidden. The eight orchestration batches below cover the exact current caller inventory from `rg -l "export_with_throttle" src/schemes` other than the common service and the shared s2045 caller handled in Phase 37.1.

The refactored `s20530028` summary/list exports do not call `export_with_throttle`, and six post-status/post-expense/unit original-or-sheet-only endpoints still invoke synchronous wrappers with request sessions, so these are an additional explicit inventory. Phases 37.0I–37.0L pass immutable scope/FY into every summary, list, original, and sheet-only route. Summary/list services run from one worker-local, read-only repeatable-read transaction over the canonical projection; original/sheet-only callers `await` the common throttled worker path, whose callback receives its own scoped session. The synchronous request-session wrappers become unreachable and are removed. The common/populator phases still own workbook reduction; no request `Session` is captured by either path.

### Phase 37.0A: Worker-local export sessions A

Scope: 3 files, ~150 LOC
Verify: `$env:EXPORT_BATCH='37.0A'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s0029/subs/s0029/excel_export/template_export_service.py`
- What: Pass immutable scope/FY and consume the worker session; never capture request DB state.
- Pattern: New callback contract in `src/schemes/common/excel_export.py` from Phase 37.

#### [MODIFY] `src/schemes/s2029/subs/s20290037/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2029/subs/s20290046/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

### Phase 37.0B: Worker-local export sessions B

Scope: 3 files, ~150 LOC
Verify: `$env:EXPORT_BATCH='37.0B'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2029/subs/s20290182/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2029/subs/s20290262/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2045/subs/s20450091/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

### Phase 37.0C: Worker-local export sessions C

Scope: 3 files, ~150 LOC
Verify: `$env:EXPORT_BATCH='37.0C'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530019/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2053/subs/s20530153/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

### Phase 37.0D: Worker-local export sessions D

Scope: 3 files, ~150 LOC
Verify: `$env:EXPORT_BATCH='37.0D'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530162/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2053/subs/s20530233/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2053/subs/s20530242/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

### Phase 37.0E: Worker-local export sessions E

Scope: 3 files, ~150 LOC
Verify: `$env:EXPORT_BATCH='37.0E'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530304/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2053/subs/s20530313/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2053/subs/s20530378/excel_export/template_export_service.py`
- What: Apply the worker-local session contract.
- Pattern: Common export contract from Phase 37.

### Phase 37.0F: Worker-local export sessions F

Scope: 3 files, ~150 LOC
Verify: `$env:EXPORT_BATCH='37.0F'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530387/excel_export/template_export_service.py`
- What: Apply the worker-local session contract while retaining direct-only DCO Staff behavior.
- Pattern: Common export contract from Phase 37 and registry direct-only declaration.

#### [MODIFY] `src/schemes/s2075/excel_export/template_export_service.py`
- What: Apply the worker-local session contract for both district and direct-only sub-head sheets.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s2235/excel_export/template_export_service.py`
- What: Apply the worker-local session contract across all four 2235 sub-schemes.
- Pattern: Common export contract from Phase 37.

### Phase 37.0G: Worker-local export sessions G

Scope: 3 files, ~150 LOC
Verify: `$env:EXPORT_BATCH='37.0G'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2245_2215/excel_export/template_export_service.py`
- What: Apply the worker-local session contract for 2215/2245.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s6245/subs/s62450017/excel_export/template_export_service.py`
- What: Apply the worker-local session contract for 6245.
- Pattern: Common export contract from Phase 37.

#### [MODIFY] `src/schemes/s6401/subs/s64010018/excel_export/template_export_service.py`
- What: Apply the worker-local session contract for 6401.
- Pattern: Common export contract from Phase 37.

### Phase 37.0H: Worker-local export sessions H

Scope: 1 file, ~60 LOC
Verify: `$env:EXPORT_BATCH='37.0H'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s7610/excel_export/template_export_service.py`
- What: Complete the caller inventory with a worker-local scoped session for all four 7610 sub-schemes.
- Pattern: Common export contract from Phase 37.

### Phase 37.0I: s20530028 budget-post summary/list exports

Scope: 3 files, ~180 LOC
Verify: `$env:EXPORT_BATCH='37.0I'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py`
- What: Resolve immutable principal scope/FY at the route and pass it to summary/list export. Change original and sheet-only calls so the common throttled callback receives the worker-created scoped session instead of the request `db`; do not expose or capture the request session in any of the four routes.
- Pattern: Current export routes at `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py:395-480` and the common snapshot contract from Phase 37.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/budget_post_details/services/export_service.py`
- What: Read canonical policy-reduced budget-post rows inside one worker-local repeatable-read transaction and render from that immutable result.
- Pattern: Current repository-backed export at `src/schemes/s2053/subs/s20530028/budget_post_details/services/export_service.py:22-67`.

#### [MODIFY] `tests/test_export_scope.py`
- What: Enable physical-taluka, consolidated-district, DCO, request-session isolation, and one-snapshot cases for budget-post summary, list, original, and sheet-only routes.
- Pattern: Extend the cumulative Phase 37 manifest.

### Phase 37.0J: s20530028 post-status summary/list exports

Scope: 3 files, ~190 LOC
Verify: `$env:EXPORT_BATCH='37.0J'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/post_status/controllers/ui_controller.py`
- What: Pass only immutable scope/FY to summary/list. Convert original and sheet-only endpoints to `await` the common throttled worker boundary whose callback receives its worker-local scoped session; never pass the request session.
- Pattern: Current export routes at `src/schemes/s2053/subs/s20530028/post_status/controllers/ui_controller.py:334-398`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/post_status/services/export_service.py`
- What: Use the canonical status reducer in one worker-local repeatable-read transaction for summary/list rendering; remove the now-unreachable synchronous original/sheet-only request-session wrappers.
- Pattern: Current summary/list implementation at `src/schemes/s2053/subs/s20530028/post_status/services/export_service.py:33-147`.

#### [MODIFY] `tests/test_export_scope.py`
- What: Enable exact-owner and consolidated status totals for summary/list/original/sheet-only, plus no request-session sharing and one repeatable-read snapshot per export.
- Pattern: Extend the cumulative Phase 37 manifest.

### Phase 37.0K: s20530028 post-expense summary/list exports

Scope: 3 files, ~190 LOC
Verify: `$env:EXPORT_BATCH='37.0K'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/post_expenses/controllers/ui_controller.py`
- What: Pass only immutable scope/FY to summary/list. Convert original and sheet-only endpoints to `await` the common throttled worker boundary whose callback receives its worker-local scoped session; never pass the request session.
- Pattern: Current export routes at `src/schemes/s2053/subs/s20530028/post_expenses/controllers/ui_controller.py:364-449`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/post_expenses/services/export_service.py`
- What: Apply filled/vacant SUM and synchronized-monetary per-owner-max-then-sum inside one worker-local repeatable-read transaction for summary/list rendering; remove the now-unreachable synchronous original/sheet-only request-session wrapper.
- Pattern: Current summary/list implementation at `src/schemes/s2053/subs/s20530028/post_expenses/services/export_service.py:30-134`.

#### [MODIFY] `tests/test_export_scope.py`
- What: Enable exact-owner and consolidated post-expense golden outputs for summary/list/original/sheet-only, intra-owner conflict metadata, session isolation, and one-snapshot assertions.
- Pattern: Extend the cumulative Phase 37 manifest.

### Phase 37.0L: s20530028 unit-expenditure summary/list exports

Scope: 3 files, ~180 LOC
Verify: `$env:EXPORT_BATCH='37.0L'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/unit_expenditure/controllers/ui_controller.py`
- What: Pass only immutable scope/FY to summary/list. Convert original and sheet-only endpoints to `await` the common throttled worker boundary whose callback receives its worker-local scoped session; never pass the request session.
- Pattern: Current export routes at `src/schemes/s2053/subs/s20530028/unit_expenditure/controllers/ui_controller.py:302-391`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/unit_expenditure/services/export_service.py`
- What: Sum canonical unit-account rows inside one worker-local repeatable-read transaction for summary/list rendering; remove the now-unreachable synchronous original/sheet-only request-session wrapper.
- Pattern: Current summary/list implementation at `src/schemes/s2053/subs/s20530028/unit_expenditure/services/export_service.py:35-129`.

#### [MODIFY] `tests/test_export_scope.py`
- What: Enable exact-owner and consolidated unit-account golden outputs for summary/list/original/sheet-only, session isolation, and one-snapshot assertions.
- Pattern: Extend the cumulative Phase 37 manifest.

### Phase 37.1: Shared/simple export reducers

Scope: 3 files, ~300 LOC
Verify: `$env:EXPORT_BATCH='37.1'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2045/common/district_expenditure/unified_excel_export.py`

- What: Pass the immutable resolved scope/FY to the shared populator; remove client-district authority and full-workbook fallthrough.
- Pattern: Current export orchestration at `src/schemes/s2045/common/district_expenditure/unified_excel_export.py:99-126`.

#### [MODIFY] `src/schemes/s2045/common/district_expenditure/excel_populator.py`

- What: Consume policy-based effective rows rather than overwriting a district cell with the last physical owner row.
- Pattern: Current row population at `src/schemes/s2045/common/district_expenditure/excel_populator.py:70-87`.

#### [MODIFY] `src/schemes/s7610/excel_export/populators/s7610_populator.py`

- What: Reduce included taluka rows per district/natural key and label remarks by taluka.
- Pattern: Current district lookup/population at `src/schemes/s7610/excel_export/populators/s7610_populator.py:99-107`.

### Phase 37.2: Section export reducers

Scope: 3 files, ~300 LOC
Verify: `$env:EXPORT_BATCH='37.2'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2245_2215/excel_export/populators/s2215_populator.py`

- What: Use effective aggregation by account head and FY; preserve labelled per-taluka remarks.
- Pattern: Current district mapping at `src/schemes/s2245_2215/excel_export/populators/s2215_populator.py:46-57`.

#### [MODIFY] `src/schemes/s2245_2215/excel_export/populators/s2245_populator.py`

- What: Use effective aggregation by table section and protect special direct-only composite rows.
- Pattern: Current section population at `src/schemes/s2245_2215/excel_export/populators/s2245_populator.py:95-140`.

#### [MODIFY] `src/schemes/s2075/excel_export/populators/s2075_populator.py`

- What: Aggregate only the district table; keep `sub_head_expenditure_2075` direct/DCO-only.
- Pattern: Current dual-table population at `src/schemes/s2075/excel_export/populators/s2075_populator.py:79-100`.

### Phase 37.3: Loan export reducers

Scope: 2 files, ~200 LOC
Verify: `$env:EXPORT_BATCH='37.3'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s6245/subs/s62450017/excel_export/district_expenditure.py`

- What: Reduce effective source rows by district/FY and preserve source-labelled remarks.
- Pattern: Current last-row district map at `src/schemes/s6245/subs/s62450017/excel_export/district_expenditure.py:36-48`.

#### [MODIFY] `src/schemes/s6401/subs/s64010018/excel_export/district_expenditure.py`

- What: Apply the identical registry policy for scheme 6401 without sharing scheme-specific cell coordinates.
- Pattern: Current 6401 query/map at `src/schemes/s6401/subs/s64010018/excel_export/district_expenditure.py:36-49`; reuse only the scope/reduction contract, not coordinates.

### Phase 37.4: Omitted simple export reducers

Scope: 2 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.4'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s0029/subs/s0029/excel_export/arthsankalpiy_jilah.py`

- What: Replace the `(section,district) → last physical row` map with registry reduction across effective sources before cell population.
- Pattern: Current overwrite at `src/schemes/s0029/subs/s0029/excel_export/arthsankalpiy_jilah.py:70-81`.

#### [MODIFY] `src/schemes/s2235/excel_export/populators/s2235_populator.py`

- What: Replace `{district: row}` with per-natural-key effective aggregation and labelled remarks for all four 2235 sub-schemes.
- Pattern: Current last-row map at `src/schemes/s2235/excel_export/populators/s2235_populator.py:96-102`.

### Phase 37.5: Simple export full gate

Scope: 1 file, ~80 LOC
Verify: `$env:EXPORT_BATCH='simple-all'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `tests/test_export_scope.py`

- What: Enable the complete simple-family matrix now that Phases 37.1–37.4 exist: exact taluka, consolidated district, DCO per-district effective source, s2245 subtype, s2075 direct-only auxiliary rows, and no last-row-wins.
- Pattern: Reuse the explicit registry manifest; no wildcard discovery.

The four-table batches below all apply one invariant: each named populator consumes policy-reduced effective rows before writing cells. Budget-post amounts derive per source then sum; post status sums by natural key; filled/vacant sum by category/class; synchronized monetary expenses take per-owner max then sum owners; unit expenditure sums by unit; DCO Staff remains direct. Each `EXPORT_BATCH` checkpoint adds the exact files listed in that phase to all earlier completed export targets, so it tests only implemented code while remaining cumulative.

### Phase 37.6A: Four-table export batch A

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6A'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530019/excel_export/populators/budget_post_details.py`
- What: Apply the four-table invariant to 20530019 budget-post cells.
- Pattern: Current per-district population at this file's `:90-173`; compile policies from `src/core/budget_data_registry.py`.

#### [MODIFY] `src/schemes/s2053/subs/s20530019/excel_export/populators/post_status.py`
- What: Apply the invariant to 20530019 status/category/class cells.
- Pattern: Replace repeated district-only queries at this file's `:30-352`.

#### [MODIFY] `src/schemes/s2053/subs/s20530019/excel_export/populators/post_expenses.py`
- What: Apply the split count/repeated-monetary policies before 20530019 cell writes.
- Pattern: Current per-owner overwrite at this file's `:30-85`.

### Phase 37.6B: Four-table export batch B

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6B'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530019/excel_export/populators/unit_expenditure.py`
- What: Sum 20530019 effective rows by district/unit before cell writes.
- Pattern: Current last-row write at this file's `:42-68`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/excel_export/populators/budget_post_details.py`
- What: Apply the budget-post invariant to 20530028.
- Pattern: Existing calculations at this file's `:90-173`.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/excel_export/populators/post_status.py`
- What: Apply the status invariant to 20530028.
- Pattern: Use the verified 20530019 conversion from Phase 37.6A while retaining this template's cell map.

### Phase 37.6C: Four-table export batch C

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6C'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/excel_export/populators/post_expenses.py`
- What: Apply split post-expense reduction to 20530028.
- Pattern: Phase 37.6A policy; retain this file's coordinates.

#### [MODIFY] `src/schemes/s2053/subs/s20530028/excel_export/populators/unit_expenditure.py`
- What: Apply unit/natural-key summation to 20530028.
- Pattern: Phase 37.6B policy; retain this file's coordinates.

#### [MODIFY] `src/schemes/s2053/subs/s20530153/excel_export/populators/budget_post_details.py`
- What: Apply derive-then-sum and consensus handling to 20530153.
- Pattern: Phase 37.6B budget-post conversion.

### Phase 37.6D: Four-table export batch D

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6D'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530153/excel_export/populators/post_status.py`
- What: Apply status reduction to 20530153.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530153/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20530153.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530153/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20530153.
- Pattern: Phase 37.6B unit conversion.

### Phase 37.6E: Four-table export batch E

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6E'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530162/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20530162.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530162/excel_export/populators/post_status.py`
- What: Apply status reduction to 20530162.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530162/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20530162.
- Pattern: Phase 37.6A expense conversion.

### Phase 37.6F: Four-table export batch F

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6F'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530162/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20530162.
- Pattern: Phase 37.6B unit conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530233/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20530233.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530233/excel_export/populators/post_status.py`
- What: Apply status reduction to 20530233.
- Pattern: Phase 37.6A status conversion.

### Phase 37.6G: Four-table export batch G

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6G'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530233/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20530233.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530233/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20530233.
- Pattern: Phase 37.6B unit conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530242/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20530242.
- Pattern: Phase 37.6B budget-post conversion.

### Phase 37.6H: Four-table export batch H

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6H'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530242/excel_export/populators/post_status.py`
- What: Apply status reduction to 20530242.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530242/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20530242.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530242/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20530242.
- Pattern: Phase 37.6B unit conversion.

### Phase 37.6I: Four-table export batch I

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6I'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530304/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20530304.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530304/excel_export/populators/post_status.py`
- What: Apply status reduction to 20530304.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530304/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20530304.
- Pattern: Phase 37.6A expense conversion.

### Phase 37.6J: Four-table export batch J

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6J'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530304/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20530304.
- Pattern: Phase 37.6B unit conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530313/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20530313.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530313/excel_export/populators/post_status.py`
- What: Apply status reduction to 20530313.
- Pattern: Phase 37.6A status conversion.

### Phase 37.6K: Four-table export batch K

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6K'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530313/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20530313.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530313/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20530313.
- Pattern: Phase 37.6B unit conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530378/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20530378.
- Pattern: Phase 37.6B budget-post conversion.

### Phase 37.6L: Four-table export batch L

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6L'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530378/excel_export/populators/post_status.py`
- What: Apply status reduction to 20530378.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530378/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20530378.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2053/subs/s20530378/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20530378.
- Pattern: Phase 37.6B unit conversion.

### Phase 37.6M: Four-table export batch M

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6M'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2029/subs/s20290037/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20290037.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290037/excel_export/populators/post_status.py`
- What: Apply status reduction to 20290037.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290037/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20290037.
- Pattern: Phase 37.6A expense conversion.

### Phase 37.6N: Four-table export batch N

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6N'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2029/subs/s20290037/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20290037.
- Pattern: Phase 37.6B unit conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290046/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20290046.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290046/excel_export/populators/post_status.py`
- What: Apply status reduction to 20290046.
- Pattern: Phase 37.6A status conversion.

### Phase 37.6O: Four-table export batch O

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6O'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2029/subs/s20290046/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20290046.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290046/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20290046.
- Pattern: Phase 37.6B unit conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290182/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20290182.
- Pattern: Phase 37.6B budget-post conversion.

### Phase 37.6P: Four-table export batch P

Scope: 3 files, ~220 LOC
Verify: `$env:EXPORT_BATCH='37.6P'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2029/subs/s20290182/excel_export/populators/post_status.py`
- What: Apply status reduction to 20290182.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290182/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20290182.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290182/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20290182.
- Pattern: Phase 37.6B unit conversion.

### Phase 37.6Q: Four-table export batch Q

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6Q'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2029/subs/s20290262/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20290262.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290262/excel_export/populators/post_status.py`
- What: Apply status reduction to 20290262.
- Pattern: Phase 37.6A status conversion.

#### [MODIFY] `src/schemes/s2029/subs/s20290262/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20290262.
- Pattern: Phase 37.6A expense conversion.

### Phase 37.6R: Four-table export batch R

Scope: 3 files, ~240 LOC
Verify: `$env:EXPORT_BATCH='37.6R'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2029/subs/s20290262/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20290262.
- Pattern: Phase 37.6B unit conversion.

#### [MODIFY] `src/schemes/s2045/subs/s20450091/excel_export/populators/budget_post_details.py`
- What: Apply budget-post reduction to 20450091.
- Pattern: Phase 37.6B budget-post conversion.

#### [MODIFY] `src/schemes/s2045/subs/s20450091/excel_export/populators/post_status.py`
- What: Apply status reduction to 20450091.
- Pattern: Phase 37.6A status conversion.

### Phase 37.6S: Four-table export batch S

Scope: 2 files, ~160 LOC
Verify: `$env:EXPORT_BATCH='37.6S'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `src/schemes/s2045/subs/s20450091/excel_export/populators/post_expenses.py`
- What: Apply split expense reduction to 20450091.
- Pattern: Phase 37.6A expense conversion.

#### [MODIFY] `src/schemes/s2045/subs/s20450091/excel_export/populators/unit_expenditure.py`
- What: Apply unit reduction to 20450091.
- Pattern: Phase 37.6B unit conversion.

### Phase 37.7: Full export conformance gate

Scope: 1 file, ~160 LOC
Verify: `$env:EXPORT_BATCH='all'; python -m unittest tests.test_export_scope -v`

#### [MODIFY] `tests/test_export_scope.py`

- What: Enable all 14 consolidatable four-table trees, all simple exporters, and direct-only 20530387. Golden workbooks assert exact taluka rows, policy-correct district/DCO totals, mixed/remarks behavior, one repeatable-read snapshot, no last-row overwrite, and no direct-plus-taluka double count.
- Pattern: Use the exact exporter manifest in Section 3.6 and the completed batch mapping; no wildcard discovery.

### Phase 38: Parser-backed server query plan

Scope: 3 files, ~520 LOC
Verify: `python -m pip install -r requirements.txt; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m unittest tests.test_chatbot_scope -v`

#### [MODIFY] `requirements.txt`

- What: Add exact `sqlglot==30.13.0`; change no other package.
- Pattern: Existing pinned manifest at `requirements.txt:1-53`; no lockfile exists.

#### [CREATE] `src/chatbot/core/query_plan.py`

- What: Parse one PostgreSQL SELECT AST into a typed restricted plan, reject the Section 5.1 grammar, resolve table/dimensions/metrics from the registry, authorize/intersect district/FY filters, build the effective-source subquery, and compile SQLAlchemy with bound values and a 1–100 limit. Generated taluka/session predicates are rejected rather than trusted or string-rewritten.
- Pattern: Replace regex/string policy at `src/chatbot/security/policies.py:46-111`; compile aggregation expressions from `src/core/budget_data_registry.py` **[NEW]**.
- System design: parser failure or an unregistered metric/operator fails closed; no retry broadens grammar.

#### [CREATE] `tests/test_chatbot_scope.py`

- What: Assert `sqlglot.__version__ == '30.13.0'`; verify the accepted plan subset, rejection of CTE/UNION/subquery/comments/multi/DML/DDL/taluka-session predicates/unknown expressions, authorized district/FY intersection and out-of-scope refusal, bound filters/limit, effective-source-before-aggregation, and golden registry metrics including repeated expenses/HRA/consensus/remarks.
- Pattern: Exercise `src/chatbot/core/query_plan.py` **[NEW]** directly; router/execution assertions are added later.

### Phase 39: Chatbot principal and mandatory policy

Scope: 3 files, ~360 LOC
Verify: `python -m unittest tests.test_chatbot_scope -v`

#### [MODIFY] `src/routers/api_assistant.py`

- What: Resolve active verified principal, map taluka to its reporting district plus exact owner, reject a deactivated principal, and reject the data query when that taluka is excluded for the requested FY without revoking its otherwise-valid authentication session. Pass immutable scope/FY instead of cookies.
- Pattern: Current user/context validation at `src/routers/api_assistant.py:63-148`.

#### [MODIFY] `src/chatbot/security/policies.py`

- What: Replace district-string checks/injection with authorization of typed query plans and bound server compilation; no policy method returns rewritten SQL text.
- Pattern: Current mixin at `src/chatbot/security/policies.py:46-111`.

#### [MODIFY] `tests/test_chatbot_scope.py`

- What: Enable cross-taluka isolation, direct vs consolidated district, DCO effective source, deactivated/excluded session, forged display-cookie, and stable DCO fingerprint cases.
- Pattern: Extend the Phase 38 plan tests through the router/policy boundary.

### Phase 40: Chatbot execution order and bound execution

Scope: 3 files, ~440 LOC
Verify: `python -m unittest tests.test_chatbot_scope -v`

#### [MODIFY] `src/chatbot/main.py`

- What: Route fast and LLM output through one parse→authorize→compile→execute pipeline; remove fast-path early execution and mutable answer/result caching.
- Pattern: Current early fast execution at `src/chatbot/main.py:91-117` and later policy at `:170-184`.

#### [MODIFY] `src/chatbot/processors/query_execution.py`

- What: Accept only the server-compiled statement plus bound parameters and immutable scope, create/close a worker-local scoped SQLAlchemy session (never share the request session across the chatbot executor), disable result cache, and log scope fingerprint/row count without SQL values. The existing psycopg pool may remain for schema metadata but cannot execute answer queries.
- Pattern: Current raw execute/cache at `src/chatbot/processors/query_execution.py:12-29,52-124`.

#### [MODIFY] `tests/test_chatbot_scope.py`

- What: Prove both fast and LLM paths hit the same boundary, no SQL executes before policy, no raw SQL API remains, one validator-feedback regeneration is bounded, and DB/LLM/parser failures never widen scope.
- Pattern: Characterize and replace ordering at `src/chatbot/main.py:91-184`.

### Phase 40.1: Chatbot fast/schema/legacy-validator closure

Scope: 3 files, ~340 LOC
Verify: `python -m compileall -q src/chatbot/core; python -m unittest tests.test_chatbot_scope -v`

#### [MODIFY] `src/chatbot/core/query_classifier.py`

- What: Fast templates produce typed unexecuted plans; scope fingerprint/FY enter the plan-cache key; no answer/result cache remains.
- Pattern: Current fast SQL and semantic cache at `src/chatbot/core/query_classifier.py:62-169,189-218`.

#### [MODIFY] `src/chatbot/core/schema_engine.py`

- What: Expose geographical district, server-only taluka ownership, registered dimensions/metrics, and aggregation semantics without presenting owner or arbitrary aggregate expressions as writable/queryable model choices.
- Pattern: Current metadata construction at `src/chatbot/core/schema_engine.py:75-122,196-208`.

#### [MODIFY] `src/chatbot/core/sql_validator.py`

- What: Remove regex security claims; retain only compatibility helpers that delegate to `query_plan.py`, or delete dead validators after all callers move. It must not inject predicates or execute strings.
- Pattern: Current regex/table/column validation at `src/chatbot/core/sql_validator.py:1-130`.

### Phase 40.2: Chatbot full contract and documentation

Scope: 2 files, ~220 LOC
Verify: `python -m unittest tests.test_chatbot_scope -v`

#### [MODIFY] `tests/test_chatbot_scope.py`

- What: Enable fast-plan and schema-metadata assertions plus full end-to-end golden answers for counts, synchronized monetary expenses, derive-then-sum HRA, mixed consensus, and labelled remarks.
- Pattern: Exercise all Phase 38–40.1 files with exact registry fixtures.

#### [MODIFY] `docs/CHATBOT_ARCHITECTURE_PLAN.md`

- What: Record authoritative taluka scope, SQLGlot-to-typed-plan boundary, server-owned pre-aggregation scope, registered metrics, both-path enforcement, no-result-cache policy, and rejected grammar.
- Pattern: Layer plan at `docs/CHATBOT_ARCHITECTURE_PLAN.md:93-204,275-311`.

### Phase 41: Cache and training privacy cleanup

Scope: 3 files, ~250 LOC
Verify: `python -m unittest tests.test_cache_privacy -v`

#### [MODIFY] `src/utils_cache.py`

- What: Separate named logical static caches from DB result functions, remove unreliable substring invalidation contract, and provide cache stats without exposing values.
- Pattern: Current hashed key/decorator/store at `src/utils_cache.py:8-45,139-227`.

#### [MODIFY] `src/routers/training.py`

- What: Use verified principal and return user-specific content private/no-store.
- Pattern: Current user-specific cache/response at `src/routers/training.py:514-589`.

#### [CREATE] `tests/test_cache_privacy.py`

- What: No authenticated public cache, no cross-scope cached answer, selection revision changes plan key, and supported public cache-API behavior. Scheme-specific nonexistent-member assertions are enabled only after both defects are modified in Phase 42.
- Pattern: Exercise current cache storage/key behavior at `src/utils_cache.py:8-45,139-227` and authenticated training response at `src/routers/training.py:514-589`.

### Phase 42: Scheme cache defect removal

Scope: 3 files, ~150 LOC
Verify: `python -m unittest tests.test_cache_privacy -v`

#### [MODIFY] `src/schemes/s2053/subs/s20530313/shared/services/cache_service.py`

- What: Remove `_cache` access and delegate only supported logical cache operations; DB result caches stay disabled.
- Pattern: Actual storage is `_store` at `src/utils_cache.py:8-13`; do not reach into either private member from scheme code.

#### [MODIFY] `src/schemes/s2053/subs/s20530387/shared/services/cache_service.py`

- What: Remove `_cache` access and delegate only supported logical cache operations; DB result caches stay disabled.
- Pattern: Actual storage is `_store` at `src/utils_cache.py:8-13`; do not reach into either private member from scheme code.

#### [MODIFY] `tests/test_cache_privacy.py`

- What: Enable static and behavioral closure assertions for both scheme services: zero `_cache`/private-store access and only the supported `utils_cache` public API.
- Pattern: Extend the Phase 41 cache contract after both production defects are removed.

### Phase 43: Full regression and architecture documentation

Scope: 3 files, ~650 LOC
Verify: `python scripts/migrate.py --database-url-env TEST_DATABASE_URL --check-only; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m compileall -q src tests; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m unittest discover -s tests -p "test_*.py" -v`

#### [MODIFY] `docs/ARCHITECTURE.md`

- What: Document one-shot migration startup, explicit empty-database-only bootstrap, verified sessions, physical taluka ownership, direct/aggregate mode, named system scopes, lazy seed/no-child-copy rule, auxiliary FY lifecycle, completion/export/chatbot flow, and correct the present JWT claim to match actual implementation.
- Pattern: Current system/role overview and pattern summary at `docs/ARCHITECTURE.md:1-102,863-894`.

#### [MODIFY] `docs/DYNAMIC_FISCAL_YEAR_REFACTORING_GUIDE.md`

- What: Add owner propagation, 77-table plus auxiliary-FY manifest, parent-ID/post-level clone order, canonical-template-only FY clone, lazy taluka seed, current-FY locking rule, and preserve all internal year/data keys.
- Pattern: Backend cloning checklist and immutable identifiers at `docs/DYNAMIC_FISCAL_YEAR_REFACTORING_GUIDE.md:149-334,496-538`.

#### [CREATE] `tests/test_end_to_end_taluka_consolidation.py`

- What: PostgreSQL-backed role matrix across all 77 owned tables plus three auxiliary FY tables, 14 consolidatable and one direct-only four-table scheme, 17 simple tables, two FYs, first/same-set/all-excluded cutover, activation/deactivation/reactivation, completion, export, chatbot, concurrent login/selection/FY/data writes, strict-audit rollback, and no secret leakage. Instrument executed owned-table statements and compare a static registered-route/raw-SQL inventory so “zero unscoped” does not mean only “routes happened to be exercised.” The inventory explicitly includes every legacy `api_budget_details.py`, physical UI mutation, legacy reducer, and synchronous/async export route; every protected mutation must produce a canonical same-transaction audit even when a legacy supplemental logger raises and is caught.
- Pattern: Build the role/FY matrix from the verified hierarchy at `docs/ARCHITECTURE.md:64-102` and the transaction runner at `src/utils_migrations.py:260-332`.
- System design: run against disposable PostgreSQL 15+; SQLite is not accepted because NULL-equality constraints, JSON, and locking semantics differ.

### Phase 44: Deployment rehearsal and release gate

Scope: 2 files, ~300 LOC
Verify: `python scripts/preflight_taluka_ownership.py --check; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python scripts/verify_taluka_cutover.py --all-districts --all-fiscal-years --dry-run --backup-restore-rehearsal`

#### [CREATE] `scripts/verify_taluka_cutover.py`

- What: Enumerate every registered district/FY and auxiliary table; verify migration checksums/catalog definitions, source counts, legacy non-zero counts, policy-based aggregate checksums, management links, owner orphans/duplicates, and post-cutover comparison. `--backup-restore-rehearsal` verifies a created backup by restoring it into `TEST_DATABASE_URL` and running pre-cutover schema/data checks. First participation/seed mutation requires explicit non-dry-run, recorded backup checksum/path, current commit SHA, domain acknowledgement, and all-district clean report.
- Pattern: Use the read-only migration discovery/query discipline at `src/utils_migrations.py:335-420` plus registry `[NEW]` `src/core/budget_data_registry.py`.

#### [MODIFY] `docs/plan.md`

- What: During implementation only, append dated verification evidence, deviations approved by product/domain owner, migration checksum, and final release/rollback decision. Do not rewrite the design silently.
- Pattern: Preserve the evidence-boundary and implementation-gate format in `docs/plan.md:23-45` **[NEW]**.

Release criteria:

- all tests pass on PostgreSQL 15+;
- table registry count is exactly 77, the auxiliary FY manifest is exactly `post_level_details`, `sub_head_expenditure_2075`, and `sub_schema_completions`, and both match database inspection;
- zero duplicate/orphan owner rows;
- zero unscoped owned-model queries in executed-query instrumentation and zero unregistered owned-data consumers in the static route/raw-SQL manifest;
- every protected identity/participation/completion/budget mutation emits one canonical redacted audit row in the caller transaction; audit insertion failure rolls back the mutation;
- direct legacy plus FY-included taluka values are never double-counted;
- newly created/reactivated taluka accounts can log in with their documented role default and are forced to change it; an already-active account that still uses that default is also forced on its first post-cutover login, while customized passwords remain valid;
- taluka UI/API/export/chatbot/completion cannot read another taluka;
- district/DCO totals equal policy-based FY-included taluka aggregation;
- Mumbai City and DCO Staff remain direct and unchanged;
- the recorded backup restores successfully into a disposable test database; pre-cutover code rollback is permitted only before any participation/seed, and post-cutover rollback is code plus verified database restore—old code is never started against seeded taluka rows;
- documentation reflects shipped behavior.

---

## Rejected alternatives

- **Overload `district` with full taluka unit:** fewer schema edits, but corrupts geographical semantics, conflicts with special composite district values in s2245, and makes DCO scans/leak prevention fragile.
- **Materialize district aggregate rows:** reduces some reader changes but creates stale/lost-update risk across the duplicated mutation topology, requires 77-table triggers or perfect write centralization, and cannot represent mixed HRA/rate attributes safely.
- **Copy existing district totals to each taluka:** multiplies totals and is incorrect.
- **Assign legacy totals to one arbitrary taluka:** fabricates ownership and is not auditable domain truth.
- **Add Redis/microservices/queue now:** no current requirement justifies the operational complexity; the modular monolith and local PostgreSQL transaction boundaries are sufficient.
- **Trust prompts or client cookies for isolation:** neither is an authorization boundary.

The result is a normalized source-of-truth model with one shared scope contract, small local transactions, no new infrastructure, and an explicit route for later production hardening without redesigning the data model.
