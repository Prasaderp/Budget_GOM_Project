# Taluka Consolidation — Remediation Plan

Technical Design Document. Companion to `docs/plan.md` (the feature plan, implemented
in commits `754d3bfb` → `e1ce2da1`). That plan's design is sound; the defects below are
**retrofit gaps** — call sites the Phase 6 write-redirection sweep missed, plus two
pre-existing latent bugs the retrofit made reachable.

Zero implementation code below. Every reference cites a file path. `[NEW]` marks
anything that does not exist yet.

---

## 0. Context status

**Context sufficient.** Files read and verified before designing:

`src/core/taluka/{write,consolidation,scope,orm_filter,constants,models,provisioning}.py`,
`src/core/secure_crud.py`, `src/core/base_models.py`, `src/main.py`,
all four `src/schemes/s2053/subs/s20530028/*/controllers/{ui,api}_controller.py`,
all four `s20530028/*/services/*_service.py` and `*/repositories/*_repository.py`,
`src/schemes/common/post_levels/{api_router,service,models}.py`,
`src/schemes/s2029/subs/s20290037/{ui_unit_expenditure,api_budget_details}.py`,
every `src/schemes/*/subs/*/{ui,api}_budget_details.py` (14 each, surveyed for the
write path, the level-count guard and the error branch),
`src/utils_district.py`, `src/utils_auth.py`, `src/utils_timing.py`,
`src/audit_service.py`, `src/routers/{auth,fiscal_year}.py`,
`templates/schemes/s2053/subs/s20530028/*_form.html`,
`templates/schemes/common/post_levels/_levels_section.html`,
`tests/{conftest,test_taluka_integration}.py`.

Two sweeps were run to bound the blast radius rather than assume it:

- every file containing a mutating route (`@router.{post,put,patch,delete}`) checked
  for `resolve_editable_row` / `create_row_family` / `delete_row_family` — the only
  gaps are the 14 `api_budget_details.py` and `post_levels/api_router.py` (C4, C5).
  `src/routers/*.py` appear in that list but touch no `TalukaScopedMixin` table.
- every `post_level_repo.get_count(...)` call site enumerated (C5b).

---

## 1. Root-cause analysis

### The mechanism, in one paragraph

`docs/plan.md` splits every scoped table into a **row family** per natural key:
a consolidated row (`taluka = ''`), a district-office contribution row
(`taluka = '__district_office__'`), and one contribution row per active taluka.
Reads go through the `do_orm_execute` listener in `src/core/taluka/orm_filter.py:36`,
which pins every ORM SELECT to `current_scope().taluka_value` — `''` for district,
DCO and anonymous callers; the taluka's own name for taluka callers. Writes go
through `resolve_editable_row()` (`src/core/taluka/write.py:45`), which deliberately
bypasses that filter and returns a **different row than the URL's id names**: for a
district caller it returns the office contribution row (a different primary key),
lifted into "district total" space.

**That id-swap is the hinge every defect below turns on.** Any code that takes the
resolved row's id and looks it up *again* through a normal (filtered) query cannot
find it. Any code that skips `resolve_editable_row()` entirely writes to the wrong
row in the family.

### Defect register

| # | Severity | Symptom | Root cause |
|---|---|---|---|
| **C1** | P0 — blocks all DCO writes | DCO assistant gets "no permission" on Edit | `_writable_taluka_value()` has no `level == 'dco'` branch |
| **C2** | P0 — 500 on every district save in s20530028 | "Record not found" → `ValueError` | Controllers re-query the resolved row's id through the read filter |
| **C3** | P0 — masks C2 | `UndefinedError: 'da_rate'` / `'relative_years'` | Error-path `render()` omits template context the success path supplies |
| **C3b** | P0 — **makes the feature's own business rule unusable** | generic 500 / "अपडेट अयशस्वी" with no reason | Every write handler catches bare `Exception`; `HTTPException(400)` from `consolidate_row()` and `403/404` from `resolve_editable_row()` are swallowed |
| **C4** | P0 — **silent data loss** | none — wrong numbers | 14 inline-edit endpoints write outside the contract |
| **C5** | P1 — silent divergence | none — wrong numbers | `post_levels` writes to the parent bypass the contract |
| **C5b** | P1 — **silent integrity loss** | none — guard never fires | Level-count guard counts against the *resolved* row id instead of the id `post_level_details` actually references |
| **C6** | P1 — pre-existing | audit trail missing for form and inline edits | `log_action()` / `log_edit()` flush after the final commit |
| **C7** | P2 — hardening | not reachable via UI | Natural-key columns mutable on the layered form path |
| **C8** | P1 — process | C1–C5b all shipped green | No HTTP-level test coverage |

---

### C1 — DCO users cannot write at all

`src/core/taluka/write.py:30-42`, `_writable_taluka_value()`:

- `level == 'taluka'` → returns the taluka's own name.
- `level == 'district'` → returns `DISTRICT_OFFICE`.
- **`level == 'dco'` falls through to `raise HTTPException(403, "Access denied")`.**

`resolve_editable_row()` calls it at line 74, *before* the safe-method branch at
line 86 — so a DCO assistant is rejected on the **GET edit form**, not just on save.
That is precisely the screenshot. It reproduces on every scheme, every sub-scheme,
every form, because `resolve_editable_row()` is the single write choke point.

Corroborating evidence this is an oversight and not a deliberate policy:

- `validate_access_control()` (`src/utils_district.py:33`) has no `dco` branch and
  returns `(True, None)` — DCO cross-district access is already granted upstream.
- `create_row_family()` (`write.py:157`) and `delete_row_family()` (`write.py:184`)
  block only `level == 'taluka'`. **A DCO assistant can create and delete rows but
  cannot open an edit form.** No coherent policy produces that.
- `check_data_filling_allowed()` (`src/utils_timing.py:50`) short-circuits to
  `(True, None)` for any level outside `['district', 'taluka']`, so a DCO assistant is
  not being blocked by the data-filling window either. `_writable_taluka_value()` is
  the only gate that rejects it.
- `src/routers/auth.py:219` seeds `dco_asst` as `level='dco', unit='KONKAN DIVISION',
  role='assistant'` — a first-class write user.

Note for the fix: a DCO's `unit` is a *division* (`KONKAN DIVISION`), never a
district. The write target must be derived from `row.district`, never from `unit`.

**Decision (confirmed with the user): a DCO assistant writes the target district's
`__district_office__` contribution row — byte-for-byte the same behaviour as that
district's own assistant.** Active talukas' contributions are preserved and the
lift/rebase cycle applies unchanged. Per-taluka drill-down editing for DCO is
explicitly out of scope; see §7.

---

### C2 — "Record not found" on every district-level form save in s20530028

Exact failing chain from the reported traceback:

```
ui_controller.py:342          service.update_form(db_detail.id, ...)
budget_post_service.py:201    record = self.repository.get_by_id(record_id, sub_scheme_code)
budget_post_repository.py:83  db.query(BudgetPostDetails).filter(id == record_id)  ← FILTERED
budget_post_service.py:203    raise ValueError("Record not found")
```

