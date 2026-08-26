# TDD — Cross-sheet propagation प्रपत्र ड → प्रपत्र क / प्रपत्र ब for the remaining 14 sub-schemes

**Role:** Principal Systems Architect
**Status:** Design. Zero implementation code below.
**Scope:** the 14 four-table sub-schemes that are **not** `20530028`.
**Predecessor:** `docs/plan-form-d-propagation.md` — shipped in commit `eab70773` for `20530028`.
That document defines the semantics. **This document does not restate them; it generalises them.**
`docs/plan.md` (taluka consolidation) and `docs/plan-taluka-remediation.md` (write-path rules) remain
binding for both.

---

## READ THIS FIRST — what is different about this plan

The predecessor answered *"what is the relationship between the three sheets?"* It answered it once,
for one sub-scheme, against one workbook, and shipped ~1,900 lines of working code.

This plan answers a different question: **"the same government form exists in 15 sub-schemes — how do
we serve all of them without writing that code 15 times?"**

So the hard problems here are not the ones the predecessor solved:

| # | Problem | Predecessor | This plan |
|---|---|---|---|
| 1 | What do the three sheets mean? | solved, 48/48 evidence | **reused verbatim**, re-verified per sub-scheme in §2 |
| 2 | Where does the code live? | 7 files inside `s20530028/derivation/` | **extract to `src/core/derivation/`, spec-driven** (§3.1) |
| 3 | How are the write paths wired? | 4 modular controllers with services/DTOs | **14 sub-schemes use a different, flat layout** (§1.3) |
| 4 | Which designations are Group A vs Group B? | one hand-built dict, 61/64 verified | **recovered per sub-scheme from 5 more workbooks** (§2.6) |

**The single most important architectural statement in this document:**

> Copying `s20530028/derivation/` into 14 sub-schemes would add ~11,000 lines of duplicated business
> logic and 15 places to fix every future bug. It is rejected. The engine is extracted to
> `src/core/derivation/`, parameterised by a small per-sub-scheme `DerivationSpec`, and `20530028`
> becomes its first consumer — with **its four existing test files passing unchanged** as the
> regression gate (Phase 5).

---

## 0. WHAT THIS DOCUMENT ASSUMES YOU KNOW

| Concept | Source | Why it matters here |
|---|---|---|
| The whole cross-sheet model — LINK 1/2/3, the class-vocabulary trap, the Filled/Vacant ownership rule | `docs/plan-form-d-propagation.md` §2 | **Not repeated here.** Read it first; this plan is unreadable without it |
| The normative locking rule | same, AMENDMENT 1 | *A field is read-only if and only if propagation writes it.* Unchanged, applies identically to all 14 |
| The propagation algebra (STEP A–E) | same, §4.1 | Unchanged. Only its *parameters* become per-sub-scheme |
| The shipped implementation | `src/schemes/s2053/subs/s20530028/derivation/` (6 files) | The thing being extracted |
| Model-keyed hook registry | `src/core/derivation/registry.py` | Already generic — keyed on the SQLAlchemy model, not the sub-scheme |
| Taluka contribution spaces | `src/core/taluka/constants.py`, `write.py:85-208`, `consolidation.py:115-190` | Unchanged; every rule the predecessor states still holds |
| Write-path rules 1–6 | `docs/ARCHITECTURE.md` § "Taluka Data Consolidation" | Rules 5 and 6 were **added** by `eab70773` and are what this plan must satisfy 14 more times |

---

## 1. MISSING CONTEXT

**Context sufficient.** The following were read end to end before designing:

- All 15 `models.py`, all 15 `config.py`, all 15 `schemas.py`, all 15 `router_api.py`.
- The complete shipped `20530028` change set (`git show eab70773`, 36 files).
- The full flat-layout write paths of `s20530162` (the pilot) and route inventories for all 13 others.
- The shared infrastructure: `src/core/secure_crud.py`, `src/schemes/common/post_levels/api_router.py`,
  `src/core/derivation/registry.py`, `src/routers/fiscal_year.py`, `src/utils_scheme.py`.
- All 15 seed migrations (`migrations/schemes/*/DATAINSERTION_*.sql`), parsed cell by cell.
- 8 source workbooks in `Divisions/../New data (by anagha mam)/`, parsed sheet by sheet.
- The live database, all 15 sub-schemes, both fiscal years, all four tables, all taluka values.

Two business questions cannot be settled from any artefact in the repository. They are isolated in
§2.8 with a recommended default each, both currently zero-cost to get wrong (§2.4), and both
changeable by editing one dict and re-running reconcile.

### 1.1 The 14 sub-schemes in scope

Every sub-scheme whose parent is in `FOUR_TABLE_PARENT_SCHEMES` (`src/utils_scheme.py:178`) **and**
which actually declares the four forms:

| Parent | Sub-scheme | Type | Class-1 & 2 designations | Family (§7) |
|---|---|---|---|---|
| 2029 | `20290037` | charged | *(none — `Class-0`/Nirank only)* | E |
| 2029 | `20290046` | charged | 3 | D |
| 2029 | `20290182` | charged | 2 | D |
| 2029 | `20290262` | charged | *(none — `Class-0`/Nirank only)* | E |
| 2045 | `20450091` | voted | 4 | C |
| 2053 | `20530019` | charged | 2 | A |
| 2053 | `20530153` | charged | 2 | A |
| 2053 | `20530162` | voted | 2 | **A — PILOT** |
| 2053 | `20530233` | charged | 2 | A |
| 2053 | `20530242` | voted | *(none)* | B |
| 2053 | `20530304` | charged | 2 | A |
| 2053 | `20530313` | voted | *(none)* | B |
| 2053 | `20530378` | charged | 2 | A |
| 2053 | `20530387` | voted | 13 | C |

**Explicitly NOT in scope** and never to be touched by this feature:
`20450182`, `20450251`, `20450262` (parent `2045` but `district_expenditure` single-table schemes —
`src/schemes/s2045/subs/s20450182/models.py` has no `BudgetPostDetails`), and every sub-scheme under
`0029`, `2075`, `2215`, `2235`, `2245`, `6245`, `6401`, `7610`.

> **Trap.** `get_scheme_models()` (`src/utils_scheme.py:182-209`) silently falls back to
> **`20530028`'s models** when a sub-scheme has no `BudgetPostDetails`. Discovery in this feature must
> therefore **never** iterate `FOUR_TABLE_PARENT_SCHEMES`; it must iterate the derivation registry
> itself (Phase 18). This is a pre-existing latent defect in `src/routers/fiscal_year.py`;
> reproducing it here would silently reconcile `20530028` three extra times per pass.

### 1.2 The schemas are already identical — verified, not assumed

All four ORM models were compared column by column across all 15 sub-schemes:

```
budget_post_details_*   10 data columns + keys   IDENTICAL in 15/15
post_status_*            9 data columns + keys   IDENTICAL in 15/15
post_expenses_*          9 data columns + keys   IDENTICAL in 15/15
unit_expenditure_*       9 data columns + keys   IDENTICAL in 15/15
```

`CATEGORIES`, `STATUSES`, `CLASSES_SHEET3`, `HRA_RATE_MAP`, `METRICS_DB_KEYS` and `METRICS_LABELS` are
byte-identical in all 15 `config.py`. `schemas.py` is structurally identical in all 15 (differs only in
the embedded sub-scheme code string).

**This is why one engine is correct and not an over-abstraction: the abstraction already exists in the
data model; only the code failed to express it.**

### 1.3 THE STRUCTURAL DIFFERENCE — 20530028 is modular, the other 14 are flat

This is the largest source of per-sub-scheme work and the thing most likely to be underestimated.

```
s20530028/                              s20530162/   (and the 13 others)
  budget_post_details/                    ui_budget_details.py        (494 L)
    controllers/{ui,api}_controller.py    api_budget_details.py       (365 L)
    services/ repositories/ dto/ utils/   ui_post_status.py          (1028 L)
  post_status/    (same 5 layers)         ui_post_expenses.py         (892 L)
  post_expenses/  (same 5 layers)         ui_unit_expenditure.py      (607 L)
  unit_expenditure/                       helpers.py schemas.py config.py models.py
  derivation/     (6 files)               router_api.py router_ui.py
```

The flat modules inline everything the modular one puts in a service + DTO + validator. There is **no
`PostExpensesService`, no `PostStatusService`, no `*UpdateDTO`, and no `utils/validators.py`** to hook
into. The predecessor's Phase 7 and Phase 8 edits therefore cannot be transplanted — their anchors do
not exist.

**Consequence for the design (§3.1):** the per-controller work must be reduced to a handful of calls
into a shared binding module, or the flat controllers will each grow ~120 lines of near-identical
logic — 14 times.

Two further layout facts that matter:

- `20530019/153/162/233/242/304/313/378/387` and `20450091` each carry a `shared/` package
  (`shared/services/audit_service.py`, `shared/utils/validators.py`).
- **The four `2029` sub-schemes do not.** They import `from src.audit_service import AuditService`
  directly (`s20290182/ui_budget_details.py:27`). See §2.7 A-3.
- **`20530028/shared/` is already cross-sub-scheme infrastructure.** The nine `2053` sub-schemes'
  `helpers.py` each import `CacheService`, `get_no_cache_headers` and `validate_numeric_inputs` from
  `src.schemes.s2053.subs.s20530028.shared.*` (e.g. `s20530162/helpers.py:6-8`). **Phase 5 must not
  delete or relocate that package** — only the five `derivation/` modules inside `20530028` move.
  `20450091` has its own `shared/` and does not import `20530028`'s.

### 1.4 THE WRITE-PATH INVENTORY — exactly six routes per sub-scheme, verified for all 14

Enumerated by grepping every `@router.post/put/delete` in every flat module of all 14 sub-schemes.
The result is perfectly uniform; there is no sub-scheme with a seventh mutating route and none missing
one.

| # | Route | File | Table | Role |
|---|---|---|---|---|
| 1 | `POST /ui/s{sub}/budget-post-details/{id}/edit` | `ui_budget_details.py` | प्रपत्र ड | **trigger** |
| 2 | `POST /ui/s{sub}/budget-post-details/api/update-inline` | `api_budget_details.py` | प्रपत्र ड | **trigger** |
| 3 | `POST /ui/s{sub}/post-expenses/{id}/edit` | `ui_post_expenses.py` | प्रपत्र ब | **trigger** + derived field |
| 4 | `POST /ui/s{sub}/post-expenses/api/update-inline` | `ui_post_expenses.py` | प्रपत्र ब | **trigger** + derived field |
| 5 | `POST /ui/s{sub}/post-status/{id}/edit` | `ui_post_status.py` | प्रपत्र क | allocation |
| 6 | `POST /ui/s{sub}/post-status/api/update-inline` | `ui_post_status.py` | प्रपत्र क | allocation |

Plus three families of route that are **already generic and need no per-sub-scheme change**:

| Route family | Wiring | Status |
|---|---|---|
| `POST/PUT/DELETE /api/schemes/{sub}/budget-post-details` | `create_secure_crud_routes()` calls `run_for(db, model, …)` at `secure_crud.py:157,180,214` | **generic — works the moment the model is registered** |
| post-levels create/update/delete + `apply-aggregates` | `create_post_levels_router(budget_post_model, …)` calls `run_for(db, budget_post_model, …)` at `post_levels/api_router.py:482` | **generic — already wired in all 14** (`api_budget_details.py`, one call each) |
| the `apply-aggregates` page-load defect | fixed globally in `static/js/post_levels.js` by `eab70773` | **already fixed for all 14** |

