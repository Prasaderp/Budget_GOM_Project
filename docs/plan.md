file_path: C:\Internship\Agenthix AI\GOM PROJECTS\BudgetMakingSystem\MAIN_PROJECT\docs\plan.md
content: # Technical Design Document — Taluka-Level Data Consolidation

> **Status:** Design approved for implementation. Zero implementation code in this document.
> **Author role:** Principal Systems Architect
> **Target:** `MAIN_PROJECT` (FastAPI + SQLAlchemy 2.0.48 + PostgreSQL + Jinja2, modular monolith)

---

## 1. MISSING CONTEXT

**Context sufficient.** The design below is anchored on files that were read in full or in relevant part:

| Area | Files verified |
|---|---|
| Auth & scoping | `src/utils_auth.py`, `src/utils_district.py`, `src/utils_taluka.py`, `src/utils_taluka_user_management.py` |
| Core framework | `src/core/base_models.py`, `src/core/base_config.py`, `src/core/registry.py`, `src/core/secure_crud.py`, `src/database.py` |
| Models (all 5 shapes) | `src/schemes/s2053/subs/s20530028/models.py`, `src/schemes/s2045/common/district_expenditure/base_models.py`, `src/schemes/s2235/subs/s22350311/models.py`, `src/schemes/s2075/models.py`, `src/schemes/s0029/subs/s0029/models.py`, `src/schemes/s2215/subs/s2215/models.py`, `src/schemes/s2245/subs/s2245/models.py`, `src/schemes/s6245/subs/s62450017/models.py`, `src/schemes/s7610/subs/s76100149/models.py` |
| UI/write paths | `src/schemes/s2053/subs/s20530019/ui_budget_details.py`, `.../ui_abstract.py`, `src/schemes/s2235/subs/s22350311/router_ui.py`, `.../helpers.py`, `src/schemes/s2053/subs/s20530019/helpers.py` |
| Cross-cutting | `src/routers/ui_taluka_selection.py`, `src/routers/completion_status.py`, `src/routers/fiscal_year.py`, `src/routers/api_assistant.py`, `src/utils_timing.py`, `src/utils_fiscal_year.py`, `src/utils_migrations.py`, `src/audit_middleware.py`, `src/main.py` (wiring only) |
| Chatbot | `src/chatbot/core/schema_engine.py`, `src/chatbot/core/sql_validator.py`, `src/chatbot/security/policies.py`, `src/chatbot/processors/query_execution.py` |
| Export | `src/schemes/common/excel_export.py`, `src/schemes/s2053/subs/s20530019/excel_export/template_export_service.py`, `.../populators/budget_post_details.py` |
| Seed data shape | `migrations/schemes/s2053/DATAINSERTION_20530019.sql` |

**Empirically verified (not assumed):** the SQLAlchemy `do_orm_execute` + `with_loader_criteria` mechanism this design depends on was executed against SQLAlchemy 2.0.48 (the version in `requirements.txt`) across 12 query shapes taken from this codebase — `query(Model)`, `query(Model.col)`, `query(func.sum())`, `with_entities(func.count())`, `group_by`, 2.0-style `select()`, subqueries, multi-entity joins, and the opt-out escape hatch. **All 12 passed.** Phase 2 re-encodes this as a permanent regression test.

---

## 2. COMPLEXITY ASSESSMENT

**Rating: L** — cross-module, backward-compatible schema change across 78 tables, no new service, no new infrastructure.

It is *not* XL: no new deployable unit, no message bus, no infra change. The high table count is mechanical breadth, not architectural depth — one column, one migration template, one ORM interception point.

Required sections: **3, 4, 5, 6.**

---

## 2.1 THE PROBLEM, PRECISELY

Every scheme table carries `district` and a natural-key `UNIQUE` constraint; **no taluka dimension exists anywhere in scheme data** (`src/core/base_models.py:22`, `src/schemes/s2053/subs/s20530028/models.py:29`). Taluka users are resolved to their parent district by `build_district_filter()` (`src/utils_district.py:87-91`) and `get_allowed_districts_for_user()` (15 copies, e.g. `src/schemes/s2235/subs/s22350311/helpers.py:19-21`). That is *why* taluka == district today: they read and write literally the same rows.

Two hard constraints discovered that shape the whole design:

1. **710 district predicates.** `grep` counts 671 `.district ==` plus 39 `.district.in_(` across `src/`. A naive "add a `taluka` column" would make every one of those queries silently double-count (district row + taluka rows in the same result set). Editing 710 sites is not a plan; it is a defect generator.
2. **District rows already hold real money.** `migrations/schemes/s2053/DATAINSERTION_20530019.sql` seeds non-zero values per district. Any design that derives the district figure purely from talukas destroys existing budget data on day one.

---

## 2.2 THE MODEL

One new column, `taluka`, on every district-scoped table. Its value defines a **row role**:

| `taluka` value | Role | Written by | Read by |
|---|---|---|---|
| `''` (empty string) | **Consolidated district row** — derived, never hand-edited | consolidation service only | everything that exists today (all 710 predicates, Excel, abstracts, DCO views, summaries) — **unchanged** |
| `'__district_office__'` | **District office contribution** | district assistant | consolidation service, breakdown page |
| `'<District> Taluka <Name>'` | **Taluka contribution** | that taluka's assistant | consolidation service, breakdown page |

**The invariant (single source of truth for this feature):**

```
row(taluka = '')[numeric_col]  ==  Σ row(taluka = '__district_office__')[numeric_col]
                                 + Σ row(taluka = t)[numeric_col]  for each ACTIVE taluka t
```

Non-numeric columns (`remarks`, `hra_rate`, …) are **not** summed — see §4.4.

Why empty string and not `NULL`: PostgreSQL treats `NULL`s as distinct in `UNIQUE` constraints, so `NULL` would permit duplicate consolidated rows. `''` with `NOT NULL DEFAULT ''` keeps every existing natural-key constraint enforceable after `taluka` is appended to it.

**Consequences that make this cheap:**