`resolve_editable_row()` returned the `__district_office__` row. `repository.get_by_id()`
is an ordinary ORM SELECT, so the `do_orm_execute` listener pins it to `taluka = ''`.
The office row is invisible to it → `None` → `ValueError`.

Why only district assistants: for a **taluka** caller the resolved row's `taluka`
equals the caller's read scope, so the re-query succeeds by coincidence. That matches
the report exactly ("assistants of any district").

The retrofit introduced this. `git diff HEAD~3 HEAD` on
`budget_post_details/controllers/ui_controller.py` shows the old line
`service.update_form(id, sub_scheme, update_dto)` replaced by
`service.update_form(db_detail.id, ...)` — swapping the id was necessary but
insufficient, because the *lookup* the service performs is the filtered one.

**Affected call sites — seven, not eight** (the only layered
controller/service/repository module in the codebase; every other scheme's router
mutates the resolved ORM object directly and is correct). Verified by reading each
service method: a site is affected **only if the service re-looks-up by id**.

| File | Line | Call | Service re-queries? |
|---|---|---|---|
| `budget_post_details/controllers/ui_controller.py` | 342 | `service.update_form(db_detail.id, …)` | yes — `budget_post_service.py:201` |
| `budget_post_details/controllers/api_controller.py` | 265 | `service.update_inline(update_dto, …)`, `id=record.id` | yes — `budget_post_service.py:118`+ |
| `unit_expenditure/controllers/ui_controller.py` | 268 | `service.update_form(…)`, `update_dto.id = db_item.id` | yes — `unit_expenditure_service.py:220` |
| `unit_expenditure/controllers/api_controller.py` | 151 | `service.update_inline(…)`, `id=record.id` | yes — same file, `get_by_id(update_dto.id)` |
| `post_expenses/controllers/ui_controller.py` | 297 | `service.update_form(db_item.id, …)` | yes — `post_expenses_service.py:199` |
| `post_expenses/controllers/api_controller.py` | 153 | `service.update_inline(update_dto, …)`, `id=record.id` | yes — `post_expenses_service.py:124` |
| `post_status/controllers/api_controller.py` | 109 | `service.update_inline(record.id, …)` | yes — `post_status_service.py:101` |
| ~~`post_status/controllers/ui_controller.py`~~ | 288 | `service.update_record(record=db_item, …)` | **no — takes the ORM object** (`post_status_service.py:195`). Not affected; do not wrap it. |

**Adjacent finding — the transaction boundary is broken on this path.**
`budget_post_repository.py:170-175`, `update()`, calls `self.db.commit()` **inside the
service**. So the controller's subsequent `db.flush()` → `consolidate_row()` →
`db.commit()` runs in a *second* transaction. Correctness currently survives only
because the `before_commit` backstop at `write.py:118` rebases the lifted row during
that first commit; but `consolidate_row()`'s `with_for_update()` lock (`consolidation.py:128`)
no longer spans the mutation, so the concurrency guarantee `docs/plan.md` §4.2 claims
is void here. Addressed in Phase 6.

---

### C3 — the 400 error page itself 500s, hiding C2

Both templates dereference variables the error-path `render()` never passes. Jinja's
default `Undefined` renders as empty text when merely printed, but **raises** on
arithmetic or attribute access — which is exactly what these two do:

| Template | Line | Expression | Raises? | Missing from error render |
|---|---|---|---|---|
| `budget_post_details_form.html` | 159 | `(detail.basic_pay\|float + detail.grade_pay\|float) * da_rate` | **yes** — arithmetic on `Undefined` | `da_rate` |
| `unit_expenditure_form.html` | 52 | `relative_years.fy_prev4.full` | **yes** — attribute access | `relative_years` |

Verified by diffing the context dicts of the success vs. error `render()` calls:

- `budget_post_details/controllers/ui_controller.py` — success L249 vs. error L378;
  missing `da_percentage`, `da_rate`, `salary_mode`. **Only `da_rate` raises.**
  `da_percentage` is consumed with `|default(64.00)` in
  `templates/schemes/common/post_levels/_levels_section.html:9`; `salary_mode` appears
  in no template. Supply all three anyway so the two render calls are symmetric — the
  next template edit must not be able to reintroduce this.
- `unit_expenditure/controllers/ui_controller.py` — success L200 vs. error L296;
  missing `relative_years`.
- `post_expenses` L329/L356 omit `nps_value` — **cosmetic only** (`{{ nps_value if item
  else '' }}` at `post_expenses_form.html:73` prints `Undefined` as empty, does not
  raise). Fix while in the file.
- `post_status` L321 — complete, no change needed.

This is **pre-existing** (the retrofit did not touch these branches) but was
effectively unreachable before.

---

### C3b — 4xx outcomes are swallowed into 500s, and the feature's own rule is invisible

C3 is only half of the broken error path. **None of the four s20530028 write handlers
has an `except HTTPException` branch**; each ends in a bare `except Exception`:

| Controller | bare `except Exception` | consequence |
|---|---|---|
| `budget_post_details/controllers/ui_controller.py` | L396 → `raise HTTPException(500)` | 500 |
| `unit_expenditure/controllers/ui_controller.py` | L307 → `raise HTTPException(500)` | 500 |
| `post_expenses/controllers/ui_controller.py` | L343 | 500 |
| `post_status/controllers/ui_controller.py` | L313 | 500 |

Three distinct `HTTPException`s are raised **inside** those `try` blocks and are
therefore all reported to the user as one opaque "An internal error occurred":

1. `consolidate_row()` → `_rebase_from_total_space()` → `HTTPException(400,
   "'<col>': district total N is below the M already entered by active talukas")`
   (`consolidation.py:100`). This is a **normal, expected** outcome — it is the
   consolidation model's one business rule, and it is the only feedback a district
   assistant can get when they under-report a total. Today it is a 500 with the reason
   deleted.
2. `resolve_editable_row()` → `HTTPException(403)` (`write.py:72/81/84`).
3. The sub-scheme mismatch → `HTTPException(404)` (e.g. `ui_controller.py:317`).

The same rule is lost more quietly in the 14 `ui_budget_details.py` files: their bare
`except Exception` (e.g. `s20530019/ui_budget_details.py:383`) renders a 400 form with
a hard-coded `"रेकॉर्ड अपडेट करण्यात अयशस्वी. कृपया पुन्हा प्रयत्न करा."` — so both
the rebase message and the "मंजूर पदे … स्तर आधीच आहेत" guard message
(`ui_budget_details.py:327`) are replaced by "try again", and retrying can never
succeed. **A dead end with no stated cause is worse than a 500**, because nothing is
logged as an error either.

Secondary, in the same area: `_rebase_from_total_space()`'s detail string is English
inside an otherwise fully Marathi UI. It becomes user-visible for the first time once
this is fixed, so it must be translated in the same change.

---

### C4 — 14 inline-edit endpoints write outside the consolidation contract

`src/schemes/*/subs/*/api_budget_details.py`, function `api_update_inline` — reference
instance `src/schemes/s2029/subs/s20290037/api_budget_details.py:216-253`:

```
record = db.query(BudgetPostDetails).filter(BudgetPostDetails.id == id, …).first()
… setattr … setattr …
db.commit()
```