> This is the single biggest saving in the plan. The predecessor's Phase 0, Phase 6 and half of
> Phase 5 were **global** work. They are done. Re-doing them is the most likely wasted effort here.

---

## 2. EVIDENCE — the cross-sheet model, re-verified per sub-scheme

The predecessor recovered LINK 1/2/3 from the `20530028` workbook. This section establishes the same
links for the other 14, **and is explicit about where the evidence is thin.**

### 2.1 The workbooks are the same government form

Eight source workbooks exist for sub-schemes in this scope, in
`Divisions/../New data (by anagha mam)/`. Every one has the same sheet set and the same block layout:

```
Page 1  = प्रपत्र ड   अ.क्र. | वर्ग | पद | मंजूर पदे ×2 | विशेष वेतन | मुळ वेतन | ग्रेड वेतन | एकूण |
                     महागाई भत्ता 64% | स्थानिक पुरक भत्ता | घर भाडे भत्ता | वाहन भत्ता |
                     धूलाई भत्ता | रोख भत्ता | चप्पल भत्ता/इतर | एकूण
Page 2  = प्रपत्र क   11 measure rows × (भरलेली | रिक्त) × (वर्ग-1 व 2 | वर्ग-3 | वर्ग-4)
Page 3  = प्रपत्र ब   मंजूर पदे: वर्ग 1..4 × (स्थायी | अस्थायी) × (भरलेली | रिक्त)
                     + a district expense table (वैद्यकिय / उत्सव / स्वग्राम / NPS·7th-pay / इतर)
Page 4  = प्रपत्र अ   unit_expenditure
```

**Same columns, same rows, same class vocabularies, same measure labels.** LINK 1, LINK 2 and LINK 3
are therefore properties of *the form*, not of one sub-scheme's copy of it. That is the mandate for
one engine.

*Format note.* Unlike the `20530028` workbook (an ODS file named `.xls` — predecessor §0.1), **these
eight are genuine OLE2/BIFF `.xls`** (magic `d0cf11e0`) and `xlrd` reads them directly. Any tooling
must sniff the magic bytes rather than assume either format.

Only cosmetic label drift was found, none of it structural: `20530313`'s प्रपत्र क labels the travel
row `प्रवास भत्ता/कायम प्रवास भत्ता`; `20530387` inserts explicit `एकूण (वर्ग-N)` subtotal rows
inside each प्रपत्र ड block and heads its blocks `उप आयुक्त (सा.प्र.) कोकण विभाग` instead of
`जिल्हा …`; the `2029` workbooks carry both `7 व्या वेतन आयोग फरक` **and** `एनपीएस` columns in the
प्रपत्र ब expense table. Any workbook-reading tool must key on **position and header text**, never on
a fixed row index.

### 2.2 LINK 2 — प्रपत्र ड class totals == प्रपत्र ब मंजूर पदे. Exact, everywhere it can be tested

Per `(district, category)` block, `Σ sanctioned_posts_curr` per class versus `भरलेली + रिक्त` in
प्रपत्र ब:

| Workbook | Blocks tested | Class-3 | Class-4 | Class-1 & 2 total |
|---|---|---|---|---|
| `20530162` | 14 | **14/14** | **14/14** | **14/14** |
| `20450091` | 14 | **14/14** | **14/14** | **14/14** |
| `20530242` | 14 | **14/14** | **14/14** | **14/14** |
| `20530313` | 13 | **13/13** | **13/13** | **13/13** |
| `20530387` | 2 | **2/2** | **2/2** | 1/2 — accounted for in §2.6 |

**LINK 2 is not approximate in any sub-scheme.** Combined with the predecessor's 95/96 for
`20530028`, the link is now verified in six independent workbooks.

The three `2029` workbooks (`20290046`, `20290182`, `20290262`) are **entirely blank** — every
प्रपत्र ड, क and ब cell is zero or empty. They confirm the *structure* and contribute no arithmetic
evidence. `20290037`, `20530019`, `20530153`, `20530233`, `20530304` and `20530378` have no workbook
in the repository at all. This is stated, not hidden; §2.6 says exactly what each mapping rests on.

### 2.3 LINK 1 — structurally identical, and why the numeric test on the seeds is uninformative

Running the predecessor's Test A against the **seed migrations** produces, at first glance, alarming
hit rates for the 14 — e.g. `20530162` scores `posts 17/48`.

**Do not act on that number. It is measuring a seed defect, not the link.** Fingerprinting every seed
dataset by content hash proves the seeds are copies:

| Table | Identical seed shared by |
|---|---|
| `post_status_*` | `20450091`, `20530019`, `20530153`, `20530162`, `20530233`, `20530242`, `20530304`, `20530313`, `20530378` — **9 sub-schemes, one dataset** |
| `post_status_*` | `20290037`, `20290046`, `20290182` — 3 sub-schemes, one dataset |
| `post_expenses_*` | the same 9, and separately the same 3 |
| `budget_post_details_*` | `20530019`, `20530153`, `20530162`, `20530233`, `20530304`, `20530378` — **6 sub-schemes, one dataset** |
| `budget_post_details_*` | `20290037`, `20290262` — 2 sub-schemes, one dataset |

Only `20530028` has three genuinely distinct seeded forms, and it is the only one with a matching
workbook in the repository. **The seeded प्रपत्र क and प्रपत्र ब for the other 14 are placeholder
content copy-pasted between sub-schemes.** Comparing प्रपत्र ड against a placeholder प्रपत्र क
measures the copy-paste, nothing else.

**What LINK 1 rests on instead, and why that is the stronger footing:**

1. It is an identity of the *form*: प्रपत्र क's nine stored measures are, by the form's own column
   headings, the class-wise sums of प्रपत्र ड's columns E, G, H, F, J, K, L, M and (N+O+P). §2.1
   shows all 15 sub-schemes use that identical form.
2. The predecessor proved that identity numerically at **48/48 cells × 9 measures** on the one
   sub-scheme where a real workbook and a faithful seed both exist.
3. LINK 2 — which shares the same `Σ sanctioned_posts_curr` aggregation over the same block
   structure — is verified 100 % in five further workbooks (§2.2).

**Operational consequence, and it is the reason this rollout is safe: the live database currently
holds no data to disagree with.**

### 2.4 THE LIVE DATABASE IS EMPTY — the decisive rollout fact

Counted directly against the production database, across **both** fiscal years and **all** taluka
values, rows where any data column is non-zero:

| Sub-scheme | प्रपत्र ड | प्रपत्र क | प्रपत्र ब posts | प्रपत्र ब expenses | post levels |
|---|---|---|---|---|---|
| `20290037` `20290046` `20290182` `20290262` `20450091` `20530019` `20530153` `20530162` `20530233` `20530304` `20530313` `20530378` `20530387` (13) | **0** | **0** | **0** | **0** | **0** |
| `20530242` | 2 | **0** | **0** | **0** | 0 |
| *(`20530028`, already shipped)* | 2 | 2 | 2 | 0 | 1 |

> **`reconcile --fix` across all 14 sub-schemes writes at most one cell** (`20530242`,
> Palghar/Permanent/Class-3, `posts 0 → 1` — the one place a non-zero प्रपत्र ड row exists with a zero
> प्रपत्र क counterpart). There is no user data to destroy, no allocation to preserve, and no data
> migration to write.
>
> **This feature should ship before the client begins data entry.** Every week of delay converts a
> zero-risk rollout into a data-reconciliation problem.

### 2.5 WHAT IS DELIBERATELY NOT CONNECTED — unchanged from the predecessor

The predecessor's §2.6 table applies verbatim to all 14. Restated in summary only, because "connect
everything" is the failure mode this section exists to prevent:

`sanctioned_posts_prev1` · `hra_rate` · प्रपत्र ड's two `एकूण` display columns · प्रपत्र क's two
`एकूण` display rows · प्रपत्र ब's `filled_posts` (**user input**) · प्रपत्र ब's entire district
expense table incl. its `other` (**user-owned, no dimension in common with प्रपत्र ड**) · प्रपत्र अ
(`unit_expenditure`) · every intra-sheet formula.

Two names to re-flag, because both recur in all 14:

- **`other` means two unrelated things.** प्रपत्र क `other` = `washing + cash + footwear` from
  प्रपत्र ड. प्रपत्र ब `other` = a district expense line. Same column name, no relationship. **A spec
  that lets propagation reach प्रपत्र ब's `other` is a data-loss bug.** The engine must therefore keep
  `derived_post_expenses_fields = ('vacant_posts',)` as a hard, asserted allowlist —
  `service.py:_record_changes` already raises `AssertionError` on a non-derived write, and that guard
  is load-bearing and must survive the extraction.
- **The district-wide expense fan-out stays exactly as-is.** In every flat sub-scheme,
  `ui_post_expenses.py` fans the five expense fields across the whole district in one `UPDATE`
  at `s20530162/ui_post_expenses.py:183-197` (the API inline route) and `:681-695` (the form route), both via `build_post_expenses_district_sync_update` (`src/schemes/common/utils.py:50`). It touches
  **both** categories, which is why §4.2 requires locking both.

### 2.6 THE PAY-CLASS BOUNDARY — recovered per sub-scheme, with its confidence stated

`DESIGNATION_PAY_CLASS` splits प्रपत्र ड's `Class-1 & 2` into प्रपत्र ब's `'1'` and `'2'`. It is the
only genuinely new domain knowledge per sub-scheme. It was recovered by solving, over every
`(district, category)` block of each workbook, the assignment that reproduces प्रपत्र ब's class-1 and
class-2 post counts.

**Family A — `20530019`, `20530153`, `20530162`, `20530233`, `20530304`, `20530378`**

```
'1':  Sub-Divisional Officer        (उपविभागीय अधिकारी)
'2':  Naib Tehsildar                (नायब तहसिलदार)
```

Derived from the `20530162` workbook: **28/28 cells exact, and the unique solution** — the brute force
over all 2² assignments has exactly one perfect fit. The other five sub-schemes have a Class-1 & 2
designation set that is *string-identical* to `20530162`'s, so the mapping transfers.
`Naib Tehsildar = '2'` is independently confirmed by the `20530387`, `20450091` and `20530028`
workbooks.

**Family C — `20450091`**

```
'1':  Sub-District Officer                        (उपजिल्हाधिकारी)            ← constrained, exact
'1':  Tehsildar/Tax Collection Officer            (तहसिलदार/करमणूक कर अधि.)   ← constrained, exact
'2':  Naib Tehsildar/Asst Tax Collection Officer  (ना.तह./सहा.करमणूक कर अधि.) ← constrained, exact
'1':  Deputy Commissioner                         (उप आयुक्त)                  ← UNCONSTRAINED (§2.8 D-1)
```

14/14 blocks fit exactly. `Deputy Commissioner` has zero posts in every block, so the workbook cannot
distinguish `'1'` from `'2'` for it; a naive best-fit search reports `'2'` purely because that is the
first value it tries. **Assign `'1'` on cadre** — a divisional Deputy Commissioner is Group A.
Recorded as D-1.

*(The workbook spells the tax posts `करमणूक कर` while `config.DESIGNATIONS_MR` spells them
`करसमापूक कर`. Irrelevant: the dict is keyed on the **English `config.DESIGNATIONS` string**, which is
what the DB stores. Marathi appears in this document only as evidence — the same rule the predecessor
set in its §2.3b.)*