- Because the consolidated row keeps `taluka = ''` and holds the *total*, **Excel exports, district-wise abstracts, budget summaries, division totals, completion status and DCO views need no logic change at all.** They already read exactly the row that now holds the correct consolidated number.
- With **zero talukas active** (today's state for every district), `consolidated == __district_office__` exactly. The system is behaviourally identical to today. Activation is the only thing that makes them diverge.
- Deactivating a taluka excludes it from the roll-up and is fully reversible — rows are retained, never deleted.

**Read isolation** is enforced structurally by a single ORM interception point, not by 710 call sites (§2.3). **Write redirection** is the only per-file change, and it is two one-line edits per form (§6 Recipe R).

---

## 2.3 READ ISOLATION — ONE INTERCEPTION POINT

A request-scoped `contextvar` carries the caller's data scope. A `do_orm_execute` listener on `SessionLocal` injects `with_loader_criteria(TalukaScopedMixin, …)` into **every ORM SELECT**, for every model carrying the mixin, including subqueries, joins and column-only queries.

| Caller | Injected predicate | Effect |
|---|---|---|
| `dco`, `district`, officers, unauthenticated, **any thread with no context** | `taluka == ''` | Sees consolidated totals — identical to today |
| `taluka` level user | `taluka == <their exact unit>` | Sees only their own rows. Cannot see siblings, cannot see the consolidated row |
| Consolidation / provisioning / breakdown page | opt-in `execution_options(taluka_scope_all=True)` | Sees all rows |

**The default is `taluka == ''`, never "unfiltered".** A forgotten context (background thread, cron, misconfigured route) degrades to today's behaviour — never to a data leak and never to a double count. This is the single most important safety property of the design.

Rejected alternatives, briefly:
- *Edit 710 predicates* — unbounded defect surface.
- *Mirror `_taluka` tables (78 new tables)* — no change to reads, but doubles the schema, duplicates 78 model definitions, and needs a parallel router/template stack. Higher total cost, worse cohesion.
- *Generic JSONB contribution store* — EAV; loses type safety, `CHECK` constraints, chatbot schema introspection and Excel typing.
- *Postgres RLS* — session-variable plumbing through a `QueuePool` for local-dev-only value; deferred, not needed.

---

## 3. BLAST RADIUS

### 3.1 Tables affected — 78

| Family | Tables | Count | Column source |
|---|---|---|---|
| 4-table schemes: s2053 (10 subs), s2029 (4), s2045/20450091 (1) — `budget_post_details_*`, `post_status_*`, `post_expenses_*`, `unit_expenditure_*` | 15 × 4 | **60** | inherits `SchemeModelMixin` → one file change |
| s2235 `district_expenditure_{22350311,22350338,22353195,22353408}` | | 4 | standalone model |
| s7610 `district_expenditure_{76100149,76100158,76100167,76101871}` | | 4 | standalone model |
| s2045 lightweight `district_expenditure_{20450182,20450251,20450262}` | | 3 | one factory (`base_models.py`) |
| s6245 `district_expenditure_62450017`, s6401 `district_expenditure_64010018` | | 2 | standalone |
| s2215 `district_expenditure_2215`, s2245 `district_expenditure_2245` | | 2 | standalone |
| s0029 `district_revenue_0029`, s2075 `district_expenditure_2075` | | 2 | standalone |
| **Total** | | **78** | |

**Explicitly EXCLUDED — do not add `taluka`:**

- `sub_head_expenditure_2075` (`src/schemes/s2075/models.py:13-41`) — **has no `district` column**; it is division-level, not district-level. Adding taluka scoping here would filter every row out of existence. This is the sharpest trap in the rollout.
- `post_level_details` (`src/schemes/common/post_levels/models.py`) — child rows keyed by `(record_id, table_name, fiscal_year)`; they hang off whichever contribution row the user edits and inherit its scope transitively. Never summed.
- All core tables in `src/models.py` (`users`, `audit_logs`, `sub_schema_completions`, `district_taluka_selection`, `taluka_user_management`, `data_filling_periods`, `fiscal_years`, `pay_matrix`, `messages`, `assistant_chats`).

### 3.2 Migration SQL (backward-compatible, idempotent)

One file: `migrations/core/013_add_taluka_dimension.sql`. The runner (`src/utils_migrations.py`) executes statements one at a time inside a transaction and explicitly supports dollar-quoted `DO $$ … $$;` blocks (docstring `src/utils_migrations.py:1-13`), so the whole migration is expressed as ordered `DO` blocks over an explicit table list.

Structure (four ordered blocks — write the table list literally, do **not** derive it from `information_schema` alone, so that `sub_head_expenditure_2075` can never be picked up by accident):

```sql
-- Block 1: add column (idempotent)
ALTER TABLE <t> ADD COLUMN IF NOT EXISTS taluka VARCHAR(100) NOT NULL DEFAULT '';

-- Block 2: rebuild natural key to include taluka
ALTER TABLE <t> DROP CONSTRAINT IF EXISTS <uq_name>;
ALTER TABLE <t> ADD CONSTRAINT <uq_name> UNIQUE (<original cols…>, taluka);

-- Block 3: backfill district-office contribution rows.
-- Copies every existing row (taluka='') to a twin row with taluka='__district_office__'.
-- Column list is read from information_schema for <t>, minus 'id', with 'taluka' overridden.
-- Guarded by NOT EXISTS on (taluka='__district_office__') so re-runs are no-ops.
INSERT INTO <t> (<cols…>, taluka) SELECT <cols…>, '__district_office__' FROM <t> WHERE taluka = '';

-- Block 4: index only the 60 four-table-family tables
CREATE INDEX IF NOT EXISTS idx_<t>_scope ON <t> (fiscal_year, district, taluka);
```

> **The constraint rebuild MUST precede the backfill, and this ordering is not stylistic.** The twin row carries *identical* natural-key values to its source (only `taluka` differs). Against the pre-migration constraint — e.g. `uq_bpd_20530028_natural_key UNIQUE (fiscal_year, district, category, class_type, designation)`, `src/schemes/s2053/subs/s20530028/models.py:29` — that `INSERT` is a guaranteed duplicate-key violation and aborts the whole migration transaction on the first table. Widening the key first is what makes the backfill legal.

Notes:
- `<uq_name>` per table is discovered from `pg_constraint` by matching `contype='u'` on that table — every family was verified to have exactly one natural-key unique constraint (`uq_bpd_20530028_natural_key`, `uq_district_exp_22350311_natural_key`, `uq_district_rev_0029_natural_key`, etc.).
- Block 4 is skipped for the 18 district-expenditure tables: they hold ≤ a few hundred rows (7 districts × sections); an extra index is pure overhead.
- **Backward compatible:** an un-migrated deploy reading a migrated DB still sees the consolidated row it always saw, because the new rows are additive and every legacy query lacks a `taluka` predicate only until the ORM filter ships in the same release.
- **Rollback:** `DELETE FROM <t> WHERE taluka <> ''; ALTER TABLE <t> DROP COLUMN taluka;` restores the pre-migration state exactly. Document it in the migration header; do not automate it.

### 3.3 Dependency changes

**None.** No new packages. Everything used is already present and pinned: `SQLAlchemy==2.0.48` (`with_loader_criteria`, `do_orm_execute` — both GA since 1.4), `fastapi==0.135.2`, `psycopg2-binary==2.9.11`. `contextvars` is stdlib. Do not add Alembic — this project has its own migration runner and adding one would fork migration history.

### 3.4 New files (11)

```
src/core/taluka/__init__.py            # public surface: scope, models, services
src/core/taluka/constants.py           # DISTRICT_LEVEL, DISTRICT_OFFICE, reserved-value guards
src/core/taluka/models.py              # TalukaScopedMixin, scoped-model registry, natural_key_columns()
src/core/taluka/scope.py               # contextvar, DataScope, resolve_scope_from_request(), scope_override()
src/core/taluka/orm_filter.py          # do_orm_execute listener
src/core/taluka/middleware.py          # TalukaScopeMiddleware
src/core/taluka/provisioning.py        # contribution-row creation on activation / new FY
src/core/taluka/consolidation.py       # roll-up recompute (locking, idempotent)
src/core/taluka/write.py               # resolve_editable_row()
src/routers/ui_taluka_breakdown.py     # read-only taluka-wise breakdown page (district/DCO)
templates/taluka_breakdown.html        # its template
migrations/core/013_add_taluka_dimension.sql
tests/test_taluka_scope.py             # scope + isolation regression suite
tests/test_taluka_consolidation.py     # invariant regression suite
```

### 3.5 Modified files (~95, almost all one-to-three-line mechanical edits)

| Group | Files | Change |
|---|---|---|
| Core mixin | `src/core/base_models.py` | `SchemeModelMixin` inherits `TalukaScopedMixin` → covers 60 tables |
| Standalone models | 12 model files + `s2045/common/district_expenditure/base_models.py` | add mixin + `taluka` to `UniqueConstraint` |
| Wiring | `src/main.py`, `src/database.py` | register middleware + ORM listener |
| Generic CRUD | `src/core/secure_crud.py` | redirect update (Recipe R); route create/delete through the lifecycle helpers (Recipe D); keep district ACL. One edit covers 78 registrations |
| Activation | `src/utils_taluka_user_management.py`, `src/routers/ui_taluka_selection.py` | provision/exclude rows on activate/deactivate |
| FY seeding | 14 × `helpers.py::ensure_fiscal_year_seeded` + `s2045/common/district_expenditure/base_helpers.py` | one line: also seed contribution rows |
| Write paths | ~79 `ui_*.py` / `router_ui.py` / `*_controller.py` files | Recipe R — the edit-form GET and POST lookups |
| Hand-written API routers | 13 `router_api.py` files (schemes that do not use `secure_crud`) | Recipe R on `PUT`; Recipe D on `POST` / `DELETE` |
| Excel threading | `src/schemes/common/excel_export.py` | propagate contextvar into the export executor |
| Chatbot | `src/chatbot/core/schema_engine.py`, `src/chatbot/security/policies.py`, `src/routers/api_assistant.py` | point at district views; map taluka unit → parent district |
| Docs | `docs/ARCHITECTURE.md` | new section + updated pattern table |

**Files that deliberately change NOT AT ALL** (and the regression suite proves it): every Excel populator, `src/schemes/s2053/common/services/abstract_service.py`, `src/schemes/s2045/common/services/*`, all `ui_abstract.py` / `ui_budget_summary.py` / `ui_category_info.py`, `src/routers/completion_status.py`, `src/routers/fiscal_year.py`, `src/utils_timing.py`, all templates except the one new page.

> `src/routers/fiscal_year.py:120-155` (`clone_table_for_fiscal_year`) was read and verified: it enumerates columns from the mapper, treats non-numeric columns as clone-through and zeroes numerics via raw SQL. `taluka` is a `String`, so it clones through and all contribution rows propagate to a new fiscal year with zeroed amounts — the invariant `0 = Σ 0` holds. **No change required.** This is a load-bearing verification, not an assumption.

---

## 4. DATA & RESILIENCE

### 4.1 Transaction boundaries

The atomic unit is **one contribution write + its roll-up**:

```
BEGIN
  UPDATE contribution row              (taluka = '<unit>' or '__district_office__')
  SELECT consolidated row FOR UPDATE   (taluka = '')
  UPDATE consolidated row = Σ active contributions
  INSERT audit_logs
COMMIT
```

The consolidated row must never be visible in a state inconsistent with its contributions. Both statements share the request's existing `Session` from `get_db()` — no nested transaction, no new session. This mirrors the existing single-commit pattern in `src/schemes/s2053/subs/s20530019/ui_budget_details.py:364-373` (audit log written before `db.commit()`).

Provisioning (taluka activation) is its own transaction and is already inside one: `src/routers/ui_taluka_selection.py:199-211` calls `sync_taluka_selection_with_management()` then a single `db.commit()`. Row provisioning hooks into that same transaction, so a failed activation leaves no orphan rows.

### 4.2 Concurrency

Two talukas of the same district saving simultaneously would both recompute the same consolidated row — a classic lost update.

**Lock:** `SELECT … WHERE taluka='' AND <natural key> FOR UPDATE` before recompute, using the exact `.with_for_update()` pattern already in `src/routers/completion_status.py:113`. Lock is held for the microseconds of one aggregate; contention is bounded by talukas-per-district (max 16, Raigad).

**Lock ordering:** always consolidated row *after* the contribution row, never the reverse — a fixed global order eliminates deadlock between concurrent taluka writers.

**Recompute is a full recomputation, not a delta** (`SUM` over contributions, not `total += delta`). This is deliberate: it is idempotent, self-healing after any crash, and immune to double-application. Cost is a single indexed aggregate over ≤ 17 rows.

### 4.3 Idempotency

| Mutation | Key strategy |
|---|---|
| Contribution row provisioning | Natural key `(fiscal_year, district, taluka, …)` + `ON CONFLICT DO NOTHING`. Re-activating an already-active taluka is a no-op, never a duplicate. |
| Roll-up recompute | Full recomputation from source rows — inherently idempotent. Safe to re-run at any time; a `scripts/` reconciliation command that recomputes everything is the disaster-recovery tool. |
| Migration | `ADD COLUMN IF NOT EXISTS`, `NOT EXISTS`-guarded backfill, `DROP CONSTRAINT IF EXISTS`. Full re-run is a no-op. |

### 4.4 Column classification (the correctness trap)

Consolidation must only sum what is summable. Classification is derived from the SQLAlchemy mapper, not hardcoded:

| Class | Detection | Roll-up behaviour |
|---|---|---|
| Additive | `Integer`, `BigInteger`, `Float`, `Numeric` | `SUM()` |
| Identity / natural key | in the table's `UNIQUE` constraint, plus `id`, `scheme_code`, `sub_scheme_code` | copied from the consolidated row; never summed |
| Non-additive text | `String`, `CHAR`, `Text` outside the natural key — `remarks`, `hra_rate` | **taken from the `__district_office__` row**, never concatenated |

`hra_rate` (`CHAR(1)` in `X/Y/Z`, `src/schemes/s2053/subs/s20530028/models.py:26`) is the canonical example: summing or concatenating it produces a `CHECK` violation. `remarks` (`String(500)`) is the other. Phase 5's test suite must assert both explicitly. Use the same `isinstance(col.type, (Integer, BigInteger, Float, Numeric))` classification already proven in `src/routers/fiscal_year.py:130-136` — reuse that logic, do not reinvent it.

### 4.5 Failure handling

| Failure | Behaviour |
|---|---|
| DB down mid-write | Transaction rolls back; contribution and consolidated row stay consistent. Existing `get_db()` rollback in `src/database.py:58-66` covers it. |
| Consolidation raises | The whole write rolls back and the user gets an error. **Do not** commit the contribution and swallow the roll-up failure — a silently stale total is worse than a failed save. This is the one place where "best effort" is the wrong instinct. |
| `memory_cache` unavailable | `src/utils_cache.py` is in-process; it cannot be "down". Stale entries are the only risk — see §4.6. |
| Contextvar unset (worker thread) | Falls back to consolidated scope — today's behaviour. Fail-safe by construction. |
| Taluka row missing for a FY | Lazy provisioning on first form open; idempotent, guarded by an existence check. |
| Chatbot LLM/DB down | Unchanged — existing circuit breaker in `src/chatbot/database.py`. |

### 4.6 Caching

No new cache layer. The existing in-process `memory_cache` / `ttl_cache` (`src/utils_cache.py`) gains **scope-aware keys**, because a taluka user and a district user must never share a cache entry.

| Cache | Current key | New key | TTL | Invalidated by |
|---|---|---|---|---|
| Abstract / summary (`ttl_cache` on `SubSchemeAbstractService`, `src/schemes/s2053/common/services/abstract_service.py:72`) | `(district, fiscal_year)` | `(district, fiscal_year, scope_key)` where `scope_key` = `''` or the taluka unit | 180 s | contribution write |
| Scheme cache (`invalidate_scheme_cache(district)`, `src/schemes/s2053/subs/s20530019/helpers.py:15`) | district | unchanged — invalidate the **parent district** on any taluka write | — | contribution write |
| District completion status (`district_status_{parent}_{fy}`, `src/routers/ui_taluka_selection.py:47`) | unchanged | unchanged | 180 s | existing `invalidate_district_status_cache` |
| Chatbot schema context (`_schema_context_cache`, TTL 900 s) | `ctx:{sub_scheme_code}` | `ctx:{sub_scheme_code}` — views are static, key unchanged | 900 s | process restart |

**Invalidation trigger:** every consolidation recompute invalidates the parent district's scheme cache, using the call already present at `src/schemes/s2053/subs/s20530019/ui_budget_details.py:374-380`. The `scope_key` addition is the only structural change; forgetting it is the one way a taluka could see another taluka's numbers, so it is called out in Phase 4's test.

---

## 5. SECURITY & OBSERVABILITY

### 5.1 Input validation

| Input | Rule |
|---|---|
| `taluka` written to any row | Must be `''`, `'__district_office__'`, or a member of `get_possible_talukas_for_district(district)` (`src/utils_taluka.py:12-29`). Rejected otherwise with 400. Never taken from a form field — always derived server-side from the auth cookie. |
| Taluka user's unit | Must satisfy `is_taluka_allowed()` (`src/utils_taluka.py:42-45`) — i.e. currently selected by its district. A deactivated taluka's session cannot write. |
| Reserved values | `''` and `'__district_office__'` are rejected as taluka *names* by the activation path, so no real taluka can ever collide with a reserved role. |
| District of a taluka row | Must equal `get_district_from_taluka(auth_unit)` (`src/utils_district.py:10-14`). Existing `validate_access_control()` (`src/utils_district.py:33-61`) stays as the outer gate. |

### 5.2 Auth / authz changes

The role matrix is **unchanged**; only the row set each principal reaches changes.

| Principal | Before | After |
|---|---|---|
| taluka assistant | edits parent district's rows | edits own contribution row only; cannot see siblings or the consolidated row |
| taluka officer1/2 | read-only on district rows | read-only on own taluka's rows |
| district assistant | edits district rows | edits `__district_office__` row; **sees consolidated everywhere** (lists, summaries, abstracts, Excel) |
| district officer1/2, DCO, `dco_asst` | read-only, district/all | unchanged — consolidated |
| Completion toggle | `level == 'district'` only (`src/routers/completion_status.py:95`) | unchanged — taluka users still cannot toggle |
| Data-filling window | `DataFillingPeriod.level` already accepts `'taluka'` (`src/models.py:179`) | unchanged — already works |

**Privilege escalation to test explicitly:** a taluka user forging a district-level cookie, or passing another taluka's name in a form field. The first is bounded by the existing cookie signing; the second is impossible because `taluka` is never read from request bodies.

### 5.3 Chatbot — the raw-SQL hole

The chatbot bypasses the ORM entirely: it executes LLM-generated SQL through its own `psycopg2` pool (`src/chatbot/processors/query_execution.py:47-52`). **`with_loader_criteria` does not apply.** Without action, every chatbot aggregate double-counts on day one.

Fix — structural, not prompt-based:

1. **Create one read-only view per district-scoped table:** `v_<table>_district AS SELECT <all columns except taluka> FROM <table> WHERE taluka = ''`. Ship in the same migration.
2. **Point the chatbot at the views:** `DynamicSchemaEngine._resolve_table_names()` (`src/chatbot/core/schema_engine.py:177-182`) maps form → `table_name`; map to the view name instead. The LLM then never sees a `taluka` column and *cannot* express a query that double-counts or leaks a taluka row. Prompt changes are unnecessary and therefore not made.
3. **Taluka users:** `DivisionDistrictSecurityMixin._enforce_district_sql_scope()` (`src/chatbot/security/policies.py:82-111`) only handles `level == 'district'`. Extend it so a `taluka` level unit is mapped to its parent district via `get_district_from_taluka()` before the check. Taluka users then get their district's consolidated answers — exactly today's behaviour, no new leak surface.
4. **Explicitly out of scope:** per-taluka chatbot drill-down. It would require either a second view family plus rejection-based predicate enforcement (brittle: the LLM forgets, the user gets errors) or session-scoped RLS (infrastructure the local-dev stack does not have). The read-only breakdown page (§6 Phase 12) serves that need deterministically. **Flagging this as a deliberate scope exclusion, not an oversight.**

Also note `src/routers/api_assistant.py:136` — `unit not in allowed_districts` currently 403s taluka users for schemes that populate `SCHEME_CONFIG.districts`. Point 3 makes this consistent across all schemes rather than accidental.

### 5.4 Structured logging

Follow existing `logger.info("key=%s …", …)` style (`src/routers/completion_status.py:145-148`).

| Point | Level | Fields |
|---|---|---|
| Taluka activation → rows provisioned | INFO | `district, taluka, fiscal_year, tables, rows_created, actor` |
| Taluka deactivation | INFO | `district, taluka, rows_retained, delta_removed_from_total` |
| Consolidation recompute | DEBUG | `table, district, fiscal_year, natural_key, contributions_summed` |
| Consolidation failure | ERROR + `exc_info` | `table, district, natural_key, actor` |
| Scope resolution anomaly (taluka unit not in its district's selected list) | WARNING | `username, unit, district` |
| Recompute > 200 ms | WARNING | `table, district, duration_ms` |

**Never log** row values (budget figures) — `AuditLog.old_values/new_values` (`src/models.py:117-118`) is the sanctioned place for that, and taluka writes flow through the existing `AuditService` unchanged.

### 5.5 Metrics

In-process counters only (no Prometheus in this stack yet — that is a production-hardening task, not this one). Expose via the existing warnings/admin surface if convenient, otherwise log a periodic summary:

- consolidation recomputes per minute; p95 duration
- invariant-violation count from the reconciliation checker (§6 Phase 13) — **must be 0**
- active talukas per district
- scope-fallback count (contextvar unset) — a rising number means a code path lost its context

---

## 6. EXECUTION PHASES

**Read before implementing any phase.** Phases 1–8 are the foundation and are strictly ordered. Phases 9–11 (rollout) are mechanical repetitions of **Recipe R** and may be parallelised across agents once Phase 8 is green. Phases 12–14 close out.

---

### Recipe R — the write-path rollout recipe (referenced by Phases 9–11)

Every form in the system follows one of two shapes. Both need exactly the same three touch points and nothing else. **Read paths are never touched** — the ORM filter from Phase 2 already makes them correct.

| Touch point | Where | What |
|---|---|---|
| **R1 — edit form GET** | the handler that loads a row by `id` for rendering the form (e.g. `ui_edit_budget_detail_form`, `src/schemes/s2053/subs/s20530019/ui_budget_details.py:212-274`) | replace the `db.query(M).filter(M.id == id)` lookup with `resolve_editable_row(db, M, id, request)`; render the returned row |
| **R2 — edit form POST** | the handler that mutates the row (e.g. `ui_update_budget_detail`, same file, `:276-413`) | same replacement at `:320-325`; mutate the returned row |
| **R3 — post-commit** | immediately after `db.commit()` in R2 | call `consolidate_row()`; keep the existing `invalidate_scheme_cache()` / `invalidate_district_status_cache()` calls that already sit there (`:374-380`) |

**Why `resolve_editable_row()` takes the raw `id` and does its own load — the sharpest trap in the rollout.** A district assistant reaches the edit form from a list that shows *consolidated* rows, so the URL carries the consolidated `id`. R1 then renders the `__district_office__` row, and the form's action is built from the rendered row's id — `templates/schemes/s2053/subs/s20530019/budget_post_details_form.html:48` composes it as `'…/' + (detail.id | string) + '/edit'`. The POST therefore arrives with the *contribution* row's id, which the district scope's read filter cannot see: `query(M).filter(M.id == <district_office_id>).first()` returns `None` under `taluka == ''`. Verified empirically against SQLAlchemy 2.0.48. A handler that keeps its own filtered lookup and merely post-processes the result 404s on every district-assistant save.

The rule this enforces: **write paths must never depend on the read filter.** Both ids legitimately circulate, so the resolver accepts either.

`resolve_editable_row(db, model, row_id, request)` behaviour (implemented once, Phase 6):
1. Load by primary key with `execution_options(taluka_scope_all=True)` — unfiltered, then authorised explicitly. 404 if absent.
2. Enforce the district ACL on the loaded row via the existing `validate_access_control()` (`src/utils_district.py:33-61`) — unchanged, still the outer gate.
3. Compute the caller's writable taluka value: taluka scope → their own unit; district scope → `'__district_office__'`; read-only roles → raise (already blocked upstream by `check_edit_permission()`, `src/utils_district.py:96-109`).
4. Dispatch on the loaded row's `taluka`:
   - equals the writable value → return it (taluka users, and district re-submits)
   - `''` (consolidated) → return the sibling with the same natural key and the writable value, creating it lazily if absent
   - anything else → **403**. This is what stops a taluka user from editing a sibling's row or the district-office row by guessing an id, now that the read filter is bypassed in step 1.
5. `taluka` is never read from the request body.
6. **Total space (district callers only).** A district assistant edits the figure its own list page shows — the district *total* — not the office share. So for safe methods (`GET`/`HEAD`/`OPTIONS`) the resolver returns the **consolidated** row, and for mutating methods it returns the `__district_office__` row lifted into total space (each additive column += the active talukas' reported sum) and marked with `TOTAL_SPACE_FLAG`. `consolidate_row()` rebases a marked row to `total − Σ active talukas` under the consolidated row's lock before summing, and `400`s if the submitted total is below what the talukas already reported. A `before_commit` listener rebases any row still marked, so a handler that skips R3 cannot persist a total as a share. Taluka callers are untouched by all of this; districts with no active taluka lift by zero.

---

### Recipe D — the natural-key lifecycle recipe (create / delete)

Recipe R covers edit only, which is all the **UI** needs: every scheme UI router exposes exactly `GET ""`, `GET /{id}/edit`, `POST /{id}/edit` and exports — no create, no delete (verified across `src/schemes/s2053/subs/s20530019/ui_budget_details.py` and `src/schemes/s2235/subs/s22350311/router_ui.py`). The row set is fixed by seeding.

The **API** surface is different and must not be left undesigned: 78 `create_secure_crud_routes()` registrations plus 13 hand-written `router_api.py` modules expose `POST` and `DELETE /{id}`. Under the row-role model both break the invariant if treated as plain single-row operations:

- **Create.** Stamping `taluka` from the caller's scope gives a district caller `''` — a consolidated row holding real money with no `__district_office__` twin behind it. The invariant is violated at birth and the reconciliation checker fails on the first run.
- **Delete.** The read filter resolves a district caller's `/{id}` to the *consolidated* row. Deleting it leaves every contribution row orphaned — invisible to all reads, still counted by the checker, and resurrected as a ghost the next time consolidation runs for that key.

Both are natural-key lifecycle operations, not row operations. Two helpers in `src/core/taluka/write.py` (Phase 6):

| Helper | Behaviour |
|---|---|
| `create_row_family(db, model, values, request)` | Writes the `__district_office__` contribution row from `values`, then `consolidate_row()` materialises the consolidated row (so `consolidate_row` must upsert, not assume the `taluka=''` row exists). **Taluka-level callers are rejected with 403** — a taluka cannot introduce a district-wide natural key. Returns the consolidated row, so API response shapes are unchanged. |
| `delete_row_family(db, model, row_id, request)` | Resolves the natural key, deletes the consolidated row **and every contribution row** for that key in one transaction. **Taluka-level callers are rejected with 403.** |

Both run inside the caller's existing transaction and reuse `natural_key_columns()` (Phase 1).

---

**Verification for every rollout phase, without exception:**
1. Log in as the district assistant, edit a value, confirm the list/summary/abstract/Excel figure changes by exactly that delta.
2. Log in as a taluka assistant of a district with ≥ 2 active talukas, edit a value, confirm (a) the district figure rises by exactly that delta, (b) the other taluka's login shows no change and cannot see the edited value.
3. `pytest tests/test_taluka_consolidation.py -k <sub_scheme_code>`.

---

### Phase 1: Scope primitives and the scoped-model mixin
Scope: 4 files, ~180 LOC
Verify: `pytest tests/test_taluka_scope.py -k "constants or natural_key" -v`

#### CREATE `src/core/taluka/constants.py`
- What: `DISTRICT_LEVEL = ''`, `DISTRICT_OFFICE = '__district_office__'`, `RESERVED_TALUKA_VALUES`, and the Marathi display label for the district-office role (derive from `DISTRICTS_MR`, `src/config.py:23-33`).
- Pattern: module-level constants, same shape as `DCO_STAFF_IDENTIFIER` in `src/config.py:13`.

#### CREATE `src/core/taluka/models.py`
- What: `TalukaScopedMixin` exposing `taluka` as a `@declared_attr` column — `String(100), nullable=False, default=DISTRICT_LEVEL, server_default='', index=True`. Plus `iter_scoped_models()` (all mapped classes inheriting the mixin) and `natural_key_columns(model)` (reads the single `UniqueConstraint` from `__table_args__`, returns its columns minus `taluka`).
- Pattern: `@declared_attr` exactly as `SchemeModelMixin` in `src/core/base_models.py:9-23`. **The `@declared_attr` form is required** — a plain class attribute makes `with_loader_criteria(Mixin, lambda cls: cls.taluka …)` raise `AttributeError` at lambda-analysis time. This was hit and fixed during design verification.
- System design: `natural_key_columns()` is the backbone of write redirection and consolidation. Every family was verified to carry exactly one natural-key `UNIQUE` constraint. Raise loudly at import time if a scoped model has zero or more than one — a silent fallback here would corrupt roll-ups.

#### CREATE `src/core/taluka/scope.py`
- What: a frozen `DataScope` dataclass (`level`, `unit`, `district`, `taluka_value`), a module-level `ContextVar` defaulting to the **consolidated** scope, `resolve_scope_from_request(request)`, `current_scope()`, and a `scope_override()` context manager for services and tests.
- Pattern: cookie reads via `get_auth_level` / `get_auth_unit` / `get_auth_role` (`src/utils_auth.py:35-46`); taluka→district resolution via `get_district_from_taluka` (`src/utils_district.py:10-14`).
- System design: **the default must be consolidated, never unfiltered.** Encode that as a test, not a comment.

#### CREATE `tests/test_taluka_scope.py`
- What: constants immutability; `natural_key_columns()` against one model of each of the 5 shapes; `resolve_scope_from_request()` for dco / district / taluka / DCO-Staff / anonymous; default-scope-is-consolidated.

---

### Phase 2: ORM read filter and request wiring
Scope: 4 files, ~140 LOC
Verify: `pytest tests/test_taluka_scope.py -v` — the 12-shape isolation matrix must be green

#### CREATE `src/core/taluka/orm_filter.py`
- What: a `do_orm_execute` listener on `SessionLocal` that, for SELECTs without `execution_options(taluka_scope_all=True)`, appends `with_loader_criteria(TalukaScopedMixin, lambda cls: cls.taluka == <scope value>, include_aliases=True)`.
- Pattern: `@event.listens_for(...)` as already used in `src/database.py:41-52`.
- System design: bail out immediately on non-SELECT. `include_aliases=True` is mandatory — without it, aliased subqueries leak. The lambda closes over the scope value; verify the closure is re-evaluated per execution (SQLAlchemy's lambda caching tracks closure variables) — the Phase 2 test must assert that two different scopes in the same process return different rows, which catches an over-cached lambda.

#### CREATE `src/core/taluka/middleware.py`
- What: `TalukaScopeMiddleware` — sets the contextvar from the request on the way in, resets it on the way out (`finally`).
- Pattern: `BaseHTTPMiddleware` exactly as `AuditMiddleware` (`src/audit_middleware.py:13-45`).

#### MODIFY `src/main.py`
- What: import and register `TalukaScopeMiddleware`, and import `orm_filter` so the listener binds at startup.
- How: add alongside the existing stack at `src/main.py:486-498`. **Order matters:** register it so it runs *before* `AuditMiddleware`, i.e. add it after `AuditMiddleware` in the `add_middleware` sequence (Starlette applies middleware in reverse registration order).

#### MODIFY `tests/test_taluka_scope.py`
- What: the isolation matrix — the 12 query shapes verified during design (`query(Model)`, `query(Model.col)`, `query(func.sum)`, `with_entities(func.count)`, `group_by`, 2.0 `select()`, subquery, two-entity join, second-model isolation, opt-in escape hatch, taluka-scoped read, and cross-scope non-caching). Use an in-memory SQLite fixture with two throwaway models carrying the mixin — no PostgreSQL needed.
- System design: **this test is the contract for the entire feature.** If it ever fails, every phase downstream is unsound.

---

### Phase 3: Schema migration
Scope: 1 file, ~200 LOC SQL
Verify: restart the app (migrations auto-run on startup via `src/database.py:68-74`), then confirm — every scoped table has a `taluka` column; `SELECT count(*) FROM <t> WHERE taluka=''` equals `… WHERE taluka='__district_office__'`; `sub_head_expenditure_2075` has **no** `taluka` column; every `uq_%_natural_key` includes `taluka`.

#### CREATE `migrations/core/013_add_taluka_dimension.sql`
- What: the four ordered `DO $$ … $$;` blocks of §3.2 over the explicit 78-table list, plus the `v_<table>_district` views for the chatbot (§5.3).
- Pattern: dollar-quoted blocks — supported by the runner (`src/utils_migrations.py:1-13`); numeric prefix continues the `migrations/core/` sequence (last is `012_add_da_percentage_to_fiscal_years.sql`).
- System design: fully idempotent (§4.3). Write the 78 table names literally in a `VALUES` list inside the `DO` block — deriving them from `information_schema` risks catching `sub_head_expenditure_2075`. Include the rollback statements in a header comment, commented out. Wrap in the runner's transaction; do not add `CONCURRENTLY` (it cannot run inside a transaction and these tables are small).

---

### Phase 4: Apply the mixin to models — 4-table family (60 tables)
Scope: 2 files, ~20 LOC
Verify: `python -c "from src.main import app"` imports clean; `pytest tests/test_taluka_scope.py -v`; spot-check that `BudgetPostDetails20530028.__table__.c.taluka` exists

#### MODIFY `src/core/base_models.py`
- What: `SchemeModelMixin` additionally inherits `TalukaScopedMixin`. This single edit gives all 60 four-table-family models the column and enrolls them in the ORM filter.
- Pattern: the existing mixin-inheritance chain at `src/core/base_models.py:25,36,43`.

#### MODIFY `src/schemes/s2053/subs/s20530028/models.py`
- What: append `'taluka'` to all four `UniqueConstraint` definitions (`:29, :55, :79, :103`) so the ORM metadata matches the migrated DB.
- System design: model metadata must mirror the DB or `create_all()` on a fresh dev database produces a schema that silently permits duplicate contribution rows.

---

### Phase 5: Apply the mixin to models — standalone tables (18 tables)
Scope: 4 files per sub-phase, ~15 LOC each — run as **5a…5d**
Verify (each): app imports clean; `pytest tests/test_taluka_scope.py -v`

| Sub-phase | Files |
|---|---|
| 5a | `s2053/subs/{s20530019,s20530153,s20530233,s20530304}/models.py` — `UniqueConstraint` only (column comes from the mixin) |
| 5b | `s2053/subs/{s20530378,s20530162,s20530242,s20530313}/models.py` + `s20530387` — same |
| 5c | `s2029/subs/*/models.py` (4) + `s2045/subs/s20450091/models.py` — same |
| 5d | `s2045/common/district_expenditure/base_models.py`, `s2235/subs/*/models.py` (4), `s7610/subs/*/models.py` (4) — add mixin **and** extend `UniqueConstraint` |
| 5e | `s6245/…`, `s6401/…`, `s2215/…`, `s2245/…`, `s0029/…`, `s2075/models.py` — add mixin **and** extend `UniqueConstraint` |

- Pattern for the factory: `create_district_expenditure_model()` (`src/schemes/s2045/common/district_expenditure/base_models.py:8-90`) — add `TalukaScopedMixin` to the `type()` bases tuple and `"taluka"` to the `UniqueConstraint`; this covers 3 tables in one edit.
- **Do not touch `SubHeadExpenditure2075`** (`src/schemes/s2075/models.py:13-41`) — no `district` column, division-level table. Adding the mixin here filters every row out of every query. Re-read §3.1 before editing this file.

---

### Phase 6: Write redirection and consolidation services
Scope: 3 files, ~260 LOC
Verify: `pytest tests/test_taluka_consolidation.py -v`

#### CREATE `src/core/taluka/consolidation.py`
- What: `consolidate_row(db, model, district, fiscal_year, natural_key)` and `consolidate_district(db, model, district, fiscal_year)`. `consolidate_row()` **upserts** the `taluka=''` row — it creates it when absent rather than assuming it exists, which is what lets `create_row_family()` (Recipe D) build a natural key from its contribution side.
- Pattern: column classification reuses the `isinstance(col.type, (Integer, BigInteger, Float, Numeric))` logic from `src/routers/fiscal_year.py:130-136`; active-taluka list from `get_selected_talukas()` (`src/utils_taluka.py:31-40`) cross-checked against `TalukaUserManagement.is_active` (`src/models.py:75`).
- System design: **lock** the consolidated row with `.with_for_update()` before writing (pattern: `src/routers/completion_status.py:113`); lock order contribution→consolidated (§4.2). Full recomputation, never delta (§4.2). Runs inside the caller's transaction — no `commit()` inside this module. Non-additive columns per §4.4. Query the contribution rows with `execution_options(taluka_scope_all=True)`.

#### CREATE `src/core/taluka/write.py`
- What: `resolve_editable_row(db, model, row_id, request)` per Recipe R (all five steps, including the `taluka_scope_all=True` load and the 403 branch), plus `ensure_contribution_row()` for lazy creation, plus `create_row_family()` / `delete_row_family()` for the natural-key lifecycle (Phase 8).
- System design: validate the target `taluka` against §5.1 before returning. Never accept a taluka value from the request body. Step 1 deliberately bypasses the read filter, so steps 2 and 4 are the *only* authorisation on this path — they are not defence in depth, they are the defence. Phase 6's test asserts the 403 branch directly.

#### CREATE `tests/test_taluka_consolidation.py`
- What: the invariant under — single taluka; multiple talukas; district-office-only (no talukas active); taluka deactivation; reactivation; `hra_rate` and `remarks` non-summation; concurrent writers (two sessions); repeated recompute idempotency; a district with zero possible talukas (Mumbai City, `src/utils_taluka.py:17`); DCO Staff (`src/utils_taluka.py:13-15`); `resolve_editable_row()` reached with the consolidated id **and** with the contribution id, both resolving to the same row; its 403 branch (a taluka user passing a sibling's id, and passing the `__district_office__` id); `create_row_family()` / `delete_row_family()` leaving no orphan and no twinless row, and both 403-ing for taluka callers.

---

### Phase 7: Row provisioning on activation and fiscal-year seeding
Scope: 4 files, ~200 LOC
Verify: activate a taluka in the UI → its contribution rows exist across all implemented sub-schemes with zeroed numerics and the district total is unchanged; deactivate → total drops by exactly that taluka's contribution; reactivate → total is restored

#### CREATE `src/core/taluka/provisioning.py`
- What: `provision_taluka_rows(db, district, taluka, fiscal_year)` — for every implemented sub-scheme, for every scoped table, clone the `taluka=''` row set with zeroed numerics and `taluka=<name>`. Plus `ensure_contribution_rows(db, model, district, fiscal_year)` for lazy/idempotent top-up.
- Pattern: table discovery via `scheme_registry.get_implemented_schemes()` → `config.forms[*].table_name` (`src/core/registry.py:99-101`, `src/core/base_config.py:29`); the clone SQL mirrors `clone_table_for_fiscal_year()` (`src/routers/fiscal_year.py:120-155`) — same column enumeration, same numeric-zeroing, with `taluka` overridden and `ON CONFLICT DO NOTHING` added.
- System design: batch insert per table, one statement — activating Raigad's 16 talukas across 78 tables must not become 1 248 round trips. Runs inside the activation transaction (§4.1). Idempotent (§4.3). Skip tables belonging to unimplemented sub-schemes.

#### MODIFY `src/utils_taluka_user_management.py`
- What: `activate_taluka_users()` (`:90-142`) also provisions rows; `deactivate_taluka_users()` (`:145-179`) triggers reconsolidation of the affected district (rows retained, excluded from the roll-up).
- How: add the calls next to the existing `TalukaUserManagement` flag flips so user activation and data provisioning share one transaction.

#### MODIFY `src/routers/ui_taluka_selection.py`
- What: after `sync_taluka_selection_with_management()` (`:207`), invalidate the district status cache. Surface a provisioning failure as a real error instead of a silent partial activation.

#### MODIFY the 15 fiscal-year seeders
- What: one line in each `ensure_fiscal_year_seeded()` — after seeding district rows, call `ensure_contribution_rows()`.
- Files: `s2235/subs/*/helpers.py` (4), `s7610/subs/*/helpers.py` (4), `s6245`, `s6401`, `s2215`, `s2245`, `s0029` `helpers.py`, and `s2045/common/district_expenditure/base_helpers.py:55`. *(Split into two sub-phases of 4 files if an agent's context is tight.)*
- Note: the 4-table family needs no seeder change — `src/routers/fiscal_year.py` clones contribution rows automatically (§3.5).

---

### Phase 8: Generic CRUD API and Excel thread-context propagation
Scope: 2 files, ~60 LOC
Verify: `PUT` through a `create_secure_crud_routes` endpoint as a taluka user writes a taluka row and updates the consolidated total; `POST` as a district user yields a consolidated row **and** its `__district_office__` twin; `DELETE` as a district user leaves zero orphan contribution rows (`scripts/check_taluka_invariant.py` clean); `POST` and `DELETE` as a taluka user both 403; a taluka user's Excel export contains only that taluka's figures; a district user's export is byte-identical to pre-migration output

#### MODIFY `src/core/secure_crud.py`
- What: `update_item` routes through `resolve_editable_row()` and calls `consolidate_row()` before `db.commit()`; `create_item` routes through `create_row_family()`; `delete_item` routes through `delete_row_family()` (Recipe D). Add `taluka` to the protected-field tuple alongside `('id', 'scheme_code', 'sub_scheme_code', 'fiscal_year')` so it can never be set from a request body.
- Pattern: the existing `_check_district_access()` / `_check_write_permission()` guards stay exactly as they are — this adds a dimension, it does not replace the district ACL. One edit here covers all 78 registrations.

#### MODIFY `src/schemes/common/excel_export.py`
- What: wrap the export callable so the scope contextvar propagates into the worker thread.
- How: `contextvars.copy_context().run(export_fn)` at the `loop.run_in_executor(_export_executor, export_fn)` call (`:286`).
- System design: without this, `ThreadPoolExecutor` workers start with an empty context and fall back to consolidated scope — safe, but a taluka user would download district-wide figures. One line closes it.

---

### Phase 9: Rollout — s2053 (10 sub-schemes)
Scope: 4 files per sub-phase — run as **9a…9k**
Verify: Recipe R verification, per sub-scheme

Apply **Recipe R** to each sub-scheme's four write handlers: `ui_budget_details.py`, `ui_post_expenses.py`, `ui_post_status.py`, `ui_unit_expenditure.py`.

| Sub-phase | Sub-scheme | Files |
|---|---|---|
| 9a–9i | `s20530019`, `s20530153`, `s20530233`, `s20530304`, `s20530378`, `s20530162`, `s20530242`, `s20530313`, `s20530387` | 4 `ui_*.py` each |
| 9j | `s20530028` — refactored layout | `budget_post_details/controllers/{ui,api}_controller.py`, `post_expenses/controllers/{ui,api}_controller.py` |
| 9k | `s20530028` — remainder | `post_status/controllers/{ui,api}_controller.py`, `unit_expenditure/controllers/{ui,api}_controller.py` |

- Pattern: R1/R2/R3 anchored at `src/schemes/s2053/subs/s20530019/ui_budget_details.py:212-274` (GET), `:276-413` (POST), `:373-380` (commit + invalidate).
- **Do not touch** `ui_abstract.py`, `ui_budget_summary.py`, `ui_category_info.py`, or anything under `excel_export/` in these sub-schemes. They read the consolidated row and are already correct. Touching them is how double-counting gets reintroduced.
- Note for `s20530028` (9j/9k): the API controllers mutate rows directly; apply R2/R3 there too, not only in the UI controllers.
- Edge case for `ui_budget_details`: the post-level count guard at `:328-338` compares `SanctionedPostsCurr` against `PostLevelRepository.get_count(db_detail.id, …)`. After redirection, `db_detail.id` is the contribution row's id — which is correct, since post-level rows belong to the row actually being edited. Verify explicitly in 9a.

---

### Phase 10: Rollout — s2029 and s2045
Scope: 4 files per sub-phase — run as **10a…10e**
Verify: Recipe R verification, per sub-scheme

| Sub-phase | Files |
|---|---|
| 10a–10d | `s2029/subs/{s20290037,s20290046,s20290182,s20290262}/` — 4 `ui_*.py` each |
| 10e | `s2045/subs/s20450091/` — 4 `ui_*.py`; plus `s2045/common/district_expenditure/base_router.py` (one edit covers `20450182`, `20450251`, `20450262`) |

---

### Phase 11: Rollout — district-expenditure and section-based schemes
Scope: 4 files per sub-phase — run as **11a…11d**
Verify: Recipe R verification, per sub-scheme

| Sub-phase | Files (`router_ui.py` each) |
|---|---|
| 11a | `s2235/subs/{s22350311,s22350338,s22353195,s22353408}` |
| 11b | `s7610/subs/{s76100149,s76100158,s76100167,s76101871}` |
| 11c | `s6245/subs/s62450017`, `s6401/subs/s64010018`, `s2215/subs/s2215`, `s2245/subs/s2245` |
| 11d | `s0029/subs/s0029`, `s2075` — **`s2075` router: apply Recipe R to the `district_expenditure_2075` handlers ONLY. The `sub_head_expenditure_2075` handlers must be left completely untouched** (§3.1). |

- Pattern: R1/R2/R3 anchored at `src/schemes/s2235/subs/s22350311/router_ui.py:107-150` (GET), `:153-234` (POST), `:216` (commit).
- Section-based schemes (`s0029`, `s2215`, `s2245`) carry `table_section_code` / `account_head_code` in the natural key — `natural_key_columns()` handles this generically; no special-casing.
- **Do not touch** `ui_division_total` (`s22350311/router_ui.py:237-296`) or any `/export` handler — they read consolidated rows and are already correct.

**Sub-phases 11e–11h — the hand-written API routers.** These 13 `router_api.py` modules each expose their own `POST`, `PUT /{id}` and `DELETE /{id}` rather than going through `secure_crud`, so Phase 8's single edit does **not** cover them. Apply **Recipe R** to `PUT` and **Recipe D** to `POST` / `DELETE`.

| Sub-phase | Files (`router_api.py` each) |
|---|---|
| 11e | `s2235/subs/{s22350311,s22350338,s22353195,s22353408}` |
| 11f | `s7610/subs/{s76100149,s76100158,s76100167,s76101871}` |
| 11g | `s6245/subs/s62450017`, `s6401/subs/s64010018`, `s2215/subs/s2215`, `s2245/subs/s2245` |
| 11h | `s0029/subs/s0029` |

- **Do not touch** `src/schemes/common/post_levels/api_router.py`. `post_level_details` rows are children of whichever contribution row the user is editing (§3.1); they are never summed and carry no natural key of their own, so the lifecycle recipes do not apply. Its `DELETE /{level_id}` stays exactly as it is.

---

### Phase 12: Chatbot scoping and the read-only breakdown page
Scope: 4 files, ~220 LOC
Verify: as a district user, ask the assistant for a district total and confirm it matches the UI exactly (no double count); as a taluka user, confirm the assistant answers with the parent district's consolidated figures and refuses cross-district questions; open the breakdown page as district and DCO users; confirm taluka users get 403

#### MODIFY `src/chatbot/core/schema_engine.py`
- What: `_resolve_table_names()` (`:177-182`) returns `v_<table>_district` instead of `<table>`.
- System design: the views carry no `taluka` column, so the LLM structurally cannot express a leaking or double-counting query. No prompt change is needed — and none should be made; prompt-based enforcement is not enforcement.

#### MODIFY `src/chatbot/security/policies.py`
- What: extend `_enforce_district_sql_scope()` (`:82-111`) so a `taluka`-level unit maps to its parent district via `get_district_from_taluka()` before the ownership check.
- Pattern: the existing early-return structure at `:96-99`.

#### CREATE `src/routers/ui_taluka_breakdown.py`
- What: a read-only page for district and DCO users showing, per natural key, the district-office row, each active taluka's row, and the consolidated total.
- Pattern: router shape and auth gating from `src/routers/ui_taluka_selection.py:95-155`; scheme-aware URL prefix `/ui/s{scheme_code}/taluka-breakdown` as used there.
- System design: query with `execution_options(taluka_scope_all=True)`. Paginate (`page_size` ≤ 500, as `src/schemes/s2235/subs/s22350311/router_ui.py:40`). Deny `level == 'taluka'` with 403 — a taluka must not see siblings even read-only.

#### CREATE `templates/taluka_breakdown.html`
- What: a table — rows = natural keys, columns = district office + each active taluka + total.
- Pattern: extend `base_template` via `get_scheme_base_template(request)`, as `templates/taluka_selection.html` does; Marathi labels from `DISTRICTS_MR` and the district-office label from Phase 1.

---

### Phase 13: Reconciliation checker and full regression suite
Scope: 3 files, ~200 LOC
Verify: `pytest tests/ -v` fully green; `python scripts/check_taluka_invariant.py` reports 0 violations across all 78 tables

#### CREATE `scripts/check_taluka_invariant.py`
- What: for every scoped table × district × fiscal year, assert `consolidated == Σ active contributions`; additionally report **orphans** (a contribution row whose natural key has no `taluka=''` row) and **twinless consolidated rows** (a `taluka=''` row with no `__district_office__` sibling) — the two shapes a mishandled API `DELETE` / `POST` produces. Report violations; `--fix` re-runs consolidation.
- Pattern: standalone script using `SessionLocal` directly, as other files in `scripts/`.
- System design: this is both the CI gate and the production disaster-recovery tool. Because recompute is idempotent (§4.3), `--fix` is always safe to run.

#### CREATE `tests/test_taluka_integration.py`
- What: end-to-end per user level — district assistant edit → consolidated delta; taluka assistant edit → district delta + sibling isolation; officer read-only; DCO consolidated view; Excel export equality before/after activation with zero-valued talukas; abstract/summary equality; chatbot district total equality.

#### MODIFY `tests/` fixtures
- What: shared fixtures for a district with active talukas, a district with none (Mumbai City), and DCO Staff.
- Regression matrix that must be green: **(a)** a district with zero talukas behaves exactly as before this feature; **(b)** Excel output for such a district is byte-identical to pre-migration; **(c)** no query anywhere returns both a consolidated row and its contributions; **(d)** no taluka can read another taluka's row through any surface — UI, API, export or chatbot.

---

### Phase 14: Documentation
Scope: 2 files, ~120 LOC
Verify: `docs/ARCHITECTURE.md` describes the `src/core/taluka/` package and the row taxonomy; the pattern table lists the new pattern

#### MODIFY `docs/ARCHITECTURE.md`
- What: add `src/core/taluka/` to the `src/core/` tree (`:66-79`); add a "Taluka Consolidation" section covering the row taxonomy, the invariant, and the ORM-filter interception point; add a **Taluka Consolidation** row to the Key Architectural Patterns table (`:863-876`); note the new `taluka` column on the 78 scoped tables and the explicit exclusion of `sub_head_expenditure_2075`; add `013_add_taluka_dimension.sql` to the migrations tree (`:752-816`).

#### MODIFY `docs/CHATBOT_ARCHITECTURE_PLAN.md`
- What: record that the chatbot now reads `v_<table>_district` views, why (structural double-count prevention), and that per-taluka chatbot drill-down is deliberately out of scope with the breakdown page as its replacement.

---

## 7. WHAT THIS DESIGN DELIBERATELY DOES NOT DO

Stated explicitly so no one implements them by accident:

1. **No per-taluka Excel sheets, and no taluka breakdown inside the district export.** Government templates are fixed-layout: a district or DCO export is the consolidated figure, byte-identical to pre-migration output. A taluka user exporting gets the same template populated from their own rows — that is the ORM filter applying uniformly (Phase 8), not a new export variant. No template, populator or sheet layout changes.
2. **No per-taluka chatbot drill-down.** §5.3 point 4.
3. **No taluka-level completion toggle.** `SubSchemaCompletion` stays district-grained.
4. **No new notifications on taluka data submission.** Activation/deactivation alerts already exist (`src/notification_service.py`).
5. **No production infrastructure.** No AWS, no Redis, no Celery, no Prometheus, no Alembic. Local PostgreSQL, in-process cache, existing migration runner — as scoped.
6. **No refactor of existing schemes into microservices.** The `src/core/taluka/` package is a cohesive module inside the existing modular monolith. Every existing structure stays where it is.

---

## 8. RISK REGISTER

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | A read path bypasses the ORM (raw SQL) and double-counts | Low — only 7 `execute(text(` sites, all reviewed | Chatbot handled via views (§5.3); `fiscal_year.py` verified correct as-is; Phase 13 checker catches any regression |
| 2 | `sub_head_expenditure_2075` accidentally scoped → all rows vanish | Medium — it sits in a file with a scoped sibling | Called out in §3.1, Phase 5e and Phase 11d; literal table list in the migration |
| 3 | Non-additive column summed → `CHECK` violation on `hra_rate` | Medium | §4.4 classification + explicit test in Phase 6 |
| 4 | Cache key missing scope → cross-taluka leak | Medium | §4.6 `scope_key`; leak test is part of Phase 13's matrix (d) |
| 5 | Contextvar lost in a worker thread | Medium | Fail-safe default is consolidated (§2.3); explicitly propagated for exports (Phase 8) |
| 6 | Lost update on concurrent taluka writes | Low | `FOR UPDATE` + full recomputation (§4.2) |
| 7 | Rollout phase edits a read path "for consistency" | Medium — it looks like an omission | Every rollout phase states which files must **not** be touched |
| 8 | Row growth (78 tables roughly double) | Low | Largest table ≈ 17k rows → ≈ 34k. Indexed. Non-issue at this scale. |
| 9 | Write handler keeps its own filtered `filter(M.id == id)` lookup and only post-processes the result → every district-assistant save 404s | **High — it is the smaller-looking edit** | Recipe R makes `resolve_editable_row()` own the load; the 403 branch replaces the read filter as the authorisation. Phase 9a is the canary. |
| 10 | Migration backfill run before the constraint rebuild → duplicate-key abort on the first table | High if the block order is treated as cosmetic | §3.2 states the dependency inline; Phase 3 verification checks constraint membership before row counts. |
| 11 | API `POST`/`DELETE` treated as single-row ops → consolidated row with no twin, or orphaned contributions | Medium — 91 endpoints, none exercised by the UI | Recipe D; taluka callers 403; Phase 13 checker detects both shapes. |


File has not been read yet. Read it first before writing to it.