No `resolve_editable_row()`. No `consolidate_row()`. The Phase 6 sweep updated the
sibling `ui_budget_details.py` in each of these directories but skipped
`api_budget_details.py`.

Consequences — **both silent, no error surfaced to the user**:

- **District / DCO caller**: the filtered read returns the **consolidated** row, so
  the edit lands directly on `taluka = ''`. It appears to work. The next time
  anything consolidates that natural key — any taluka save, any form save, any
  activation — `consolidate_row()` overwrites it with `sum(contributions)` and the
  edit is gone.
- **Taluka caller**: the edit lands on its own contribution row correctly but nothing
  rolls it up, so the district total stays stale indefinitely.

This is live, not dead code: `grep -rl "update-inline" templates/` returns **56 list
templates**. Affected files (14):

```
s2029/subs/{s20290037,s20290046,s20290182,s20290262}/api_budget_details.py
s2045/subs/s20450091/api_budget_details.py
s2053/subs/{s20530019,s20530153,s20530162,s20530233,s20530242,
            s20530304,s20530313,s20530378,s20530387}/api_budget_details.py
```

---

### C5 — `post_levels` writes to the parent bypass the contract

`src/schemes/common/post_levels/api_router.py:389`, `apply_aggregates`:

```
budget_post = service.db.query(budget_post_model).filter(id == budget_post_id, …).first()
… service.apply_aggregates_to_budget_post(budget_post_id, …)   ← writes salary columns
```

Same class as C4 — the parent is located through the read filter and mutated with no
`consolidate_row()`. District/DCO edits land on the consolidated row and are
overwritten at the next consolidation; taluka edits never propagate up.

Note for the fix: `apply_aggregates_to_budget_post()`
(`src/schemes/common/post_levels/service.py:253`) does **two** things — it reads the
levels by `budget_post_id` (L267) *and* re-queries and mutates the parent by that same
id (L270-292, including its own `self.db.commit()`). Those two ids are not the same
row once write redirection applies. See Phase 14 — passing it a single resolved id
would zero the parent out.

---

### C5b — the level-count guard is dead in ~30 call sites, not one

`post_level_details` (`src/schemes/common/post_levels/models.py`) is **not**
`TalukaScopedMixin` and is keyed by `budget_post_id` — a raw FK to a parent primary key.

**Which parent id do levels actually reference?** Every read path in
`post_levels/api_router.py` locates the parent through the *normal, filtered* query
(`get_levels` L57-61, `get_level_limit_info` L96-99, `create_level` L139-142). So a
level row always carries **the id the caller's read scope sees**: the consolidated row
for district and DCO callers, the taluka's own contribution row for taluka callers.

The retrofit changed the guard's argument from that id to the **resolved write
target's** id. For a district or DCO caller that is the `__district_office__` row, to
which no level has ever been attached, so `get_count()` returns 0 and the guard
**silently never fires** — a district assistant can set मंजूर पदे to 0 while five
levels exist. No error, no log.

Confirmed broken at every one of these (all pass a resolved-row id):

| Call site | Count |
|---|---|
| `src/schemes/*/subs/*/ui_budget_details.py` — `get_count(db_detail.id, …)` | 13 of 14 (confirm `s20290037` individually, its call is formatted differently) |
| `s20530028/budget_post_details/services/budget_post_service.py:153` (inline), `:208` (form) | 2 |
| `s20530028/budget_post_details/controllers/api_controller.py:239` — `get_count(record.id, …)` | 1 |
| `src/schemes/*/subs/*/api_budget_details.py` | currently **correct** (`record` is still the filtered/consolidated row) — but Phases 7-13 switch these to `resolve_editable_row()` and will break them unless the guard keeps the URL `id` |

**The fix is the URL path parameter, not a sibling lookup.** `id` (or
`budget_post_id`) as it arrives on the route *is* the id `post_level_details`
references, for all three caller kinds, with no extra query. Restore it. A
`_sibling()`-based lookup is only needed where the URL id is not in scope — inside
`budget_post_service.update_form()` / `update_inline()`, which receive only the
resolved id; there, pass the URL id down from the controller rather than adding a
query.

(Per-taluka level rows are naturally partitioned by `budget_post_id` and the
`uq_pld_level_name` unique constraint, so no schema change is required. A taluka
entering its own levels against its own contribution row is coherent under the
row-role model and is left as-is.)

---

### C6 — audit rows for form and inline edits are never committed

Both audit writers flush without committing: `log_action()`
(`src/audit_service.py:93-94`) and `log_edit()` (`src/audit_service.py:181-182`).
`get_db()` (`src/database.py:58-66`) closes the session without committing, so any
audit row added *after* the final `db.commit()` is discarded.

Affected — the call sits after the commit in:

- the four `s20530028/*/controllers/ui_controller.py` (`log_action`, e.g. L349 after
  the commit at L346);
- all 14 `src/schemes/*/subs/*/api_budget_details.py` (`log_edit`, e.g.
  `s20290037/api_budget_details.py:258` after the commit at L253).

Not affected: the four `s20530028/*/controllers/api_controller.py` use
`log_audit_async` (its own session), and the 14 `ui_budget_details.py` already call
`log_action` before the commit (e.g. `s20530019/ui_budget_details.py:356`).

Pre-existing — the old code had the same ordering, because `repository.update()`
already committed. The retrofit's added `db.commit()` neither caused nor fixed it.
One-line reorder; folded into the phases that already touch these files.

---

### C7 — natural-key columns are mutable on the layered form path

`BudgetPostDetails20530028`'s natural key is
`(fiscal_year, district, category, class_type, designation, taluka)`
(`src/schemes/s2053/subs/s20530028/models.py:29`). The edit form posts `District`,
`Category`, `Class` and `Designation` and the handler assigns all four.

`src/core/secure_crud.py:160-161` already made the correct decision for the generic
CRUD path — it pops `'taluka'` and `*natural_key_columns(model)` from the update
payload. The s20530028 form handlers do not.

**Not currently reachable through the UI**: the templates disable the natural-key
`<select>`s on edit and submit hidden mirrors of the row's own values
(`budget_post_details_form.html:57,68,79`; `unit_expenditure_form.html:31,43`). A
crafted POST, however, would move the office row to a new natural key while the
consolidated row and any taluka rows keep the old one — orphaning the old
consolidated row (still holding the old total, still listed) and creating a second
consolidated row from the office contribution alone. Cheap guard, real hole; ranked
P2 accordingly.

---

### C8 — no HTTP-level test coverage

`tests/test_taluka_*.py` (1,582 lines) exercise `resolve_editable_row()`,
`consolidate_row()`, the ORM filter and the invariant checker **directly against the
database**. Not one test issues a request to an actual endpoint. That is exactly why
C1–C5 shipped green: every one of them lives in the gap between a correct primitive
and its caller.

---

## 2. Complexity assessment

**L** — cross-module, multiple services, ~45 files (the bulk being one mechanical
two-line edit repeated across 14 near-identical sub-scheme directories). **No schema
change, no migration, no new dependency.** Sections 3, 4, 5, 6 apply.

The row-role model, the ORM filter, the consolidation algorithm and the provisioning
path are all correct and are **not** modified. This plan closes call-site gaps only.