**Family C — `20530387`** (13 Class-1 & 2 designations, single district `DCO Staff`)

```
'1':  Divisional Commissioner · Additional Commissioner · Tehsildar ·
      Deputy Commissioner · Deputy Collector ·
      Assistant Director Town Planning · Assistant Director
'2':  Naib Tehsildar · Naib Tehsildar (Ulhasnagar) · Accounts Officer ·
      Planning Assistant · Assistant Accounts Officer · Law Officer (Honorarium)
```

Derived exactly:

- **Permanent** — प्रपत्र ड `वर्ग-1 व 2` = विभागीय आयुक्त 1 + अपर आयुक्त 1 + तहसिलदार 3 +
  नायब तहसिलदार 2 = 7. प्रपत्र ब = class1 (4+1) = 5, class2 (2+0) = 2. `5 = 1+1+3`, `2 = 2`. **Exact.**
- **Temporary** — प्रपत्र ड = 13. प्रपत्र ब = class1 5, class2 7, total 12. `5 = 2+1+1+1`,
  `7 = 3+1+1+1+1`. The residual `+1` is **`Law Officer (Honorarium)`, whose basic pay is 0 and which
  the preparer omitted from प्रपत्र ब** — the same class of one-district variance the predecessor
  documented for Raigad/Temporary. Assign `'2'`, matching `20530028`'s treatment of the identical
  designation.

**Trap — `20530387` designation string drift.** `config.DESIGNATIONS` and the seeded rows disagree:
the DB contains `Cashier/Senior Pay Scale/Recovery Agent/Rent Collector` while the config lists
`Cashier/Senior Pay Scale`, `Clerk/Rent Collector`, `Clerk/Recovery Agent` and `Laborer`. All four are
`Class-3`/`Class-4`, so none reaches the lookup — but the same class of drift *would* silently break a
Class-1 & 2 mapping, and an unmapped designation defaults to `'2'` (under-reporting the gazetted
count). **Phase 7 creates a test that pins this for all 15 sub-schemes.**

**Family D — `20290046`, `20290182`** (workbooks blank; assigned on cadre)

```
20290046   '1': Deputy Collector/Expert Officer · City Architect
           '2': Assistant City Architect                        ← §2.8 D-2
20290182   '1': Deputy Collector/Expert Officer
           '2': Naib Tehsildar                                  ← settled by 4 other workbooks
```

**Families B and E — `20530242`, `20530313`, `20290037`, `20290262`**

`DESIGNATION_PAY_CLASS = {}`. None of these four has a single `Class-1 & 2` designation in either its
config or its seed, so the lookup is never reached. An empty dict is the correct and complete answer,
not a gap.

**Note — the same name can sit in a different class in a different sub-scheme.** `20290182` places
`Sub-Divisional Officer` in `Class-3`, whereas Family A places it in `Class-1 & 2`. This is not a
conflict: `pay_class_for()` tests `class_type` **first**, so a Class-3 row resolves to `'3'` and never
consults the dict. The dict is only ever consulted for `Class-1 & 2` rows. Keep it that way.

### 2.7 THE ANOMALIES — three, each able to corrupt a column or a log silently

**A-1 · `Class-0` / `Nirank` — a class value that is in no config.**
`20290037` and `20290262` carry 8 प्रपत्र ड rows each with `class_type = 'Class-0'` and
`designation = 'Nirank'`, in both the seed and the live DB — while their `config.CLASSES_SHEET1_2`
lists only the usual three. The workbook shows why: `निरंक` ("nil") is a literal placeholder row the
preparer writes when a category has **no posts at all**, and its `वर्ग` cell is left blank
(`Budget 20290262 …xls` Page 1, rows 13 and 28). Every value on it is zero.

Today `pay_class_for()` raises `ValueError` for anything outside the three classes, and
`aggregate_pay_classes()` catches it and emits `logger.warning` **per row, per request**
(`aggregator.py:71-81`). For these two sub-schemes that is 8 warnings on every single प्रपत्र ड save —
a log flood that will bury the genuine unmapped-designation warnings §5.4 depends on.

> **Design decision.** The spec gains `ignored_class_types: frozenset[str]`. A row whose `class_type`
> is in that set is skipped at `DEBUG`, contributing zero — semantically exact for `निरंक`. Anything
> outside both the known classes and the ignore set keeps the existing `WARNING`. `20290037` and
> `20290262` set `frozenset({'Class-0'})`; the other 13 set `frozenset()`.

**A-2 · `20530313`'s प्रपत्र क class vocabulary is wider than its प्रपत्र ड vocabulary.**
`config.CLASSES_SHEET1_2 = ['Class-3', 'Class-4']` — correct for प्रपत्र ड, which has only Talathi
(Class-3) and Kotwal (Class-4), and matching the workbook. But **प्रपत्र क holds `Class-1 & 2` rows
anyway** — 32 per fiscal year in the live DB, and the workbook's Page 2 keeps its `वर्ग-1 व 2`
columns (`Budget 20530313 …xls` Page 2, rows 38-49, all zero).

If the spec's प्रपत्र क class list were `CLASSES_SHEET1_2`, `acquire_derivation_locks()` would never
lock those rows, `derive_from_form_d()` would never zero them, and `validate_allocation()` would
reject them as `अवैध पद वर्ग` — leaving rows that are stale, invisible to propagation, and
un-editable because the form locks them.

> **Design decision.** The spec carries `post_status_classes` as a field **in its own right**, always
> the full प्रपत्र क vocabulary `('Class-1 & 2', 'Class-3', 'Class-4')` for all 15, decoupled from
> `CLASSES_SHEET1_2`. `CLASSES_SHEET1_2` continues to drive the प्रपत्र ड form's dropdown and is not
> touched. Propagation then zeroes `20530313`'s Class-1 & 2 प्रपत्र क cells, which is correct:
> प्रपत्र ड says there are no such posts.

**A-3 · The four `2029` sub-schemes have no `shared/` package.**
`20290037/46/182/262` lack `shared/services/audit_service.py`; their controllers import
`from src.audit_service import AuditService` (`s20290182/ui_budget_details.py:27`). The shipped
`20530028` derivation code imports `...shared.services.audit_service`.

> **Design decision.** The engine takes `AuditService` from `src.audit_service` directly. The
> `20530028` `shared` wrapper is a thin delegate over exactly that class with an identical
> `log_action(db, request, action, table_name, record_id, old_values, new_values)` signature
> (`s20530028/shared/services/audit_service.py:13,32` delegating to `src/audit_service.py:58`), so
> `20530028`'s audit rows are unchanged by the switch. Phase 5 verifies this against the existing
> audit assertions in `tests/test_s20530028_derivation_e2e.py`.

### 2.8 THE TWO OPEN BUSINESS DECISIONS

| # | Question | Recommended default | Where it lives | Cost to change | Cost of being wrong **today** |
|---|---|---|---|---|---|
| **D-1** | Is `20450091`'s `Deputy Commissioner` Group A or Group B? | **`'1'`** — a divisional Deputy Commissioner is a gazetted Group A post. The workbook cannot decide it (0 posts in all 14 blocks) | `s20450091/config.py` `DESIGNATION_PAY_CLASS` | one dict entry + `reconcile --fix --sub-scheme 20450091` | **nil** — the sub-scheme has zero rows (§2.4) |
| **D-2** | In `20290046`, is `City Architect` Group A and `Assistant City Architect` Group B? | **`City Architect → '1'`, `Assistant City Architect → '2'`**, by parity with `20530387`'s `Assistant Director Town Planning → '1'` / `Planning Assistant → '2'` | `s20290046/config.py` | same | **nil** — zero rows |

Neither blocks any phase. Both are recorded in the sign-off pack (§6.2) so the client answers them
before data entry begins, which is when the answer starts to matter.

---

## 3. BLAST RADIUS

### 3.1 Complexity — and the architecture that follows from it

**Rating: XL.** New shared core package, 14 sub-schemes, a refactor of shipped production code, a
generalised operational tool. All sections (3, 4, 5, 6) required.

**The decision, stated once and applied everywhere below.**

| | Approach | New/changed LOC | Places to fix a bug | Verdict |
|---|---|---|---|---|
| **A** | Copy `s20530028/derivation/` into each of the 14 | ~11,000 (84 new files) | 15 | **Rejected** — duplicated business logic at industrial scale |
| **B** | One config-driven engine in `src/core/derivation/`; every sub-scheme (incl. `20530028`) declares a `DerivationSpec` | ~950 engine + ~35 × 15 bindings | **1** | **Chosen** |
| **C** | Engine in `src/schemes/common/derivation/`, leaving `src/core` untouched | same as B | 1 | Rejected — the registry it must own already lives at `src/core/derivation/registry.py`, and `src/core/secure_crud.py` imports from there. Splitting the package across two roots is worse than moving nothing |

**Why B is not over-engineering.** §1.2 proves the four tables, nine measures, three class
vocabularies and two categories are *already* identical in all 15 sub-schemes. The engine does not
invent an abstraction; it names one the schema already enforces. The spec has **11 fields, of which
only 5 actually vary** across the 15 (§3.3).

**The risk B introduces, and how it is retired.** B refactors code that is live in production for
`20530028`. The mitigation is structural, not procedural: `eab70773` shipped four test files totalling
~1,470 lines (`tests/test_s20530028_derivation_{mapping,aggregator,split,e2e}.py`) exercising the
algebra, the lock order, the clamps, the allocation invariant and the HTTP surface.

> **Phase 5 is a hard gate: the extraction is complete only when all four `20530028` test files pass
> with zero edits to their assertions.** If a test must change, the extraction changed behaviour, and
> the change is a defect until proven otherwise. Import-path-only edits are permitted; assertion edits
> are not.

### 3.2 Files affected

**New — 8 engine + 1 binding module + 14 spec modules + 5 test files:**

```
src/core/derivation/__init__.py                  [NEW]  package marker (missing today — Phase 0)
src/core/derivation/spec.py                      [NEW]  DerivationSpec + register_spec/spec_for
src/core/derivation/mapping.py                   [NEW]  pay_class_for / status_class_for / DA & HRA adapters
src/core/derivation/aggregator.py                [NEW]  CellTotals, aggregate_pay_classes, roll_up
src/core/derivation/split_policy.py              [NEW]  PreserveShareSplit, PostRatioSplit
src/core/derivation/service.py                   [NEW]  acquire_derivation_locks, derive_from_form_d, derive_for_row
src/core/derivation/allocation.py                [NEW]  scan_space_for, class_totals_for, rebalance_status_split
src/core/derivation/validators.py                [NEW]  validate_filled_against_sanctioned, validate_allocation
src/schemes/common/derivation_bindings.py        [NEW]  the 5 call-sites the flat controllers use
src/schemes/{s2029,s2045,s2053}/subs/s{sub}/derivation.py   [NEW] × 14  (~35 LOC each)
tests/test_core_derivation_spec.py               [NEW]
tests/test_core_derivation_engine.py             [NEW]
tests/test_subscheme_derivation_matrix.py        [NEW]  parametrised over all 15 registered specs
tests/test_subscheme_derivation_e2e.py           [NEW]  two flat sub-schemes, all 6 routes
tests/test_derivation_pay_class_coverage.py      [NEW]  the §2.6 drift guard
```