---

## 3. Blast radius

### Files affected

| Group | Count | Paths |
|---|---|---|
| Core write module | 1 | `src/core/taluka/write.py` |
| Consolidation (message only) | 1 | `src/core/taluka/consolidation.py` — translate the rebase-rejection detail |
| s20530028 controllers | 8 | `s2053/subs/s20530028/{budget_post_details,unit_expenditure,post_expenses,post_status}/controllers/{ui,api}_controller.py` |
| s20530028 services/repos | 2–5 | `budget_post_details/services/budget_post_service.py` (C5b), plus `*/repositories/*_repository.py` (Phase 6 only, after caller audit) |
| Inline-edit endpoints | 14 | `src/schemes/*/subs/*/api_budget_details.py` |
| Form-edit endpoints | 14 | `src/schemes/*/subs/*/ui_budget_details.py` — C5b guard id + C3b error message only; **their write path is already correct, do not touch it** |
| Post levels | 2 | `src/schemes/common/post_levels/{api_router.py,service.py}` |
| Tests | 1 `[NEW]` | `tests/test_taluka_http.py` |
| Docs | 2 | `docs/ARCHITECTURE.md`, `docs/plan.md` |

### Schema changes

**None.** No migration. `migrations/core/013_add_taluka_dimension.sql` stands as-is.

### Dependency changes

**None.** No package added, removed or version-bumped.

### Explicitly NOT changed (verified correct, do not touch)

- `src/core/taluka/{orm_filter,scope,provisioning,constants,models}.py`
- `src/core/taluka/consolidation.py` — **logic** untouched; the only edit anywhere in
  this plan is translating the rejection message at L100-103 (Phase 1). The row-role
  model, the recompute algorithm and the `FOR UPDATE` lock stay exactly as they are.
- `src/core/taluka/middleware.py` and its registration order in `src/main.py:491`
- `src/routers/fiscal_year.py` — `clone_table_for_fiscal_year()` treats `taluka` as a
  non-numeric column and therefore clones the whole row family into the new year with
  numerics zeroed. Correct as written; **verify, do not edit.**
- The chatbot — `src/chatbot/core/schema_engine.py:179` exposes the district views
  from migration 013 (no `taluka` column), so generated SQL cannot double-count.
  `src/chatbot/security/policies.py:104` maps a taluka user to its district's
  consolidated figures. Covered by `tests/test_taluka_chatbot.py`. **Verify, do not edit.**
- Excel export services — pure ORM reads, correctly scoped by the listener.
- `templates/` — **no UI change in this plan.** The two error-path fixes are
  controller-side context additions; the templates already reference these variables.

---

## 4. Data & resilience

### Transaction boundaries

The contract from `docs/plan.md` §4.2, restated because Phase 6 exists to restore it:
**one transaction per request covering `resolve_editable_row()` → mutation →
`consolidate_row()` → `commit()`.** `consolidate_row()` takes
`SELECT … FOR UPDATE` on the consolidated row (`consolidation.py:128`); that lock is
the serialization point for concurrent district-office and taluka writers to the same
natural key. An intermediate commit releases it and the guarantee is lost.

Violated in two places today:

- the s20530028 layered path, where all four `*_repository.update()` (and `create()`)
  commit internally — `budget_post_repository.py:173`, `unit_expenditure_repository.py:214`,
  `post_expenses_repository.py:245`, `post_status_repository.py:233`. Phase 6 converts
  those to `flush()` and moves commit ownership to the controller — **after** an
  explicit audit of every caller (some callers today rely on the repository committing
  and would otherwise silently stop persisting).
- `post_levels/service.py:292`, `apply_aggregates_to_budget_post()`. Removed in
  Phase 14, which gives that path its first real transaction boundary.

### Concurrency

Unchanged and already correct:

- `consolidate_row()` is a **full recompute, never a delta** — idempotent, so
  double-application, retry and crash-recovery are all safe.
- The `before_commit` backstop (`write.py:118`) rebases any lifted row a handler
  forgot to consolidate. Keep it. It is what has been holding the s20530028 path
  together.
- `ensure_contribution_row()` (`write.py:133`) uses existence-check plus the
  natural-key `UNIQUE` constraint as backstop — safe under concurrent first-edit.

### Caching

No cache-key or TTL change. Note only the **ordering** requirement:
`CacheService.invalidate_scheme_cache(district)` must run **after** the commit, so a
concurrent reader cannot repopulate the cache from the pre-commit state. Phases 3–5
and 7–10 preserve the existing post-commit placement; do not move these calls earlier
while reordering the audit call (C6).

### Failure handling

- DB down → `get_db()` (`src/database.py:62`) rolls back and re-raises; the
  `after_soft_rollback` listener (`write.py:128`) discards the lifted-row registry so
  a recycled session cannot rebase a stale object. No change.
- `consolidate_row()` raising `HTTPException(400)` from `_rebase_from_total_space()`
  is a **normal** outcome (district total below what talukas already reported), not a
  fault. It must reach the user as its own Marathi sentence on a re-rendered form.
  Adding template context (C3) is not sufficient on its own — the exception never
  reaches that branch, because every handler catches bare `Exception` first (C3b).
  Phase 1 therefore does two things: adds the missing context **and** inserts an
  `except HTTPException` branch ahead of it. This is the single most important
  user-visible improvement in the plan.

### Idempotency

`consolidate_row()` is idempotent by construction. No new mutation in this plan needs
an idempotency key: every one is a last-write-wins field update on a single row,
followed by a full recompute.

---

## 5. Security & observability

### Auth / authz changes

One, and only one: `_writable_taluka_value()` gains a `level == 'dco'` branch (C1).
Everything else about the ACL is unchanged. Specifically preserved:

- Officers remain read-only. Handlers already reject
  `auth_role in ("officer1", "officer2", "dco")` before reaching the write path;
  the new DCO branch keys on `level`, and role-gating stays upstream where it is.
  Concretely, of the four `level='dco'` accounts seeded at `src/routers/auth.py:216-219`,
  **only `dco_asst` (`role='assistant'`) gains write**. `dco_main` (`role='dco'`),
  `dco_o1` and `dco_o2` are still stopped by that role check, one frame earlier.
- `validate_access_control()` (`utils_district.py:33`) still runs first at
  `write.py:70`, so DCO Staff isolation (`DCO_STAFF_IDENTIFIER`) and the
  taluka→parent-district check are untouched.
- The writable taluka value is **never** taken from the request body — always derived
  from the auth cookie (`write.py:31-33`). The DCO branch must honour this: derive
  from `row.district`, never from `unit` (a DCO's unit is `KONKAN DIVISION`, not a
  district) and never from a form field.

### Input validation

C7's guard is the one addition: on the layered update path, drop `taluka` and every
`natural_key_columns(model)` entry from the applied payload, mirroring
`secure_crud.py:160-161`. Bounds and type validation are unchanged.

### Structured logging

Add at existing levels, using the existing `logging` config — no new sink:

- `WARNING` in `_writable_taluka_value()` when a caller is rejected, with
  `level`, `unit`, `row.district`. Today a 403 leaves no trace, which is why C1 was
  reported as a user complaint rather than caught in a log.
- `INFO` once per fixed call site when a write is redirected from the URL id to a
  different row id (`url_id`, `resolved_id`, `taluka`, `table`). This is the single
  fact that makes the whole feature debuggable and it is currently unlogged.
- Keep `consolidation.py:160`'s existing `DEBUG` line as-is.

### Metrics

None. Local-dev Postgres, no metrics backend in the stack; adding one is
out of scope per the standing "no production infrastructure yet" constraint.

---

## 6. Execution phases

16 phases, ≤4 files each, each independently verifiable. Run in order — Phase 1 makes
every later failure legible, and Phases 2–3 are what the user is blocked on today.

Common verification prerequisite: Postgres running, app startable via
`python -m uvicorn src.main:app --reload`. There is no project-wide `verify`
command; the suite is `python -m pytest tests/ -q`.

---

### Phase 1: Make error paths renderable and 4xx outcomes legible
**Scope:** 3 files, ~40 LOC
**Verify:** `python -m pytest tests/ -q` (no regression). Then, as a district
assistant on a district that has at least one active taluka with non-zero figures,
POST a प्रपत्र ड edit lowering मंजूर पदे below what the talukas already reported.
Expect a **400 form** carrying the specific Marathi sentence — not a 500, and not
"कृपया पुन्हा प्रयत्न करा".

**[MODIFY]** `src/core/taluka/consolidation.py`
- **What:** `_rebase_from_total_space()` (L100-103) raises `HTTPException(400, …)`
  with an English detail. This string becomes user-visible for the first time in this
  phase. Translate it to Marathi, keeping the column name and both numbers.
- **System design:** this is the consolidation model's only business rule. Keep it an
  `HTTPException(400)` — do **not** convert it to `ValueError`; the api_controllers
  already map `HTTPException` to a JSON error with its own status code and would lose
  the 400 otherwise.

**[MODIFY]** `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py`
- **What — two independent changes to the same handler:**
  1. **C3:** the `except ValueError` render at L378 is missing `da_rate` (the one that
     raises), plus `da_percentage` and `salary_mode` for symmetry. Add all three.
  2. **C3b:** insert an `except HTTPException as e:` branch **before** `except
     ValueError` (order matters — `HTTPException` is an `Exception`, and Python takes
     the first matching clause). It must `db.rollback()`, then: for `e.status_code ==
     400`, re-render the same form with `"error": e.detail` and `status_code=400`; for
     anything else, `raise` unchanged so 403/404 keep their real status. Without this,
     the bare `except Exception` at L396 turns `consolidate_row()`'s 400, and
     `resolve_editable_row()`'s 403, into the same opaque 500.
- **Pattern:** copy the context derivation from the success path in the same file,
  L243-247 (`get_fiscal_year_from_request` → `get_salary_mode` / `get_da_percentage` /
  `get_da_rate`). Hoist those four lines above the `try:` so both paths share one
  computation. For the `except HTTPException` shape, the sibling
  `budget_post_details/controllers/api_controller.py:287` is the existing precedent
  (JSON rather than HTML, same intent).
- **System design:** the context lines are DB reads; hoisting them above the `try`
  guarantees they run before any `rollback()`. Keep the error render's row re-fetch as
  `service.get_by_id(id, sub_scheme)` — see the note under the next file.

**[MODIFY]** `src/schemes/s2053/subs/s20530028/unit_expenditure/controllers/ui_controller.py`
- **What:** the same two changes. The `except ValueError` render at L296 is missing
  `relative_years`; add it. Insert the same `except HTTPException` branch before it
  (the bare `except Exception` is at L307).
- **Pattern:** success path L197-210 in the same file.
- **System design — do not "fix" the error-path re-fetch.** `service.get_by_id(id,
  sub_scheme)` at L295 uses the **URL** `id`, which is the consolidated row for a
  district/DCO caller and the taluka's own row for a taluka caller — both visible
  under the read filter, so it does **not** return `None`, and it is *not* an instance
  of C2. Reusing the already-resolved `db_item` here would be actively wrong: the
  handler has just called `db.rollback()`, and on a first edit that row was INSERTed
  by `ensure_contribution_row()` inside the transaction that was rolled back, so the
  instance is gone. Leave the re-fetch as it is.

*(Do not add `nps_value` to post_expenses here — Phase 5 already opens that file.)*

---

### Phase 2: Grant DCO users the district-office write target
**Scope:** 1 file + 1 test, ~20 LOC
**Verify:** `python -m pytest tests/test_taluka_scope.py tests/test_taluka_integration.py -q`,
then log in as `dco_asst` and open an edit form for any district in any scheme —
must render, not 403.
**Expected still-broken after this phase:** a DCO *save* in s20530028 still fails —
once `_writable_taluka_value()` returns `DISTRICT_OFFICE` for a DCO, the DCO takes the
same C2 path as a district assistant. Phase 3 closes it. Do not treat that as a
regression from this phase.

**[MODIFY]** `src/core/taluka/write.py`
- **What:** add a `level == 'dco'` branch to `_writable_taluka_value()` (L30-42)
  returning `DISTRICT_OFFICE`. Place it after the `taluka` branch and before the
  `district` branch, or fold it into the district branch — the behaviour is
  identical, the DCO simply has no `unit`-to-`district` equality to check because
  `validate_access_control()` (already invoked at L74) grants DCO every district.
- **Pattern:** the existing `level == 'district'` branch at L40-41.
- **System design:**
  - **Never** derive the district from `unit` — a DCO's unit is `KONKAN DIVISION`.
    `row.district` is already the function's `district` parameter; use it.
  - Update the docstring at L45-58: it currently enumerates only taluka and district
    callers and will otherwise mislead the next reader.
  - Add the `WARNING` log on the remaining reject path (§5) — include `level`,
    `unit`, `district`.
  - Cross-check `create_row_family()` (L157) and `delete_row_family()` (L184): both
    already permit DCO. After this change all three verbs agree. State that in the
    module docstring.

**[MODIFY]** `tests/test_taluka_integration.py`
- **What:** add DCO-write coverage beside the existing
  `test_dco_sees_consolidated_total_never_raw_contributions` (L127). Assert: a DCO
  edit to district X lands on X's `__district_office__` row; the consolidated total
  moves by exactly the delta; X's active talukas' contribution rows are byte-identical
  before and after.
- **Pattern:** `test_district_assistant_edit_moves_consolidated_by_exact_delta` (L81)
  — same assertions, DCO auth context.

---

### Phase 3: Write-scope helper + budget_post_details
**Scope:** 4 files, ~55 LOC
**Verify:** log in as a district assistant, edit a प्रपत्र ड record via
संपादन, save. Expect a 303 redirect to the list with the new value visible, **not**
"Record not found". Repeat as `dco_asst` and as a taluka assistant. Then add two
levels to a post and try to save मंजूर पदे = 1 — the guard must reject it (C5b);
before this phase it silently accepts.

**[MODIFY]** `src/core/taluka/write.py`
- **What:** add `[NEW]` context manager `writable_scope(row)` — installs a `DataScope`
  whose `taluka_value` is `row.taluka`, for the duration of a service call that must
  re-read the row it was handed. This is the minimal general fix for C2: it makes the
  read filter agree with the write target for exactly the span where a legacy service
  re-queries by id, and nowhere else.