**Modified — 20530028 (3 modified + 5 deleted, extraction only), shared (3), per sub-scheme (8 × 14), templates (4 × 14):**

| File(s) | Change | Phase |
|---|---|---|
| `src/core/derivation/registry.py` | add `register_model_spec()` and `registered_specs()`; existing `register` / `is_registered` / `run_for` signatures unchanged | 4 |
| `s20530028/derivation/{mapping,aggregator,split_policy,allocation,service}.py` | deleted; imports re-pointed at the engine | 5 |
| `s20530028/derivation/__init__.py` | builds and registers the `20530028` `DerivationSpec` | 5 |
| `s20530028/{post_status,post_expenses}/utils/validators.py` | delegate to `core/derivation/validators.py` | 5 |
| `s{sub}/config.py` × 14 | `+ DESIGNATION_PAY_CLASS`, `+ POST_STATUS_CLASSES`, `+ IGNORED_CLASS_TYPES`, `+ DERIVED_*`, `+ ALLOCATABLE_*`, `+ POST_STATUS_FIELD_LABELS_MR` | 7-9 |
| `s{sub}/__init__.py` × 14 | `from . import derivation  # noqa: F401` — registration must happen at scheme import | 10-17 |
| `s{sub}/ui_budget_details.py` × 14 | one hook call after `consolidate_row()` | 10-17 |
| `s{sub}/api_budget_details.py` × 14 | one hook call after `consolidate_row()`; `db.rollback()` on every error path | 10-17 |
| `s{sub}/ui_post_expenses.py` × 14 | lock hoist, `filled ≤ sanctioned`, stop writing `vacant_posts`, hook, deterministic fan-out order | 10-17 |
| `s{sub}/ui_post_status.py` × 14 | reject non-`Filled`, lock hoist, allocation validation, `rebalance_status_split()`, stop writing totals | 10-17 |
| `s{sub}/schemas.py` × 14 | narrow `PostStatusUpdate` (empty) and `PostExpensesUpdate` (drop `vacant_posts`) | 10-17 |
| `s{sub}/router_api.py` × 14 **+ `20530028`** | narrow the CRUD factories on **both** target tables — `post-status → {"GET"}`, `post-expenses → {"GET","PUT"}` (§4.5) | 5, 10-17 |
| `templates/…/s{sub}/post_status_form.html` × 14 | identical patch — `is_filled` gate, `Posts` readonly, notice | 10-17 |
| `templates/…/s{sub}/post_status_list.html` × 14 | 3 anchored edits — `inline_posts` readonly, `applyAllocationLock()`, action link → तपशील | 10-17 |
| `templates/…/s{sub}/post_expenses_form.html` × 14 | identical patch — `VacantPosts` readonly, notice | 10-17 |
| `templates/…/s{sub}/post_expenses_list.html` × 14 | 2 anchored edits — `inline_vacant` readonly, notice | 10-17 |
| `scripts/reconcile_form_derivation.py` | registry-driven, `--sub-scheme` filter | 18 |
| `src/routers/fiscal_year.py` | reconcile the newly created year after the clone (§4.5) | 18 |
| `docs/ARCHITECTURE.md` | the propagation section becomes scheme-agnostic | 20 |

**Template drift, measured — this is why the two form templates are a verbatim patch and the two list
templates are not.** Differing lines against `20530028`'s pre-`eab70773` version, normalised for the
sub-scheme code:

```
post_status_form.html    0-4 lines   in all 14   → apply the eab70773 patch verbatim
post_expenses_form.html  0-4 lines   in all 14   → apply the eab70773 patch verbatim
post_status_list.html    18-925 lines            → 3 ANCHORED edits, never a patch
post_expenses_list.html   1-537 lines            → 2 ANCHORED edits, never a patch
```

The list templates carry per-sub-scheme summary and chart blocks. Attempting to patch them by diff
will fail or, worse, apply to the wrong hunk.

**No schema change. No migration. No new column on any table. No new dependency.**
Everything is stdlib + SQLAlchemy + Pydantic + FastAPI. The workbook analysis that produced §2 is
design-time evidence and ships no code: **do not add `odfpy`; `xlrd` (2.0.2) is already installed and
is still not needed at runtime.**

**Explicitly NOT touched:** every intra-sheet formula (`ui_budget_summary.py`, the प्रपत्र ड form's
महागाई भत्ता / घर भाडे भत्ता boxes, `post_levels/service.py`); all `excel_export/*` populators —
`excel_export/populators/post_status.py` is **byte-identical between `20530028` and the flat
sub-schemes** (modulo the sub-scheme code) and writes the stored ORM columns straight into fixed
workbook cells (`…/s20530162/excel_export/populators/post_status.py:41-47`), so every export becomes
correct for free the moment the columns are correct;
`ui_unit_expenditure.py`; `ui_abstract.py`; `ui_category_info.py`; `src/chatbot.py`;
`static/js/post_levels.js` (already fixed globally).

### 3.3 The `DerivationSpec` — what actually varies

| Field | Type | Varies? | Value across the 15 |
|---|---|---|---|
| `budget_post_model` | model | **yes** | `.models.BudgetPostDetails` |
| `post_status_model` | model | **yes** | `.models.PostStatus` |
| `post_expenses_model` | model | **yes** | `.models.PostExpenses` |
| `designation_pay_class` | `Mapping[str,str]` | **yes** | §2.6 — 5 distinct dicts, 4 of them empty |
| `ignored_class_types` | `frozenset[str]` | **yes** | `{'Class-0'}` for 2, `frozenset()` for 13 |
| `post_status_classes` | `tuple[str,…]` | no | `('Class-1 & 2','Class-3','Class-4')` × 15 |
| `pay_classes` | `tuple[str,…]` | no | `('1','2','3','4')` × 15 |
| `statuses` | `tuple[str,…]` | no | `('Filled','Vacant')` × 15 |
| `hra_rate_map` | `Mapping[str,float]` | no | `{'X':0.3,'Y':0.2,'Z':0.1}` × 15 |
| `derived_post_status_fields` / `derived_post_expenses_fields` / `allocatable_post_status_fields` | `tuple[str,…]` | no | the 9 / `('vacant_posts',)` / the 8 |
| `split_policy` | `SplitPolicy` | no | `PreserveShareSplit()` × 15 |

Five varying fields. The non-varying ones stay on the spec anyway — with defaults — so that a future
sub-scheme that genuinely differs is a data change, not a code change.
`pay_class_to_status_class` is **derived** inside `spec.py` from `post_status_classes`, never
hand-written per sub-scheme.

### 3.4 The three prerequisites — all already satisfied

| Prerequisite | Status | Evidence |
|---|---|---|
| `apply-aggregates` must not zero pay data on page load | **done globally** | `static/js/post_levels.js` fixed by `eab70773`; applies to all 14 |
| `secure_crud` must invoke the hook | **done, generic** | `secure_crud.py:157,180,214-244` — keyed on the model |
| post-levels routes must invoke the hook | **done, generic** | `post_levels/api_router.py:11,482` — takes `budget_post_model` as a factory argument |

The only genuinely missing piece is `src/core/derivation/__init__.py` — the directory works today only
as an implicit namespace package. Phase 0.

### 3.5 Dependency changes

**None.**

---

## 4. DATA & RESILIENCE

Everything in the predecessor's §4 holds unchanged. This section states **only what generalising
changes**, plus one failure mode the predecessor did not cover.

### 4.1 The algebra is unchanged; only its parameters move

STEP A (aggregate प्रपत्र ड per contribution space) → STEP B (प्रपत्र ब `vacant`) → STEP C (roll up to
प्रपत्र क class totals) → STEP D (split by policy) → STEP E (rebalance on allocation edit) are copied
verbatim into the engine. The normative constraints survive intact and must be re-asserted in Phase 5:

- **Per-row rounding, then sum** — never sum-then-round. Per-row rounding is exactly additive across
  taluka contributions; the alternative breaks the invariant `scripts/check_taluka_invariant.py`
  enforces.
- **The aggregator consumes प्रपत्र ड's values exactly as प्रपत्र ड produces them.** The DA and HRA
  adapters in the engine's `mapping.py` are the only code that follows an intra-sheet formula, and
  they must keep following the प्रपत्र ड display calculation, not improve on it.
- **The target `taluka` is always a contribution space**, never `''`.
- **The caller owns commit and rollback.** The engine never commits and never rolls back.

### 4.2 Transaction boundaries and lock order — one global order, now spanning 15 model families

Lock order within one sub-scheme is unchanged and is a correctness requirement, not an optimisation:

```
1. BudgetPostDetails consolidated row   (held by the प्रपत्र ड controller)
2. PostExpenses  consolidated rows, class_type ASC over ('1','2','3','4')
3. PostStatus    consolidated rows, (class_type, status) in configured order
```

**Two facts make this safe across 15 sub-schemes:**

1. Each sub-scheme's tables are physically distinct (`post_status_20530162` ≠ `post_status_20530019`),
   and a single request only ever touches one sub-scheme's tables because the sub-scheme is fixed by
   the route prefix. **No cross-sub-scheme lock cycle is reachable.**
2. The rank ordering is enforced *inside* `acquire_derivation_locks()`, which every path must call
   before its first `consolidate_row()` on a target table — rule 6 of `docs/ARCHITECTURE.md`.

**The deadlock this feature would otherwise introduce, restated because it is easy to lose in a flat
controller:** `ui_post_status.py`'s `POST /{id}/edit` calls `consolidate_row(PostStatus, …)` — a
rank-3 lock — before `rebalance_status_split()` would take rank-2. Hoisting
`acquire_derivation_locks()` above the first `consolidate_row()` is what prevents it. **This hoist
must be repeated in all four प्रपत्र क / प्रपत्र ब flat handlers of every sub-scheme** (routes 3–6 of
§1.4), and Phase 19 asserts it.

**The प्रपत्र ब fan-out widens the lock set to both categories.** When any of the five district
expense fields is present, `ui_post_expenses.py` updates every row of the district — both `Permanent`
and `Temporary`. The lock set must then cover both, acquired in sorted category order, exactly as
`s20530028/post_expenses/controllers/ui_controller.py:326-334` does:
`lock_categories = sorted(CATEGORIES if fans_out else (row.category,))`.

**The fan-out `UPDATE` must also become deterministically ordered.** The flat implementation issues a
bulk `query(...).update(...)` (`s20530162/ui_post_expenses.py:197` and `:695`) whose row-lock acquisition
order is whatever the planner picks — two concurrent district edits can deadlock on each other. The
predecessor solved this in the modular controller by materialising the affected rows
`ORDER BY category, class_type` and assigning field by field
(`s20530028/post_expenses/controllers/ui_controller.py:371-381`). **The flat controllers must adopt
the same ordered-materialisation form.** This is the one place where the flat sub-schemes need real
behaviour change beyond adding calls.

### 4.3 Concurrency — unchanged

`SELECT … FOR UPDATE` on the complete consolidated target set, always in rank order, always before the
first target `consolidate_row()`. `_require_complete_rows()` turns a missing consolidated row into a
loud `RuntimeError` rather than a silent partial lock — keep that.

### 4.4 Caching

Propagation writes happen inside the request transaction, so the existing invalidation on each handler
already covers the target tables — every flat handler calls `invalidate_scheme_cache(district)` and
`invalidate_district_status_cache(...)` after commit. **No new cache key, no new TTL, no new
invalidation trigger.** The one requirement: invalidation must stay **after** `db.commit()`, so a
concurrent reader cannot repopulate the cache from an uncommitted snapshot.