- **Pattern:** `scope_override()` in `src/core/taluka/scope.py:82` — wrap it; do not
  reimplement contextvar handling.
- **System design:**
  - Keep the span **as narrow as possible** — wrap only the service mutation call,
    never a whole handler. Everything outside must keep the caller's real scope.
  - Audited safe for the four s20530028 services: the only nested query is
    `PostLevelRepository.get_count()` against `post_level_details`, which is not
    `TalukaScopedMixin` and is therefore unaffected by the listener. Re-confirm this
    per service before wrapping; if a future service reads another scoped table
    inside the span, switch that one to passing the ORM object instead.
  - SQLAlchemy's identity map returns the *same instance* `resolve_editable_row()`
    already loaded and lifted, so no state is lost across the re-query. Note this in
    the docstring — it is non-obvious and load-bearing.

**[MODIFY]** `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py`
- **What:** wrap the `service.update_form(db_detail.id, …)` call at L342 in
  `writable_scope(db_detail)`. Pass the URL `id` alongside it as the level-count
  reference (C5b — see the service below). Separately, move the
  `AuditService.log_action(…)` call (L349-357) to **before** `db.commit()` (C6).
- **System design:** leave `CacheService.invalidate_scheme_cache()` **after** the
  commit (§4). Leave the explicit `consolidate_row()` in place — it is idempotent and
  the `before_commit` backstop currently depends on nothing.

**[MODIFY]** `src/schemes/s2053/subs/s20530028/budget_post_details/controllers/api_controller.py`
- **What:** same wrap around `service.update_inline(update_dto, sub_scheme)` (L265).
  This is the inline grid-edit path and fails identically today. Also fix C5b in the
  inline guard at L239-241: `post_level_repo.get_count(record.id, …)` must use the URL
  `id`, because `record` is the office row for a district/DCO caller and carries no
  levels. This one is already broken today, independently of C2.

**[MODIFY]** `src/schemes/s2053/subs/s20530028/budget_post_details/services/budget_post_service.py`
- **What:** the level-count guards at L153 (`update_inline`) and L208 (`update_form`)
  call `get_count(record.id, …)`, where `record` is the resolved write target. Add an
  explicit parameter for the levels reference id and have both controllers pass the
  URL `id`; use it for `get_count()` only. Everything else in these methods keeps
  operating on `record`.
- **System design:** do **not** derive it with a sibling query — the URL id is already
  the correct value and costs nothing (C5b). Default the new parameter to `record_id`
  so any caller not yet updated behaves exactly as today rather than crashing.

---

### Phase 4: unit_expenditure + post_expenses controllers
**Scope:** 4 files, ~40 LOC
**Verify:** as a district assistant, save an edit from प्रपत्र अ and प्रपत्र ब, both
via the form and via inline grid edit. Then confirm the district total equals
office + active talukas with `python scripts/check_taluka_invariant.py`.

**[MODIFY]** `.../unit_expenditure/controllers/ui_controller.py` — wrap
`service.update_form(…)` (L268) in `writable_scope(db_item)`.
**[MODIFY]** `.../unit_expenditure/controllers/api_controller.py` — wrap
`service.update_inline(…)` (L151) in `writable_scope(record)`.
**[MODIFY]** `.../post_expenses/controllers/ui_controller.py` — wrap
`service.update_form(db_item.id, …)` (L297); move `log_action` (L303) before the
commit (L301); add `nps_value` to both error renders (L329, L356); add the Phase 1
`except HTTPException` branch ahead of the bare `except Exception` at L343.
**[MODIFY]** `.../post_expenses/controllers/api_controller.py` — wrap
`service.update_inline(…)` (L153) in `writable_scope(record)`.
- **Pattern for all four:** Phase 3's `budget_post_details` changes; for the
  `except HTTPException` branch, Phase 1's.

---

### Phase 5: post_status controllers
**Scope:** 2 files, ~20 LOC
**Verify:** as a district assistant, save an edit from प्रपत्र क via form and inline.
`python -m pytest tests/ -q`.

**[MODIFY]** `.../post_status/controllers/ui_controller.py`
- **Do not wrap anything in `writable_scope`.** This handler calls
  `service.update_record(record=db_item, …)` (L288), and `update_record`
  (`post_status_service.py:195`) takes the **ORM object**, not an id — it never
  re-queries, so C2 does not apply here. This is the one site of the eight that is
  already correct; adding a scope override would be dead code.
- **What actually changes:** move `log_action` before the commit at L308 (C6), and add
  the Phase 1 `except HTTPException` branch ahead of the bare `except Exception` at
  L313 (C3b — `consolidate_row()` is inside that `try`). Note
  `resolve_editable_row()` at L280 is *outside* the `try` and already propagates
  correctly; leave it there.

**[MODIFY]** `.../post_status/controllers/api_controller.py` — wrap
`service.update_inline(record.id, …)` (L109) in `writable_scope(record)`.
- **Note:** this api_controller has no `except HTTPException` handler around
  `resolve_editable_row()` at L93, unlike its three siblings. A 403 from a taluka
  caller therefore escapes as an unhandled exception. Add the same
  `except HTTPException → JSONResponse` shape the siblings use
  (`budget_post_details/controllers/api_controller.py:287`).

---

### Phase 6: Restore the single-transaction boundary
**Scope:** 1–4 files, ~20 LOC. **Highest-risk phase — do it last among the C2 work
and do the audit step first.**
**Verify:** `python -m pytest tests/ -q`, then exercise **every** caller found in the
audit, confirming each still persists. Then `python scripts/check_taluka_invariant.py`.

**[AUDIT then MODIFY]** the four `s20530028/*/repositories/*_repository.py`
- **What:** `update()` (e.g. `budget_post_repository.py:170-175`) calls
  `self.db.commit()` internally, splitting each request into two transactions and
  releasing `consolidate_row()`'s `FOR UPDATE` lock before consolidation runs.
  Convert to **`flush()` only**, leaving commit ownership to the controller. Leave
  `create()` alone — nothing in this plan depends on it.
- **Do not add `refresh()`.** `Session.refresh()` emits an ORM SELECT, which the
  `do_orm_execute` listener scopes; refreshing the `__district_office__` row while the
  caller's scope is `''` would find nothing. It is also unnecessary — the caller
  already holds the live instance and `flush()` keeps it current.
- **Mandatory first step:** `grep -rn "repository.update(\|\.update(record" src/` and
  enumerate **every** caller. Any caller that does not itself commit must gain one.
  If the caller list is not fully enumerable with confidence, **stop and report** —
  do not convert. A missed caller silently stops persisting, which is worse than the
  lock-scope defect being fixed.
- **Pattern:** the non-layered routers already do this correctly —
  `src/schemes/s2029/subs/s20290037/ui_unit_expenditure.py:463-466`
  (`db.flush()` → `consolidate_row()` → `db.commit()`).
- **System design:** once this lands, the explicit `consolidate_row()` calls run under
  the same transaction as the mutation and the `FOR UPDATE` lock is meaningful again.
  Keep the `before_commit` backstop regardless — it is defence in depth, not a
  substitute.

---

### Phases 7–13: the 14 generic sub-schemes, two per phase

These 14 directories are near-identical copies. Each needs work in **both** of its
budget-details modules, so they are batched by directory — one agent, one directory,
full context — two directories (4 files) per phase:

| Phase | Sub-schemes |
|---|---|
| 7 | `s2029/subs/s20290037`, `s2029/subs/s20290046` |
| 8 | `s2029/subs/s20290182`, `s2029/subs/s20290262` |
| 9 | `s2045/subs/s20450091`, `s2053/subs/s20530019` |
| 10 | `s2053/subs/s20530153`, `s2053/subs/s20530162` |
| 11 | `s2053/subs/s20530233`, `s2053/subs/s20530242` |
| 12 | `s2053/subs/s20530304`, `s2053/subs/s20530313` |
| 13 | `s2053/subs/s20530378`, `s2053/subs/s20530387` |

**Scope per phase:** 4 files, ~70 LOC
**Verify per phase:** as a district assistant on a district with an active taluka —
(a) inline-edit a row from the list page, then save any form for the same natural key,
and confirm the inline edit **survives** (today it does not); (b) with two levels on a
post, try to save मंजूर पदे = 1 through both the form and the inline grid — both must
reject; (c) lower a total below what the talukas reported and confirm the form comes
back with the specific Marathi sentence, not "कृपया पुन्हा प्रयत्न करा".
After Phase 13: `python scripts/check_taluka_invariant.py` → **zero** violations.

**[MODIFY]** `<sub_scheme>/api_budget_details.py` — C4, C5b, C6
- **What:** in `api_update_inline`,
  1. replace the raw `db.query(BudgetPostDetails).filter(id == id, …).first()`
     (e.g. `s20290037` L216-219) with
     `resolve_editable_row(db, BudgetPostDetails, id, request)` plus a
     `sub_scheme_code` equality check;
  2. delete the now-redundant `validate_access_control()` block (L223-225) —
     `resolve_editable_row()` performs it at `write.py:70`;
  3. insert `db.flush()` → `consolidate_row(...)` immediately **before** the existing
     `db.commit()` (L253);
  4. move the `AuditService.log_edit(…)` call (L258) to before that commit (C6) — it
     only flushes, so where it sits today the audit row is discarded;
  5. **where a level-count guard is present in this file** (`post_level_repo.get_count(…)`
     — present in most but not all 14; `s20290037` has none), make sure it keeps using
     the URL `id`. It is correct today only because `record` was the filtered row;
     switching to `resolve_editable_row()` silently kills it otherwise (C5b).
- **Pattern:** the canonical implementation is in the sibling file
  `src/schemes/s2029/subs/s20290037/ui_unit_expenditure.py:436-466` — resolve,
  sub-scheme check, mutate, flush, `consolidate_row` with
  `natural_key_columns(Model)`, commit, then invalidate cache. Follow it exactly;
  do not invent a variant.
- **System design:**
  - Add `except HTTPException → JSONResponse({"success": False, "message": e.detail},
    e.status_code)`. `resolve_editable_row()` and `consolidate_row()` both raise
    `HTTPException`, and these are JSON endpoints — without it a 403 or the
    total-below-talukas 400 becomes an unhandled 500. The pattern is already in
    `s20530028/budget_post_details/controllers/api_controller.py:287`.
  - `consolidate_row()` must be called **before** `db.commit()`, inside the same
    transaction — that is the whole point.
  - Leave `invalidate_scheme_cache()` after the commit.

**[MODIFY]** `<sub_scheme>/ui_budget_details.py` — C5b, C3b **only**
- **What — the write path in this file is already correct; do not restructure it.**
  Exactly two changes:
  1. the level-count guard (e.g. `s20530019` L323-324) passes `db_detail.id`; change it
     to the URL `id`. `db_detail` is the office row for a district/DCO caller and
     carries no levels, so the guard is a permanent no-op today (C5b).
  2. the bare `except Exception` error render (e.g. `s20530019` L383-414) hard-codes
     `"error": "रेकॉर्ड अपडेट करण्यात अयशस्वी…"`, which erases both the guard message
     and `consolidate_row()`'s total-below-talukas message. Use the exception's own
     `detail` when it is an `HTTPException` with a 4xx status, and fall back to the
     existing string otherwise (C3b).
- **System design:** leave the `taluka_scope_all` re-fetch in that handler alone — it
  is deliberate and correct. Confirm the model import name and table-name literal per
  file before editing; these directories are near-copies but not identical.

---

### Phase 14: post_levels parent writes
**Scope:** 2 files, ~40 LOC
**Verify:** as a district assistant with active talukas — note the post's salary
figures, add two levels, click apply-aggregates. The parent must show the **sum of the
levels**, never zeros. Then save any other form for the same natural key and confirm
the applied figures survive. Repeat as a taluka assistant and as `dco_asst`.

**The trap in this phase, stated first.** `apply_aggregates_to_budget_post()`
(`service.py:253`) does two things with **one** id parameter:

```
L267  aggregates = self.calculate_aggregates(budget_post_id, …)   ← READS post_level_details
L270  budget_post = self.db.query(budget_post_model).filter(id == budget_post_id, …)  ← WRITES the parent
```

Those two ids are no longer the same row. Levels hang off the **consolidated** row id
(C5b); the write must land on the **office** row. Passing the resolved office id for
both — the obvious reading of "use `resolve_editable_row()` here" — makes
`calculate_aggregates()` find zero levels and **overwrite every salary column of the
parent with 0**. Split the two before changing anything else.

**[MODIFY]** `src/schemes/common/post_levels/service.py`
- **What:** change `apply_aggregates_to_budget_post()` to stop locating and committing
  the parent itself. It should take the **levels id** (unchanged, for
  `calculate_aggregates`) and the **resolved parent ORM object** to assign onto, then
  return the aggregates without touching the transaction. Delete the internal
  re-query at L270-277 and the `self.db.commit()` at L292 — the caller owns both.
- **System design:** the deleted `filter(fiscal_year == …, sub_scheme_code == …)`
  checks were defence-in-depth on a lookup that no longer happens here; the caller
  performs the equivalent checks before resolving. Do not silently drop them — assert
  them against the passed object instead.

**[MODIFY]** `src/schemes/common/post_levels/api_router.py`
- **What:** in `apply_aggregates` (L389): keep the existing filtered lookup at L414-417
  as the **levels/identity** row (that is the id the UI listed and the id levels are
  keyed to), keep its `access_validator` call, then additionally call
  `resolve_editable_row(db, budget_post_model, budget_post_id, request)` to get the
  **write target**, pass both into the reworked service method, and finish with
  `db.flush()` → `consolidate_row(...)` → `db.commit()`.