### 4.5 Failure handling — and two gaps the predecessor did not cover

| Failure | Behaviour |
|---|---|
| Engine raises mid-request | Caller rolls back the whole transaction. प्रपत्र ड, क and ब move together or not at all |
| Missing consolidated target row | `RuntimeError` + `form_derivation_missing_consolidated` log. Never a partial write |
| Unknown Class-1 & 2 designation | Falls back to `'2'` + `WARNING`. Never a silent `'1'`, which would inflate the gazetted count |
| `class_type` in `ignored_class_types` | Skipped at `DEBUG`, contributes zero (§2.7 A-1) |
| `filled_posts > sanctioned` | `vacant` clamped to 0, `form_derivation_clamp` at `WARNING`. `filled` is never rewritten |
| Sub-scheme has no spec registered | `run_for()` returns `None` — the sub-scheme behaves exactly as it does today. **This is what makes the phased rollout safe: an un-migrated sub-scheme is untouched, not broken** |

> **GAP — the generic CRUD `POST` and `DELETE` on the *target* tables bypass propagation, and
> `DELETE` breaks every later प्रपत्र ड save.** `create_secure_crud_routes()` is applied to all four
> models in every `router_api.py`. Its `run_for()` call is keyed on the model being written, and the
> only registered model is `BudgetPostDetails` — so `POST /api/schemes/{sub}/post-status` creates a
> प्रपत्र क row from caller-supplied values with no derivation, and `DELETE` removes one.
>
> `DELETE` is the dangerous one: `delete_row_family()` (`src/core/taluka/write.py:291-316`) removes
> the consolidated row **and every contribution row** for that natural key. The next प्रपत्र ड save
> in that `(district, fiscal_year, category)` then hits `_require_complete_rows()`, which raises
> `RuntimeError` — **every subsequent प्रपत्र ड edit in that district and category returns 500 until
> the row is restored by hand.** `POST` is narrower: the natural-key vocabulary is fixed and fully
> seeded (96 प्रपत्र क and 64 प्रपत्र ब rows per fiscal year; 12 and 8 for `20530387`), so a create
> can only succeed for a key that does not exist, which today means none.
>
> **This is live in the shipped `20530028` and would otherwise be replicated 14 more times.** No
> template and no JS calls these routes — grepping `templates/` and `static/` for
> `api/schemes/…/post-status` and `…/post-expenses` returns nothing — so suppressing them costs no
> functionality.
>
> **Fix (Phase 10 recipe, plus a one-line Phase 5 addendum for `20530028`):** narrow both target
> factories to the methods that have a supported write path — `post-status → methods={"GET"}` and
> `post-expenses → methods={"GET", "PUT"}`. प्रपत्र ड and प्रपत्र अ keep the full method set;
> प्रपत्र ड's writes are the trigger and are already hooked.

> **GAP — fiscal-year rollover bypasses every hook.** `src/routers/fiscal_year.py:163-197` clones all
> four tables for a new fiscal year with raw `INSERT … SELECT`. The clone is internally consistent
> (प्रपत्र ड, क and ब are copied together), **but the DA percentage is per fiscal year**
> (`fiscal_years.da_percentage`, read by `src/utils_da_rate.py:50`). If the new year's DA rate differs
> from the source year's, every cloned `dearness_allowance` in प्रपत्र क is stale on creation — for
> all 15 sub-schemes, including the already-shipped `20530028`.
>
> **Fix (Phase 18):** after the clone loop commits, run the registry-driven reconciliation for the new
> fiscal year. It is a full recompute and idempotent, so it is safe to run unconditionally. Deleting a
> fiscal year needs nothing — the delete removes all four tables' rows together
> (`fiscal_year.py:266-273`).

### 4.6 Idempotency