- **Pattern:** Phase 7's shape for the flush/consolidate/commit tail.
- **System design:**
  - No `writable_scope()` here. `post_level_details` is not `TalukaScopedMixin`, so
    the levels read is unaffected by the ORM filter either way, and the parent is
    reached through the resolved object rather than a re-query. Adding the override
    would only widen the blast radius for no gain.
  - `apply_aggregates` **sets** rather than adds. For a district/DCO caller the
    resolved office row arrives lifted into total space, so writing the level sum onto
    it means "this is the district total", and `consolidate_row()` rebases it down to
    the office share. That is the same semantics as every other district-level edit —
    keep it, do not special-case.
  - `except HTTPException: raise` already exists at L447; the new 400 from
    `consolidate_row()` therefore surfaces correctly with no extra work.

*(The s20530028 level-count guard, previously scheduled here, moved to Phase 3 — it
becomes reachable the moment Phase 3 lands and must be fixed in the same change.)*

---

### Phase 15: Natural-key immutability on the layered form path
**Scope:** 4 files, ~20 LOC
**Verify:** `python -m pytest tests/ -q`; then POST an edit with a tampered
`District` value and confirm it is ignored (row unchanged, no new consolidated row).
`python scripts/check_taluka_invariant.py` → zero violations.

**[MODIFY]** the four `s20530028/*/controllers/ui_controller.py`
- **What:** before applying the DTO, drop `taluka` and every
  `natural_key_columns(model)` entry from the payload, so a crafted POST cannot move a
  row out of its family.
- **Pattern:** `src/core/secure_crud.py:160-161` already does exactly this —
  `for protected in ('id', 'scheme_code', 'sub_scheme_code', 'fiscal_year', 'taluka',
  *natural_key_columns(model)): update_data.pop(protected, None)`. Reuse the idea;
  consider lifting it to a small shared helper in `src/core/taluka/write.py` rather
  than pasting it four times.
- **System design:** silently drop, do not 400. The UI submits hidden mirrors of the
  row's own values (`budget_post_details_form.html:57,68,79`), which are always
  identical to what is dropped — erroring would break a legitimate submit.

---

### Phase 16: HTTP-level regression suite and docs
**Scope:** 3 files, ~280 LOC
**Verify:** `python -m pytest tests/ -q` — all green, including the new file.

**[CREATE]** `tests/test_taluka_http.py`
- **What:** the coverage gap that let C1–C5b ship. Drive real endpoints with FastAPI's
  `TestClient` and auth cookies, one case per defect:
  1. District assistant POSTs a s20530028 form edit → **303**, value visible on the
     list, consolidated total moved by exactly the delta (C2).
  2. Same request when the service raises a validation error → **400 with a rendered
     form**, never a 500 (C3).
  3. District assistant POSTs a total **below** what its active talukas already
     reported → **400**, and the response body contains the specific Marathi sentence,
     not the generic "try again" string (C3b). This is the case that would have caught
     the most damaging gap and it must assert on the message text, not just the status.
  4. `dco_asst` GETs an edit form → **200**, not 403; POSTs → persists to that
     district's office row (C1).
  5. Inline-edit POST, then a form save on the same natural key → the inline value
     **survives** (C4).
  6. With N levels on a post, a district assistant POSTs `sanctioned_posts_curr < N`
     through both the form and the inline endpoint → both **rejected** (C5b). Assert on
     a district *with* active talukas, since that is the caller whose resolved row
     differs from the levels' parent.
  7. `apply-aggregates` as a district assistant with levels present → the parent's
     salary columns equal the level sum, and are **not** zero (C5 / Phase 14).
  8. Taluka assistant POSTs → only its own contribution row changes; a sibling
     taluka's row is byte-identical (isolation under the real middleware stack).
  9. Officer at every level POSTs → **403** (no privilege regression from C1).
- **Pattern:** reuse `tests/conftest.py` — `scoped_session_factory` (L75), the cookie
  request builders (L33-70, including `dco_request` at L66) and `activate_talukas`
  (L105). Add a `TestClient` fixture that exercises the real middleware chain —
  `TalukaScopeMiddleware` must run, or the tests prove nothing.
- **System design:** these must be **integration** tests through the ASGI app. A test
  that calls the controller function directly reproduces the exact blind spot being
  closed.

**[MODIFY]** `docs/ARCHITECTURE.md`
- **What:** in the taluka/consolidation section, document the four rules that were
  implicit and therefore violated:
  1. *A resolved write target's id must never be re-looked-up through a filtered
     read* — pass the object, or use `writable_scope()`.
  2. *Every mutation of a `TalukaScopedMixin` model must be followed by
     `consolidate_row()` in the same transaction.*
  3. *An id that references a scoped row from an unscoped table (`post_level_details`)
     is the **read-scope** id, never the write target's id.* Keep the two apart at
     every call site that has both.
  4. *`consolidate_row()`'s 400 is a business outcome, not a fault* — a handler that
     catches bare `Exception` around a write path is a bug.
  Add the DCO row-role entry (DCO writes the district-office contribution row).

**[MODIFY]** `docs/plan.md`
- **What:** append a short "Remediation" note pointing at this document and marking
  the Phase 6 sweep as incomplete-as-shipped (the 14 `api_budget_details.py` files and
  `post_levels/api_router.py` were never covered; the 14 `ui_budget_details.py` were
  covered for the write path but broke the level-count guard). Do not rewrite the
  original plan — it remains the record of the design.

---

## 7. Deferred — explicitly not in this plan

- **Per-taluka drill-down editing for DCO users.** A new capability, not a fix:
  needs a taluka target in the write path, a selector on `templates/taluka_breakdown.html`,
  and its own ACL. Confirmed out of scope with the user.
- **Making `post_level_details` taluka-scoped.** Not needed — `budget_post_id`
  already partitions levels per contribution row, and `uq_pld_level_name` enforces it.
  Revisit only if per-taluka level roll-up into the consolidated row is ever required.
- **Production infrastructure** (AWS, Redis, managed Postgres, metrics backend).
  Unchanged standing constraint.

---

## 8. Verification checklist (run after Phase 16)

| Check | Command / action | Expected |
|---|---|---|
| Unit + integration | `python -m pytest tests/ -q` | all pass |
| Data invariant | `python scripts/check_taluka_invariant.py` | zero violations |
| District save | district assistant, all 4 s20530028 forms | 303, value persists |
| DCO save | `dco_asst`, any district, any scheme | 200 on GET, 303 on POST |
| Under-report rejected **legibly** | district assistant sets a total below its active talukas' reported sum | 400 form showing the specific Marathi reason — never a 500, never "पुन्हा प्रयत्न करा" |
| Level guard live | district assistant with N levels sets मंजूर पदे < N, form **and** inline, in every scheme family | rejected with its own message |
| Apply-aggregates | district assistant with levels → apply | parent = level sum, not zeros |
| Audit trail | any form or inline edit | a row lands in `audit_logs` |
| Taluka isolation | taluka assistant edits | sibling taluka rows unchanged |
| Inline durability | inline edit → then any form save on same key | inline value survives |
| Officer read-only | `dco_o1` / district officer POST | 403 |
| DCO Staff isolation | `dco_staff_asst` edits | only `DCO_STAFF_IDENTIFIER` rows reachable; no taluka roll-up applies |
| Chatbot | district total question, district + taluka user | equals ORM consolidated total |
| Excel | export as district, DCO, taluka | totals match the on-screen list |
| Fiscal year | create a new fiscal year | full row family cloned, numerics zeroed |