`derive_from_form_d()` is a full recompute of one contribution space, not a delta. Running it twice
changes nothing the second time — `PreserveShareSplit` reproduces the same share from the values it
just wrote (the fixed-point property proved in the predecessor's §4.6). Interrupted reconcile runs are
safe to repeat. **This property must be preserved by the extraction and is asserted in Phase 5.**

---

## 5. SECURITY & OBSERVABILITY

### 5.1 Authorisation — propagation adds no new surface

Every hook runs **inside** a handler that has already checked role, level, district access and the
data-filling window. The engine never reads the request for anything except audit attribution and, in
`derive_for_row()`, the writable taluka via `_writable_taluka_value()` — which is derived from the
auth cookie, **never from the request payload**. Family deletion in `secure_crud.py:225-244` passes a
server-generated taluka list; a payload cannot select it.

**The extraction must not widen this.** `spec_for(model)` is a lookup keyed on a SQLAlchemy class
obtained from the route's own closure — there is no path by which a request can name a different
sub-scheme's spec. Phase 19 asserts that a `20530162` request cannot reach `20530028` rows.

### 5.2 Input validation — exact bounds

| Input | Bound | Where |
|---|---|---|
| प्रपत्र ब `filled_posts` | `0 ≤ filled ≤ Σ sanctioned_posts_curr(pay_class)` in the caller's own space | `core/derivation/validators.py:validate_filled_against_sanctioned` |
| प्रपत्र क `Filled[m]`, the 8 money measures | `0 ≤ value ≤` प्रपत्र ड class total for `m` | `core/derivation/validators.py:validate_allocation` |
| प्रपत्र क `posts`, and every field on a `Vacant` row | **rejected — `409`** | flat handler guard, before any mutation |
| प्रपत्र ब `vacant_posts` in a request body | **dropped from the schema** | `s{sub}/schemas.py` `PostExpensesUpdate`, `extra="forbid"` |
| every numeric | `0 ≤ v ≤ MAX_INPUT_VALUE` (999,999,999) | existing `validate_numeric_inputs` |

The ceiling is computed in **the caller's own contribution space** (`scan_space_for()`): a district or
DCO caller is checked against the consolidated प्रपत्र ड scan they just typed district totals against;
a taluka caller against its own contribution. Do not simplify this to a single scan — it is the
difference between "your share" and "the district total".

### 5.3 Structured logging

Every event keeps its existing key=value shape and gains **one field: `sub_scheme`**. Without it, a
production log line is ambiguous across 15 sub-schemes writing to differently-named tables.

```
form_derivation           sub_scheme= district= taluka= fiscal_year= category= b_rows= c_rows= fields_changed= clamps= duration_ms=   DEBUG
form_derivation_changed   sub_scheme= … field= old= new=                                                                              INFO
form_derivation_clamp     sub_scheme= … pay_class= filled= sanctioned=                                                                WARNING
form_derivation_missing_consolidated  sub_scheme= table= natural_keys=                                                                ERROR
form_allocation_changed / form_allocation_clamp   sub_scheme= …                                                                       INFO / WARNING
unknown Class-1 & 2 designation                   sub_scheme= designation=                                                            WARNING
ignored class_type (निरंक)                        sub_scheme= class_type=                                                             DEBUG
```

Audit rows are unchanged: `action="DERIVE"`, `table_name` = the concrete per-sub-scheme table, plus
old/new values of the derived fields only.

### 5.4 Metrics

Three, all per sub-scheme:

1. `form_derivation.duration_ms` — p50/p95 per `(sub_scheme, district)`. A district with many active
   talukas issues one scan per contribution space; regression here means the aggregator is being
   called outside the batch.
2. `form_derivation.clamps` — a sustained non-zero rate means `filled_posts` and प्रपत्र ड's
   `sanctioned_posts_curr` disagree, i.e. a data problem the user must resolve.
3. `unknown_designation` count per sub-scheme — **any** non-zero value means
   `DESIGNATION_PAY_CLASS` is incomplete for that sub-scheme and gazetted counts are being
   under-reported. This is the single most valuable alert in the feature; it is the runtime form of
   the §2.6 drift trap and of the Phase 7 test.

---

## 6. EXECUTION PHASES

### 6.1 The phase map

**21 phases in four movements:**

```
Phase 0        Preflight — prove the shared infrastructure is already generic
Phase 1-4      Build the engine in src/core/derivation/            (no behaviour change anywhere)
Phase 5        GATE — 20530028 re-pointed at the engine, its 4 test files pass UNCHANGED
Phase 6-9      Shared bindings + all 14 sub-scheme configs
Phase 10       PILOT — 20530162 end to end, all 6 routes, 4 templates
Phase 11-17    Rollout — the remaining 13, mechanical repetition of Phase 10
Phase 18-20    Reconcile + fiscal-year gap, cross-sub-scheme tests, docs
```

**On phase size.** Phases 0–9 are 1–6 files each, as design phases should be. Phases 10–17 are
deliberately larger (12 files per sub-scheme) because they contain **zero new design** — each is the
verbatim application of the Phase 10 recipe to a sub-scheme whose models, schemas and form templates
were proved identical in §1.2 and §3.2. Splitting them further would produce phases that are not
independently verifiable (a sub-scheme with a spec but no controller hook is a half-wired system).
Each rollout phase remains independently verifiable because one sub-scheme's six routes are disjoint
from every other sub-scheme's.

---

### Phase 0: Preflight — prove the shared infrastructure, and close the package gap

Scope: 1 file, ~5 LOC
Verify: `python -c "import src.core.derivation as d; print(d.__file__)"` and
`pytest tests/test_s20530028_derivation_e2e.py -q`

**[CREATE]** `src/core/derivation/__init__.py`
- What: package marker. The directory currently resolves only as an implicit namespace package, which
  works but makes the package un-importable from a zipapp and hides typos in submodule names.
- Pattern: match `src/core/taluka/__init__.py`.

**[VERIFY, no file]** Confirm and record, in the phase's commit message, that:
- `secure_crud.py:157,180,214` calls `run_for` for **any** registered model.
- `post_levels/api_router.py:482` calls `run_for(db, budget_post_model, …)`, and all 14 flat
  sub-schemes already construct that router (`api_budget_details.py`, one call each).
- `static/js/post_levels.js` no longer POSTs `apply-aggregates` on page load.

> If any of these is false, **stop**: the predecessor's Phase 0/6 were not as global as this plan
> assumes, and §3.4 must be re-derived before continuing.

---

### Phase 1: The spec

Scope: 2 files, ~150 LOC
Verify: `pytest tests/test_core_derivation_spec.py -q`

**[CREATE]** `src/core/derivation/spec.py`
- What: the frozen `DerivationSpec` dataclass of §3.3, plus `register_spec(spec)` and
  `spec_for(model) -> DerivationSpec`. `pay_class_to_status_class` is a computed property, never a
  constructor argument. `__post_init__` validates: the three models are distinct; every value of
  `designation_pay_class` is in `pay_classes`; `post_status_classes` is non-empty; the derived-field
  tuples name real columns on their models; `allocatable_post_status_fields ⊆ derived_post_status_fields`.
- Pattern: frozen dataclass + module-level dict, as `src/core/derivation/registry.py:7-21`. Re-import
  is idempotent; re-registering a *different* spec for the same model raises — same rule, same reason
  (import order must not decide business behaviour).
- System design: `register_spec()` indexes the spec by **all three** models, so
  `spec_for(PostStatus20530162)` resolves without the caller knowing the sub-scheme. Lookup is a plain
  dict — no cache, no TTL, no invalidation; the mapping is fixed at import time.

**[CREATE]** `tests/test_core_derivation_spec.py`
- What: a valid spec round-trips; duplicate-model registration with a different spec raises; a pay
  class outside `pay_classes` raises; a derived field naming a non-existent column raises;
  `pay_class_to_status_class` collapses `{1,2} → Class-1 & 2`, `3 → Class-3`, `4 → Class-4`.

---

### Phase 2: Mapping and aggregation

Scope: 3 files, ~230 LOC
Verify: `pytest tests/test_core_derivation_engine.py -k "mapping or aggregate" -q`

**[CREATE]** `src/core/derivation/mapping.py`
- What: `pay_class_for(spec, class_type, designation)`, `status_class_for(spec, pay_class)`,
  `form_d_dearness_allowance(spec, row, da_rate)`, `form_d_house_rent_allowance(spec, row)`, and the
  9-entry `MEASURE_MAP`.
- Pattern: lift `s20530028/derivation/mapping.py` verbatim; replace the module-level `config` imports
  with `spec` lookups. **The two arithmetic expressions must not change** — they reproduce what
  प्रपत्र ड displays, and matching it is the requirement.
- System design: resolution order is **`class_type` first, `designation` second** (§2.6). New:
  `class_type in spec.ignored_class_types` → return `None` and log at `DEBUG`; callers treat `None` as
  "contributes nothing". Unknown `Class-1 & 2` designation → `'2'` + `WARNING` carrying `sub_scheme`.

**[CREATE]** `src/core/derivation/aggregator.py`
- What: `CellTotals`, `aggregate_pay_classes(db, spec, *, taluka, district, fiscal_year, category, da_rate)`,
  `roll_up_to_status_classes(spec, totals)`.
- Pattern: lift `s20530028/derivation/aggregator.py`; `BudgetPostDetails` becomes
  `spec.budget_post_model`, `PAY_CLASSES` becomes `spec.pay_classes`, and the three hard-coded class
  keys become `spec.post_status_classes`.
- System design: **one unscoped ORM query per contribution space**
  (`execution_options(TALUKA_SCOPE_ALL_OPTION=True)`), filtered on the exact `taluka` value — never a
  query per class. `salary` accumulates as `Decimal` and is rounded once at the end; every other
  measure is rounded per row then summed (§4.1). A `None` pay class is skipped without touching the
  accumulator.

**[CREATE]** `tests/test_core_derivation_engine.py` *(mapping + aggregation cases; grows in Phases 3-4)*
- What: mirror the assertions of `tests/test_s20530028_derivation_{mapping,aggregator}.py` against a
  synthetic two-sub-scheme fixture, plus the new `ignored_class_types` path and the `None`-pay-class
  skip.

---

### Phase 3: Split policy and the propagation writer

Scope: 2 files, ~400 LOC
Verify: `pytest tests/test_core_derivation_engine.py -q`

**[CREATE]** `src/core/derivation/split_policy.py`
- What: the `SplitPolicy` protocol, `PreserveShareSplit`, `PostRatioSplit`.
- Pattern: lift `s20530028/derivation/split_policy.py` **unchanged** — it has no sub-scheme dependency
  at all. The fallback chain stays: own share → salary share → post share → `1.0`.
- System design: the default moves from a module-level `SPLIT_POLICY` singleton to
  `spec.split_policy`, defaulting to `PreserveShareSplit()`. Changing one sub-scheme's policy stays a
  one-line change, now in its own `derivation.py`.

**[CREATE]** `src/core/derivation/service.py`
- What: `acquire_derivation_locks(db, spec, district, fiscal_year, category)`,
  `derive_from_form_d(db, spec, *, district, fiscal_year, category, taluka, request=None)`, and
  `derive_for_row(db, row, request, *, taluka=None)` — the last resolving its spec via
  `spec_for(type(row))` so it matches the `DerivationHook` signature the registry already calls.
- Pattern: lift `s20530028/derivation/service.py`; models and vocabularies come from `spec`;
  `AuditService` from `src.audit_service` (§2.7 A-3).
- System design, all load-bearing and all preserved verbatim:
  - **Lock order** — `PostExpenses` `class_type ASC`, then `PostStatus` `(class_type, status)` in
    configured order, both `with_for_update()`, both on `taluka == DISTRICT_LEVEL`.
  - **`_require_complete_rows()`** — a missing consolidated row is an `ERROR` + `RuntimeError`, never
    a partial lock set.
  - **`_record_changes()`'s allowlist assertion** — writing a field outside `spec.derived_*_fields`
    raises `AssertionError`. This is the guard that keeps propagation away from प्रपत्र ब's
    user-owned `other` (§2.5). It must not be softened to a log.
  - **Never commits, never rolls back.** Flush + `consolidate_row()` per changed family, then return.

---

### Phase 4: Allocation, validators, and registry integration

Scope: 3 files, ~330 LOC
Verify: `pytest tests/test_core_derivation_engine.py tests/test_core_derivation_spec.py -q`

**[CREATE]** `src/core/derivation/allocation.py`
- What: `scan_space_for(row)`, `class_totals_for(db, spec, row, *, taluka)`,
  `rebalance_status_split(db, row, request=None)` — STEP E.
- Pattern: lift `s20530028/derivation/allocation.py`; `PostStatus` becomes `spec.post_status_model`,
  `VALID_CLASS_KEYS` becomes `spec.post_status_classes`, `ALLOCATABLE_POST_STATUS_FIELDS` becomes
  `spec.allocatable_post_status_fields`.
- System design: the three refusals stay hard errors — a lifted total-space row, a non-`Filled` row,
  and `taluka in ('', DISTRICT_LEVEL)`. `posts` is **never** touched here; it is owned by LINK 3
  inside `derive_from_form_d`.

**[CREATE]** `src/core/derivation/validators.py`
- What: `validate_filled_against_sanctioned(db, record, filled_posts)` and
  `validate_allocation(db, record, values)`, both resolving their spec from the record's model.
- Pattern: merge `s20530028/post_expenses/utils/validators.py:validate_filled_against_sanctioned` and
  `s20530028/post_status/utils/validators.py:validate_allocation`, unchanged in behaviour, returning
  the same `(bool, marathi_message)` tuples the flat controllers already expect.
- System design: both compute their ceiling in `scan_space_for(record)` (§5.2). Marathi messages are
  taken verbatim from the shipped code so the client sees identical wording in all 15 sub-schemes.

**[MODIFY]** `src/core/derivation/registry.py`
- What: add `register_model_spec(spec)`, which registers the spec **and** binds `derive_for_row` as
  the hook for `spec.budget_post_model`, so a sub-scheme's `derivation.py` is one call. `register`,
  `is_registered` and `run_for` keep their current signatures and semantics — `secure_crud.py` and
  `post_levels/api_router.py` must not need editing.
- System design: also expose `registered_specs()` returning the specs in a **stable, sorted order**
  (by sub-scheme code) for the Phase 18 reconcile tool and the Phase 19 matrix, so reconcile output is
  diffable between runs.

---

### Phase 5: **GATE** — 20530028 re-pointed at the engine, with zero test edits

Scope: 3 modified + 5 deleted, ~−800 LOC net
Verify: `pytest tests/test_s20530028_derivation_mapping.py tests/test_s20530028_derivation_aggregator.py tests/test_s20530028_derivation_split.py tests/test_s20530028_derivation_e2e.py -q`
— **and `git diff` on those four files must show import-path changes only. Any assertion edit fails the phase.**

**[MODIFY]** `src/schemes/s2053/subs/s20530028/derivation/__init__.py`
- What: build the `20530028` `DerivationSpec` from the existing `config.py` constants
  (`DESIGNATION_PAY_CLASS`, `VALID_CLASS_KEYS`, `STATUSES`, `HRA_RATE_MAP`, `DERIVED_*`,
  `ALLOCATABLE_*`), `ignored_class_types=frozenset()`, and call `register_model_spec()`. Re-export
  `acquire_derivation_locks`, `derive_for_row`, `derive_from_form_d` so the four `20530028`
  controllers keep their current import lines unchanged.

**[DELETE]** `.../s20530028/derivation/{mapping,aggregator,split_policy,service,allocation}.py`
- What: their content now lives in `src/core/derivation/`. Every module that imported them
  (`post_expenses/utils/validators.py`, `post_status/utils/validators.py`, the four controllers, the
  four test files) re-points to `src.core.derivation.*`.
- Pattern: prefer deletion over leaving re-export shims. A shim is a second place a future reader can
  believe the logic lives.

**[MODIFY]** `.../s20530028/post_expenses/utils/validators.py` + `.../post_status/utils/validators.py`
- What: keep `validate_nps_value` and `validate_post_status_inputs` (sub-scheme-local, no engine
  dependency); delegate `validate_filled_against_sanctioned` and `validate_allocation` to
  `src/core/derivation/validators.py`.

**[MODIFY]** `.../s20530028/router_api.py` *(the §4.5 addendum — one line, applies retroactively)*
- What: narrow the shipped `post-status` factory from `methods={"GET","POST","DELETE"}` to
  `methods={"GET"}`, and the `post-expenses` factory to `methods={"GET","PUT"}`.
- System design: closes the "deleting a target row breaks every later प्रपत्र ड save" failure
  documented in §4.5, in the sub-scheme where it is already live.
  `tests/test_s20530028_derivation_e2e.py` asserts `PUT` is `405`; Phase 19 extends that to `POST` and
  `DELETE` — a **new** assertion in a **new** file, not an edit to an existing one, so the Phase 5
  gate still holds.

> **Why this phase exists and must not be merged into Phase 4.** It is the only point at which the
> extraction can be proved behaviour-preserving, against real assertions written before the refactor
> was contemplated. Everything after it is new wiring on proven code.

---

### Phase 6: The flat-controller binding module

Scope: 2 files, ~180 LOC
Verify: `pytest tests/test_core_derivation_engine.py -q` and `ruff check src/schemes/common/`

**[CREATE]** `src/schemes/common/derivation_bindings.py`
- What: the five call-sites a flat controller needs, so that each controller edit is 2–4 lines rather
  than 120:
  1. `derive_after_consolidate(db, row, request)` — the प्रपत्र ड / प्रपत्र ब trigger.
  2. `lock_targets(db, row, *, fan_out, categories)` — hoisted `acquire_derivation_locks()` over
     `sorted(categories)` when the district expense fan-out is active, else the row's own category
     (§4.2).
  3. `reject_derived_status_edit(row)` — raises `409` with the shipped Marathi message when
     `row.status != 'Filled'`.
  4. `rebalance_after_consolidate(db, row, request)` — STEP E.
  5. `ordered_district_rows(db, model, row, sub_scheme)` — the affected प्रपत्र ब rows materialised
     `ORDER BY category, class_type` for the deterministic fan-out (§4.2).
- Pattern: thin adapters over `src/core/derivation/*`; **no business logic of their own**. If a
  behaviour needs changing later it changes in the engine, not here.
- System design: each helper is no-op-safe — if the row's model has no registered spec it returns
  without doing anything, so a half-migrated deployment degrades to today's behaviour rather than
  raising (§4.5).

**[CREATE]** `tests/test_subscheme_derivation_matrix.py` *(skeleton; filled in Phase 19)*
- What: a `pytest.mark.parametrize` over `registered_specs()`, so every sub-scheme added in Phases
  7–17 is automatically covered by every invariant the file asserts. Starting the file here means no
  rollout phase can add a sub-scheme without it being tested.

---

### Phase 7: Family A pay-class config — the six identical 2053 sub-schemes

Scope: 6 config files + 1 test, ~30 LOC each
Verify: `pytest tests/test_derivation_pay_class_coverage.py -q`

**[MODIFY]** `s20530019/config.py`, `s20530153/config.py`, `s20530162/config.py`,
`s20530233/config.py`, `s20530304/config.py`, `s20530378/config.py`
- What: add, to each, the identical block: `DESIGNATION_PAY_CLASS` (§2.6 Family A),
  `POST_STATUS_CLASSES = ('Class-1 & 2','Class-3','Class-4')`, `IGNORED_CLASS_TYPES = frozenset()`,
  `DERIVED_POST_STATUS_FIELDS`, `DERIVED_POST_EXPENSES_FIELDS`, `ALLOCATABLE_POST_STATUS_FIELDS`,
  `POST_STATUS_FIELD_LABELS_MR`.
- Pattern: copy the constant block at `s20530028/config.py:194-235` verbatim (`CLASS_1_2_KEY` … `POST_STATUS_FIELD_LABELS_MR`), and author `DESIGNATION_PAY_CLASS` (`config.py:157`) per §2.6.
- System design: **`POST_STATUS_CLASSES` is a new constant, not an alias of `CLASSES_SHEET1_2`**
  (§2.7 A-2). Even where the two are equal today, aliasing them would make `20530313` a special case
  in Phase 9 instead of a uniform one.

**[CREATE]** `tests/test_derivation_pay_class_coverage.py`
- What: for every sub-scheme in scope, assert that every `Class-1 & 2` designation appearing in
  `config.DESIGNATIONS`, in `config.POSITION_ORDER`, **or in the seed migration** has a key in
  `DESIGNATION_PAY_CLASS`, and that every value is in `('1','2')`. This is the automated form of the
  §2.6 drift trap and the compile-time twin of the §5.4 `unknown_designation` metric.

---

### Phase 8: Family C pay-class config — the two sub-schemes with their own cadres

Scope: 2 files, ~40 LOC
Verify: `pytest tests/test_derivation_pay_class_coverage.py -q`

**[MODIFY]** `s20450091/config.py` — `DESIGNATION_PAY_CLASS` per §2.6 Family C. Add an inline comment
on `Deputy Commissioner` recording that it is **D-1**, unconstrained by the workbook, assigned `'1'`
on cadre.

**[MODIFY]** `s20530387/config.py` — the 13-entry `DESIGNATION_PAY_CLASS` per §2.6. Add an inline
comment on `Law Officer (Honorarium)` recording that प्रपत्र ब omits it (13 vs 12) and that `'2'`
matches `20530028`'s treatment of the same designation.

---

### Phase 9: Families B, D and E — the empty and the anomalous

Scope: 6 files, ~25 LOC
Verify: `pytest tests/test_derivation_pay_class_coverage.py -q`

**[MODIFY]** `s20530242/config.py`, `s20530313/config.py` — `DESIGNATION_PAY_CLASS = {}`.
For `20530313`, `POST_STATUS_CLASSES` is the **full three-class tuple** while `CLASSES_SHEET1_2`
stays `['Class-3','Class-4']`. Add the §2.7 A-2 rationale as a comment; this is the one place where a
reader will otherwise "fix" the apparent inconsistency and reintroduce the bug.

**[MODIFY]** `s20290046/config.py`, `s20290182/config.py` — §2.6 Family D, with a comment on
`20290046` recording **D-2**.

**[MODIFY]** `s20290037/config.py`, `s20290262/config.py` — `DESIGNATION_PAY_CLASS = {}` and
`IGNORED_CLASS_TYPES = frozenset({'Class-0'})`, with the §2.7 A-1 `निरंक` rationale as a comment.

---

### Phase 10: **PILOT** — `20530162` end to end

Scope: 12 files (8 Python + 4 templates), ~260 LOC changed
Verify: `pytest tests/test_subscheme_derivation_e2e.py -q` — the new file, written against
`20530162`, covering all six routes of §1.4 plus the two generic `secure_crud` routes.

This phase establishes the recipe. **Every subsequent rollout phase is this list, applied verbatim.**

**[CREATE]** `s20530162/derivation.py`
- What: build the `DerivationSpec` from `config.py` + `models.py`, call `register_model_spec()`.
- Pattern: `s20530028/derivation/__init__.py` as rewritten in Phase 5. ~35 LOC, no logic.

**[MODIFY]** `s20530162/__init__.py`
- What: `from . import derivation  # noqa: F401`, placed **before** the router imports.
- System design: registration must complete at scheme-import time, because `secure_crud` and the
  post-levels router resolve the hook lazily at request time via `run_for` and will silently do
  nothing if the module was never imported. `src/main.py` imports the sub-scheme package, so this one
  line is what makes routes 1–6 *and* the two generic route families live.

**[MODIFY]** `s20530162/ui_budget_details.py` — `POST /{id}/edit`
- What: after the existing `consolidate_row(db, BudgetPostDetails, …)` and **before** `db.commit()`
  (`ui_budget_details.py:358-364`), call `derive_after_consolidate(db, db_detail, request)`.
- Pattern: `s20530028/budget_post_details/controllers/ui_controller.py:465-475`.

**[MODIFY]** `s20530162/api_budget_details.py` — `POST /api/update-inline`
- What: the same insertion after `consolidate_row` (`api_budget_details.py:266-273`). The `try` block
  already rolls back on `HTTPException`; extend the rollback to the generic handlers so a
  mid-propagation failure cannot leave the session dirty.
- Pattern: `s20530028/budget_post_details/controllers/api_controller.py:335-344`.

**[MODIFY]** `s20530162/ui_post_expenses.py` — both routes
- What, in order: (a) hoist `lock_targets(...)` above the first `consolidate_row`, with
  `fan_out = any(expense field is not None)`; (b) call `validate_filled_against_sanctioned` and reject
  with `400` + the Marathi message; (c) **stop assigning `db_item.vacant_posts`** — delete the line,
  do not set it to a computed value; (d) replace the bulk fan-out `query(...).update(...)` with
  `ordered_district_rows()` + field assignment (§4.2); (e) call
  `derive_after_consolidate(db, db_item, request)` after `consolidate_row`, before `commit`;
  (f) `db.rollback()` on every error path.
- Pattern: `s20530028/post_expenses/controllers/ui_controller.py:326-412` and
  `api_controller.py:171-205`.
- System design: (c) is the whole point — `vacant_posts` becomes derived. Leaving the assignment in
  would make the last writer win non-deterministically between the form value and the derivation.
  **Both routes assign it today** — `ui_post_expenses.py:181` in `api_update_inline` and `:674` in
  `ui_update_post_expense` — and both must lose the assignment *and* the `VacantPosts` form parameter.
  **Both routes also fan out** (§4.2), so (a) and (d) apply to both, not just the form route.

**[MODIFY]** `s20530162/ui_post_status.py` — both routes
- What, in order: (a) `reject_derived_status_edit(db_item)` immediately after `resolve_editable_row`,
  before any mutation; (b) hoist `lock_targets(...)`; (c) drop `District/Category/Class/Status/Posts`
  from the accepted form fields and from the update dict — they are keys or derived, never writable
  here; (d) `validate_allocation` on the eight money measures; (e) `rebalance_after_consolidate()`
  after `consolidate_row`, before `commit`; (f) pass `is_filled=(item.status == 'Filled')` into both
  template renders.
- Pattern: the full shipped diff of `s20530028/post_status/controllers/ui_controller.py:289-389` and
  `api_controller.py:126-188`.
- System design: **both routes assign `record.posts` today** — `ui_post_status.py:591` in
  `api_update_inline` and the `update_dict` in `ui_update_post_status`. `posts` is owned by LINK 3 and
  is written only by `derive_from_form_d`; leaving either assignment in place lets a प्रपत्र क save
  silently overwrite the प्रपत्र ब-derived post split until the next प्रपत्र ड edit restores it.

**[MODIFY]** `s20530162/schemas.py`
- What: `PostStatusUpdate` becomes an empty `BaseModel` with `extra="forbid"`; `PostExpensesUpdate`
  lists the eight caller-owned fields and drops `vacant_posts`, with `extra="forbid"`.
- Pattern: the `eab70773` diff of `s20530028/schemas.py:62-105`, verbatim.

**[MODIFY]** `s20530162/router_api.py`
- What: `methods={"GET"}` on the `post-status` `create_secure_crud_routes()` call, and
  `methods={"GET", "PUT"}` on the `post-expenses` call. प्रपत्र ड and प्रपत्र अ are untouched.
- Pattern: `s20530028/router_api.py:26-31` (which today passes `{"GET","POST","DELETE"}`).
- System design: `PUT` on प्रपत्र क is suppressed rather than schema-narrowed because the generic
  updater writes arbitrary body fields and then consolidates — there is no seam in it for the
  allocation rebalance. `POST` and `DELETE` on **both** target tables are suppressed for the reason
  in §4.5: neither runs propagation, and `DELETE` removes a whole natural-key family and makes every
  later प्रपत्र ड save in that district and category raise. The UI routes are the only supported
  प्रपत्र क and प्रपत्र ब write paths, and nothing in `templates/` or `static/` calls the generic
  ones.

**[MODIFY]** 4 templates under `templates/schemes/s2053/subs/s20530162/`
- `post_status_form.html` — apply the `eab70773` patch verbatim (measured **0 differing lines** from
  `20530028`'s pre-change version): `is_filled` heading and notice, `Posts` readonly, the eight
  measures readonly when not `is_filled`, submit button hidden on `Vacant`.
- `post_expenses_form.html` — apply verbatim (also 0 differing lines): `VacantPosts` readonly + notice.
- `post_status_list.html` — 3 **anchored** edits: `inline_posts` readonly; the `applyAllocationLock()`
  helper plus its call in `loadRecordData()`; the row action link becomes `तपशील`, unconditional.
- `post_expenses_list.html` — 2 **anchored** edits: `inline_vacant` readonly; the द्रुत संपादन notice.

**[CREATE]** `tests/test_subscheme_derivation_e2e.py`
- What: the flat-layout analogue of `tests/test_s20530028_derivation_e2e.py`, over `20530162`:
  a प्रपत्र ड edit propagates; a प्रपत्र ब `filled_posts` edit moves प्रपत्र क `posts`; a `Vacant`
  प्रपत्र क edit is `409`; a `Filled` allocation edit rebalances and preserves the class total; an
  over-ceiling allocation is `400`; `PUT /api/schemes/20530162/post-status/{id}` is `405`;
  `PostExpensesUpdate` rejects `vacant_posts` with `422`; taluka and district callers each derive in
  their own space; a second identical save changes nothing (idempotence).

---

### Phases 11–17: Rollout — the remaining 13 sub-schemes

Each phase: **12 files per sub-scheme**, exactly the Phase 10 list. No new design.
Verify, per phase: `pytest tests/test_subscheme_derivation_matrix.py -k "<sub1> or <sub2>" -q`

| Phase | Sub-schemes | Family | The one thing to watch |
|---|---|---|---|
| **11** | `20530019`, `20530153` | A | Nothing — string-identical to the pilot |
| **12** | `20530233`, `20530304` | A | `20530304`'s `post_status_list.html` differs most from the pilot's (925 lines); use the anchors, never a patch |
| **13** | `20530378`, `20450091` | A / C | `20450091` is parent `2045`: confirm the template path root (`templates/schemes/s2045/subs/…`) and that D-1 is recorded |
| **14** | `20530242`, `20530313` | B | `20530313` — `POST_STATUS_CLASSES` ≠ `CLASSES_SHEET1_2` (§2.7 A-2). Assert प्रपत्र क Class-1 & 2 derives to zero rather than being skipped |
| **15** | `20530387` | C | Single district (`DCO Staff`); `POST_EXPENSES_DISTRICT_COMPONENT` has one entry; 13-entry pay-class dict; the §2.6 designation drift |
| **16** | `20290046`, `20290182` | D | **No `shared/` package** (§2.7 A-3) — `AuditService` from `src.audit_service`; the 4-line-drift template variant; D-2 recorded for `20290046` |
| **17** | `20290037`, `20290262` | E | `IGNORED_CLASS_TYPES = {'Class-0'}` (§2.7 A-1). Assert a `निरंक` row logs at `DEBUG`, contributes zero, and emits **no** `WARNING` |

**Per-phase file list (identical for every sub-scheme):**

```
[CREATE] s{sub}/derivation.py
[MODIFY] s{sub}/__init__.py                 [MODIFY] s{sub}/ui_budget_details.py
[MODIFY] s{sub}/api_budget_details.py       [MODIFY] s{sub}/ui_post_expenses.py
[MODIFY] s{sub}/ui_post_status.py           [MODIFY] s{sub}/schemas.py
[MODIFY] s{sub}/router_api.py
[MODIFY] templates/schemes/{parent}/subs/s{sub}/post_status_form.html
[MODIFY] templates/schemes/{parent}/subs/s{sub}/post_status_list.html
[MODIFY] templates/schemes/{parent}/subs/s{sub}/post_expenses_form.html
[MODIFY] templates/schemes/{parent}/subs/s{sub}/post_expenses_list.html
```

> **Rollout safety property.** A sub-scheme with no registered spec is untouched — `run_for()` returns
> `None` and every binding helper is a no-op (§4.5). The system is therefore correct after **every**
> phase, not only after Phase 17, and any phase can be reverted independently.

---

### Phase 18: Reconciliation, generalised — and the fiscal-year gap closed

Scope: 2 files, ~120 LOC changed
Verify: `python scripts/reconcile_form_derivation.py --dry-run` (expect: 15 sub-schemes scanned,
**at most 1 cell reported** — `20530242` Palghar/Permanent/Class-3 `posts 0 → 1`, §2.4), then
`--dry-run --sub-scheme 20530162` (expect: 0 changes).

**[MODIFY]** `scripts/reconcile_form_derivation.py`
- What: replace the three hard-coded `s20530028` imports (`scripts/reconcile_form_derivation.py:28-39`)
  with iteration over `registered_specs()`; add `--sub-scheme` alongside the existing `--district` and
  `--fiscal-year`; report per sub-scheme and in total.
- Pattern: keep the existing dry-run-by-default, per-district commit, full-recompute structure — it is
  already idempotent and interrupt-safe.
- System design: **discovery is registry-driven, never `FOUR_TABLE_PARENT_SCHEMES`** (§1.1 trap).
  `registered_specs()` returns a stable sorted order so two runs produce diffable output.

**[MODIFY]** `src/routers/fiscal_year.py`
- What: after the clone loop's `db.commit()` (`fiscal_year.py:215`), run the reconciliation for the newly
  created fiscal year across all registered specs.
- System design (§4.5 GAP): the clone copies प्रपत्र क and ब verbatim, but `da_percentage` is per
  fiscal year, so every cloned `dearness_allowance` is stale whenever the new year's rate differs.
  Reconcile is a full recompute and idempotent, so it runs unconditionally. Failure must be logged and
  must **not** roll back the clone — a created-but-unreconciled year is recoverable by running the
  script; a half-created year is not.
- Note in the commit message that this also closes the same latent gap for the already-shipped
  `20530028`.

---

### Phase 19: The cross-sub-scheme invariant matrix

Scope: 2 files, ~450 LOC
Verify: `pytest tests/ -q` — the whole suite, including all four untouched `20530028` files.

**[MODIFY]** `tests/test_subscheme_derivation_matrix.py`
- What: parametrised over `registered_specs()` — so it covers all 15 automatically — asserting, per
  sub-scheme:
  1. **Spec integrity** — three distinct models; every name in `DERIVED_*` is a real column; every pay
     class in `('1','2','3','4')`; `post_status_classes` equals the प्रपत्र क vocabulary.
  2. **Lock order** — `acquire_derivation_locks` issues `PostExpenses` before `PostStatus`, each in
     its configured order (captured via a SQLAlchemy `before_cursor_execute` hook, as
     `tests/test_s20530028_derivation_e2e.py` already does).
  3. **The allowlist assertion still bites** — attempting a non-derived write raises.
  4. **Idempotence** — two consecutive `derive_from_form_d` calls; the second changes nothing.
  5. **Taluka invariant** — `row('') == Σ contributions` on both target tables after propagation.
  6. **Isolation** — a spec's engine call never touches another sub-scheme's tables (§5.1).
  7. **`ignored_class_types`** — contributes zero, logs at `DEBUG`, emits no `WARNING`.
  8. **Route surface** — for all **15**, `PUT`, `POST` and `DELETE` on
     `/api/schemes/{sub}/post-status` are `405`, `POST` and `DELETE` on `/post-expenses` are `405`,
     and `PostExpensesUpdate` rejects `vacant_posts` with `422` (§4.5).

**[MODIFY]** `tests/test_subscheme_derivation_e2e.py`
- What: extend the Phase 10 flat-layout suite to a second, structurally different sub-scheme —
  `20290182` (no `shared/`, different template variant, different parent scheme) — to prove the recipe
  is not `2053`-specific.

---

### Phase 20: Documentation and final validation

Scope: 2 files
Verify: `pytest tests/ -q` and `python scripts/reconcile_form_derivation.py --dry-run`

**[MODIFY]** `docs/ARCHITECTURE.md`
- What: retitle `## Cross-sheet propagation (20530028)` to cover all 15; point it at
  `src/core/derivation/` and the `DerivationSpec`; state that adding a sub-scheme is a spec plus six
  route hooks and nothing else. Write-path rules 5 and 6 are unchanged in wording and now apply to 15
  sub-schemes.

**[MODIFY]** this document
- What: record the answers to D-1 and D-2 once the client gives them, and the actual
  `reconcile --dry-run` output from the production run, so the sign-off pack is self-contained.

---

## 6.2 SIGN-OFF PACK — what the client must see before Phase 18 runs with `--fix`

1. **The rollout writes at most one cell.** §2.4, measured directly against production. Attach the
   `--dry-run` output.
2. **The two open questions.** D-1 (`20450091` Deputy Commissioner) and D-2 (`20290046` City Architect
   / Assistant City Architect), §2.8. Both currently cost nothing to get wrong; both must be settled
   before data entry.
3. **What becomes read-only, and — more importantly — what does not.** Read-only: प्रपत्र ब
   `रिक्त पदे`; प्रपत्र क `पदे`; प्रपत्र क's eight measures on the `रिक्त` row. Still fully editable:
   प्रपत्र ब `भरलेली पदे`, every district expense field, and प्रपत्र क's eight measures on the
   `भरलेली` row. The rule is one sentence: *a field is read-only if and only if propagation writes it.*
4. **A seed-data observation, not a software change.** §2.3: the seeded प्रपत्र क and प्रपत्र ब for
   nine `2053`/`2045` sub-schemes are one identical placeholder dataset, and प्रपत्र ड is identical
   across six of them. If those seeds are ever re-applied to a fresh database, propagation will
   overwrite the placeholder प्रपत्र क from प्रपत्र ड — correctly. The client may nonetheless want to
   know that six sub-schemes currently ship the same प्रपत्र ड numbers.
5. **The fiscal-year rollover fix.** §4.5. Creating 2026-27 with a different DA percentage would
   previously have carried 2025-26's महागाई भत्ता into प्रपत्र क unchanged, in all 15 sub-schemes.
6. **Two API methods are being withdrawn.** §4.5. `POST` and `DELETE` on
   `/api/schemes/{sub}/post-status` and `/post-expenses`, plus `PUT` on `post-status`. Nothing in the
   application calls them, and `DELETE` on a प्रपत्र क row currently makes every later प्रपत्र ड save
   in that district and category fail. If the client has an external integration against those
   endpoints, they must say so **before** Phase 10 ships.

---

## 7. WHAT THIS DESIGN DELIBERATELY DOES NOT DO

- **It does not unify the flat and modular layouts.** Refactoring 14 sub-schemes × ~4,600 lines into
  the `20530028` module shape is a far larger change than this feature, with no client-visible
  benefit. The binding module (Phase 6) gives the flat controllers the same seams without the rewrite.
- **It does not touch a single intra-sheet formula.** Same scope boundary as the predecessor. The
  software's own महागाई भत्ता, घर भाडे भत्ता, गोषवारा and level-aggregation arithmetic were set to
  the client's requirement and may deliberately differ from the workbook.
- **It does not connect प्रपत्र अ.** `unit_expenditure`'s natural key is
  `(fiscal_year, district, unit_account)` — no category, class or designation dimension. No
  relationship exists in any of the 15 workbooks.
- **It does not correct the seed data.** §2.3 documents the duplication; fixing it is a data task for
  the client, not a code change, and propagation makes it moot for प्रपत्र क and ब.
- **It does not fix `get_scheme_models()`'s silent fallback.** Flagged in §1.1 and routed around;
  fixing it is a separate change to `src/utils_scheme.py` and `src/routers/fiscal_year.py`.
- **It does not add a workbook parser to the runtime.** The §2 analysis is design-time evidence. The
  reconcile tool compares the database against itself, never against a file.
- **It does not add propagation to the generic CRUD `POST`/`DELETE` on प्रपत्र क and प्रपत्र ब.** It
  suppresses those methods instead (§4.5). Making `DELETE` propagation-aware would mean deciding what
  it means to delete a row from a fixed vocabulary that प्रपत्र ड's totals must land in — a question
  with no good answer. Suppression is the correct one.
- **It does not make प्रपत्र क's class totals editable anywhere.** They are owned by प्रपत्र ड. The
  allocation, and only the allocation, is user data.
- **It does not touch completion status.** `src/routers/completion_status.py` records a user-toggled
  `SubSchemaCompletion` flag and never inspects row values, so nothing about propagation changes when
  a sub-scheme is marked complete. Checked, so that it is not re-investigated.

---

## 8. ROLLOUT ORDER (operational, not code)

1. Ship Phases 0–5. `20530028` behaviour is unchanged and proven by its own untouched tests.
2. Ship Phases 6–9. Still no behaviour change: specs and configs exist, no controller calls them yet.
3. Ship Phase 10 (`20530162`) to staging. Exercise all six routes by hand plus the two generic ones.
   Confirm the four templates lock exactly the derived fields and nothing else.
4. Run `reconcile --dry-run --sub-scheme 20530162` in production. Expect zero changes (§2.4).
5. Ship Phases 11–17 in order. After each, run `--dry-run` for that phase's sub-schemes.
6. Ship Phase 18. Run `--dry-run` across all 15, attach to the sign-off pack, then `--fix`.
7. Ship Phases 19–20.
8. Settle D-1 and D-2 with the client. If either answer differs from the default, edit one dict entry
   and re-run `--fix --sub-scheme <code>`.
