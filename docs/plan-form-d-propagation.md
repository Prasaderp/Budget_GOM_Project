# TDD — Cross-sheet propagation: प्रपत्र ड → प्रपत्र क / प्रपत्र ब (sub-scheme 20530028)

**Role:** Principal Systems Architect
**Status:** Design. Zero implementation code below.
**Scope:** sub-scheme `20530028` only (District Administration, Voted). No other sub-scheme is touched.
**Builds on** `docs/plan.md` (taluka consolidation) and `docs/plan-taluka-remediation.md`
(write-path rules). Both remain binding.

---

## AMENDMENT 1 — the read-only rule was too wide (Phase 8 corrected)

Phases 0–10 shipped. Field review then found that Phase 8 locked **more than this feature
derives**: प्रपत्र क's entire form was made read-only — all nine measures, the अपडेट रेकॉर्ड button, the
list's द्रुत संपादन block and the `PUT` route — even though §2.8 **C2** of this same document proves
that प्रपत्र क's **Filled/Vacant allocation is not derivable from प्रपत्र ड at all**. Locking it
removed the user's only way to express data the software cannot compute, which is a strictly worse
outcome than the stale-value risk D3 was written to avoid.

**The normative locking rule — the only one, and it supersedes every earlier phrasing:**

> **A field is read-only if and only if propagation writes it.**
> Being *on* a propagation-target table is not a reason to lock a field. Being derived is.

Applied to sub-scheme 20530028, exhaustively — this table is the specification, and Phase 8 and
Phase 11 below implement exactly it:

| Form | Field | Owner | UI |
|---|---|---|---|
| प्रपत्र ड | every column | user | editable |
| प्रपत्र ब | `filled_posts` (भरलेली पदे) | user (§2.8 C2) | **editable** |
| प्रपत्र ब | `vacant_posts` (रिक्त पदे) | derived — LINK 2 (§2.5) | read-only |
| प्रपत्र ब | `medical_expenses`, `festival_advance`, `swagram_maharashtra_darshan`, NPS trio, `other` | user — **not connected** (§2.6) | **editable** |
| प्रपत्र क | `posts`, both statuses | derived — LINK 3 (§2.5) | read-only |
| प्रपत्र क | the 8 money measures, **class total** (`Filled + Vacant`) | derived — LINK 1 (§2.4) | not directly editable |
| प्रपत्र क | the 8 money measures, **Filled/Vacant allocation** | **user** (§2.8 C2) | **editable, authored on the `Filled` row** |
| प्रपत्र क | the 8 money measures on the `Vacant` row | derived (`total − Filled`) | read-only |

**Why the allocation is authored on the `Filled` row only.** One number per measure parameterises the
whole split — once `Filled[m]` is chosen, `Vacant[m] = total[m] − Filled[m]` is forced. Making both
sides editable would add no expressive power and would create a two-way race (which side wins when
both move?). Authoring on `Filled` and deriving `Vacant` is also the **identical mental model the
client already has from प्रपत्र ब**, where भरलेली पदे is typed and रिक्त पदे is computed. One rule,
both forms.

**Why the user's allocation survives later प्रपत्र ड edits — no new mechanism needed.**
`PreserveShareSplit` (D1, §2.9) already reads `old_filled / (old_filled + old_vacant)` as its tier-1
share. After an allocation edit that fraction *is* the user's intent, so the next प्रपत्र ड save
reproduces it exactly when the total is unchanged (the fixed-point property proved in §4.6) and
rescales it proportionally when the total moves. **The Phase 3 seam was designed for this; unlocking
the allocation is what makes D1 mean something.**

Sections rewritten by this amendment: **§2.9 D3**, **§4.1 STEP D** (+ new **STEP E**), **§4.3**,
**§5.2**, **§7**, and **Phase 8**. **Phase 11** is added as the delta for a deployment that already
shipped the original Phase 8.

---

## SCOPE BOUNDARY — read this before anything else

This feature does **one** thing: it reproduces in software the **cross-sheet** links that the
client's workbook makes by hand, so that filling `Page_1` (प्रपत्र ड) automatically fills the
related cells of `Page_2` (प्रपत्र क) and `Page_3` (प्रपत्र ब).

**In scope — cross-sheet only:**

```
Page_1 (प्रपत्र ड)  ──►  Page_2 (प्रपत्र क)      9 measures, class totals
Page_1 (प्रपत्र ड)  ──►  Page_3 (प्रपत्र ब)      sanctioned posts per pay-class → vacant
Page_3 (प्रपत्र ब)  ──►  Page_2 (प्रपत्र क)      the Filled/Vacant post split
```

**Explicitly OUT of scope — every formula that lives *inside* one sheet.** The software's own
intra-sheet calculations (how प्रपत्र ड computes महागाई भत्ता from मुळ वेतन + ग्रेड वेतन, how it
computes घर भाडे भत्ता from `hra_rate`, how the गोषवारा totals a column, how the level aggregator
rolls levels into a post) were **set up to the client's requirement and may deliberately differ from
the workbook.** This document does not change any of them, does not "correct" their rounding, and
does not propose a new column for any value they already produce.

The single rule that connects the two worlds:

> **The aggregator consumes प्रपत्र ड's values exactly as प्रपत्र ड itself produces them.**
> It never re-derives, re-rounds or improves them. If प्रपत्र ड shows a row's महागाई भत्ता as
> 1,563, प्रपत्र क's महागाई भत्ता total must contain 1,563. Matching is the requirement; being
> "more correct" than प्रपत्र ड is a defect.

That rule is what makes this feature safe to ship without touching a single client-owned formula,
and it is restated as a normative constraint in §4.1 and pinned by a test in Phase 10.

---

## 0. WHAT THIS DOCUMENT ASSUMES YOU KNOW

| Concept | Source | Why it matters here |
|---|---|---|
| **The source workbook** | `Divisions/Main files (Original and Translated Files)/Budget 20530028 for 2025-26 (Eng-Translated).xls` | Where the cross-sheet relationships were read from. `Page_1` = प्रपत्र ड, `Page_2` = प्रपत्र क, `Page_3` = प्रपत्र ब |
| Row-role model (`taluka` = `''` / `__district_office__` / `<taluka>`) | `src/core/taluka/constants.py` | Propagation must run **inside one contribution space**, never on consolidated rows |
| Read filter (every ORM SELECT is scoped) | `src/core/taluka/orm_filter.py` | Every query this feature issues **must** opt out via `taluka_scope_all=True` |
| Write redirection + total-space lift | `src/core/taluka/write.py:85-208` | The row a district user edits temporarily holds *district totals*, not its own share |
| Roll-up recomputation | `src/core/taluka/consolidation.py:115-190` | Full recompute, never delta. This feature copies that philosophy exactly |
| Write-path rules 1–4 | `docs/ARCHITECTURE.md` § "Taluka Data Consolidation" | Rule 2 (flush → consolidate → commit, one controller-owned transaction) is extended, not replaced |
| Multi-row fan-out write | `.../post_expenses/controllers/ui_controller.py:350-392` | The existing precedent for "one save touches N rows, each consolidated, one commit" |

### 0.1 How to read the workbook

The file has a `.xls` extension but is an **OpenDocument spreadsheet**
(`mimetype = application/vnd.oasis.opendocument.spreadsheet`, PK zip magic). `xlrd` refuses it
(`XLRDError: Openoffice.org ODS file; not supported`) and so does `pandas.read_excel`. Read it with
`zipfile` + `xml.etree` over `content.xml`; handle `table:number-columns-repeated` /
`table:number-rows-repeated` or column alignment silently shifts.

**The cross-sheet links carry no formulas.** Inside a block, `Page_1` uses real formulas
(`of:=SUM([.G7:.H7])`, `of:=ROUND([.I7]*0.64;0)`). Between sheets there is **not one formula
anywhere** — every `Page_2` and `Page_3` figure was typed by hand from `Page_1`. That is why the
relationships in §2 had to be recovered by matching numbers against row and column headers rather
than by reading formulas, and it is why they are stated below with a hit-rate rather than assumed.

---

## 1. MISSING CONTEXT

**Context sufficient.** All 4 models, all 4 feature modules, all write paths, the seed migration, the
taluka core package, the Excel export populators, the templates and the JS were read end to end, and
the source workbook was parsed cell by cell.

Three business rules remain that only the client can settle. They are isolated in §2.9 with a
recommended default each, and each is implemented as a swappable policy so that changing the answer
is a one-line change, not a redesign.

---

## 2. THE CROSS-SHEET MODEL

### 2.1 The three sheets — headers, shape, and which cells this feature touches

**`Page_1` — प्रपत्र ड.** One block per `(unit, category)`; 8 units × 2 categories = 16 blocks, plus
a Konkan Division roll-up block. Columns:

| Col | Header | DB column | Connected? |
|---|---|---|---|
| A / B / C | Sr No. / Class / Position | `class_type`, `designation` | keys |
| D | Approved Posts 2024-25 | `sanctioned_posts_prev1` | **no** |
| E | Approved Posts 2025-26 | `sanctioned_posts_curr` | **yes** → क `posts`, ब `vacant_posts` |
| F | Special Pay | `special_pay` | **yes** → क `special_pay` |
| G | Basic Pay | `basic_pay` | **yes** → क `salary` |
| H | Grade Pay | `grade_pay` | **yes** → क `grade_pay` |
| I | Total | *(display only, = G+H)* | no — क recomputes its own Total row |
| J | Dearness Allowance 64% | *(computed from G+H)* | **yes** → क `dearness_allowance` |
| K | Local Supplementary Allowance | `local_supplementary_allowance` | **yes** → क `local_supplementary_allowance` |
| L | House Rent Allowance | *(computed from G+H and `hra_rate`)* | **yes** → क `house_rent_allowance` |
| M | Vehicle Allowance | `vehicle_allowance` | **yes** → क `travel_allowance` |
| N | Washing Allowance | `washing_allowance` | **yes** → क `other` (one of three) |
| O | Cash Allowance | `cash_allowance` | **yes** → क `other` (one of three) |
| P | Footwear Allowance / Others | `footwear_allowance_other` | **yes** → क `other` (one of three) |
| Q | Total | *(display only)* | no |

Rows: 14 designations in a Permanent block, 17 in a Temporary block, then a `Total` row, then a
two-cell helper row (`Page_1` D22/E22 style) holding the Class-1&2 and Class-3 post counts — a
cross-check aid the preparer used against `Page_3`. **The helper row carries no information beyond
`Σ sanctioned_posts_curr` per class and needs no counterpart in software.**

**`Page_2` — प्रपत्र क.** One block per `(unit, category)`. Rows are measures, columns are
`Filled × {Class-1 & 2, Class-3, Class-4}` then `Vacant × {…}`:

| Row label | DB column | Source |
|---|---|---|
| Positions | `posts` | ड col E total; Filled/Vacant split from ब |
| Salary | `salary` | ड col G |
| Grade Pay | `grade_pay` | ड col H |
| **Total** | *(none — display only)* | = Salary + Grade Pay |
| Special pay | `special_pay` | ड col F |
| Dearness Allowance | `dearness_allowance` | ड col J |
| St.P.B. | `local_supplementary_allowance` | ड col K |
| House Rent | `house_rent_allowance` | ड col L |
| Traveling Allowance | `travel_allowance` | ड col M |
| Others | `other` | ड cols N + O + P |
| **Total** | *(none — display only)* | grand total |

**11 display rows, 9 stored measures.** `config.py:METRICS_LABELS` (11) vs `METRICS_DB_KEYS` (9)
already encodes exactly this. **No new प्रपत्र क column is needed.**

**`Page_3` — प्रपत्र ब.** Two independent tables per unit:

- **Top — मंजूर पदे / Approved Posts.** Rows = class `1,2,3,4`; columns = Permanent Filled, Permanent
  Vacant, Temporary Filled, Temporary Vacant. `filled + vacant = sanctioned` is the sheet's own
  definition. **This table is connected.**
- **Bottom — district expenses.** Medical Expenses, Festival Advance, Swagram/Maharashtra Darshan,
  one of {7th Pay Commission Difference + NPS | NPS | 7th Pay Commission Difference}, Other, Total.
  One row per district, no class or category dimension. **This table is NOT connected — it has no
  relationship to प्रपत्र ड at all.**

### 2.2 THE CLASS-VOCABULARY TRAP — the hardest part of the whole feature

The three sheets do **not** share a class vocabulary.

```
प्रपत्र ड   class_type ∈ { 'Class-1 & 2', 'Class-3', 'Class-4' }      CLASSES_SHEET1_2
प्रपत्र क   class_type ∈ { 'Class-1 & 2', 'Class-3', 'Class-4' }      CLASSES_SHEET1_2
प्रपत्र ब   class_type ∈ { '1', '2', '3', '4' }                       CLASSES_SHEET3
```
(`config.py:26-27`)

प्रपत्र ब splits Class-1 from Class-2. प्रपत्र ड and क do not. **The split is carried by
`designation`, and nothing in the codebase encodes it today.** Recovering it is mandatory for the
ड → ब link and is the single largest new piece of domain knowledge this feature introduces (§2.5).

### 2.3 THE NAMING TRAPS — four, each able to silently corrupt a column

**(a) `other` means two unrelated things.** प्रपत्र क's `other` is
`washing_allowance + cash_allowance + footwear_allowance_other` rolled up from प्रपत्र ड (workbook
`Page_2` row "Others" = `Page_1` cols N+O+P, verified 48/48). प्रपत्र ब's `other` is a district-level
expense line beside `medical_expenses` (`Page_3` col G). Same column name, no relationship.
**प्रपत्र ब's `other` is user-owned and must never be written by this feature.**

**(b) The workbook's English labels are a different translation from the DB's.** Same Marathi
original, two renderings. A mapping keyed on the workbook string silently misses every row:

| Workbook (`Page_1` col C) | `config.py` `DESIGNATIONS` |
|---|---|
| Tehsildar/Upper Tehsildar/Secretary | Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk) |
| Deputy Tehsildar/Probationary Deputy Tehsildar | Naib Tehsildar/Probationary Naib Tehsildar |
| Senior Clerk | Head Clerk (Awwal Karkun) |
| Top Clerk/Assistant Accountant | Head Clerk/Deputy Accountant |
| Stenographer (Senior) / (Junior) | Stenographer (Higher) / (Lower) |
| Circle Officer | Divisional Officer |
| Soldier/Naik/Havaldar/Watchman/Cleaner | Peon/Naik/Havaldar/Watchman/Cleaner |
| Legal Officer (Honorary) | Law Officer (Honorarium) |
| Clerk/Surveyor/Recovery Clerk | Clerk/Land Surveyor/Recovery Clerk |
| Tele-Operator / Junior Stenographer (Legal Dept. Assistant) | Telephone Operator/Steno-Typist(Law Officer Asst.) |

**`DESIGNATION_PAY_CLASS` (§2.5) keys on the `config.py` spelling, never the workbook's.** Workbook
spellings appear in this document only as evidence.

**(c) Permanent and Temporary use different designation strings for the same post.** The Permanent
block has 14 designations, Temporary has 17, and five posts change name between them
(`Deputy Collector` ↔ `Deputy Collector / Probationary Deputy Collector`, and so on). The Excel
export populator already encodes this collapse as `perm_aliases` / `temp_aliases`
(`excel_export/populators/budget_post_details.py:71-87`). **`DESIGNATION_PAY_CLASS` must contain both
spellings of every Class-1 & 2 post** — omitting the Temporary variant of `Tehsildar` alone
misclassifies 29 posts in Konkan Division.

**(d) District labels differ between workbook and DB.** Workbook `Mumbai Suburbs` / `रायगड`
(untranslated) vs DB `Mumbai Suburban` / `Raigad`; workbook `Deputy Commissioner (S.P.) Konkan
Division` vs DB `DCO Staff`. Worse, **`Page_2` labels the Mumbai Suburban block "Mumbai City"**
(rows 39 and 54) — the district-name cell was copy-pasted and never corrected. Any tool reading the
workbook must map blocks **by position, not by the label in column A**. This affects the Phase 9
reconcile script only; nothing in the request path reads the workbook.

### 2.4 LINK 1 — प्रपत्र ड → प्रपत्र क

Both tables store money **in thousands of rupees** (`(Figures In Thousands)` on every workbook block
header; `(आकडे हजारात)` in the list footer). **No unit conversion anywhere in this feature.**

For one प्रपत्र क cell = `(fiscal_year, district, category, class_type)` — before the Filled/Vacant
split — over the प्रपत्र ड rows sharing that `(district, category, class_type)`:

| प्रपत्र क column | Rule |
|---|---|
| `posts` | total = `Σ sanctioned_posts_curr`; the Filled/Vacant split comes from प्रपत्र ब (§2.5) |
| `salary` | `Σ basic_pay` |
| `grade_pay` | `Σ grade_pay` |
| `special_pay` | `Σ special_pay` |
| `dearness_allowance` | `Σ` **प्रपत्र ड's own per-row महागाई भत्ता**, computed exactly as प्रपत्र ड computes it |
| `local_supplementary_allowance` | `Σ local_supplementary_allowance` |
| `house_rent_allowance` | `Σ` **प्रपत्र ड's own per-row घर भाडे भत्ता**, computed exactly as प्रपत्र ड computes it, from each row's own `hra_rate` |
| `travel_allowance` | `Σ vehicle_allowance` |
| `other` | `Σ (washing_allowance + cash_allowance + footwear_allowance_other)` |

**On महागाई भत्ता and घर भाडे भत्ता — why no new column is needed.** प्रपत्र ड does not store these
two; it computes them per row for display (`budget_post_details_form.html:158-166`) from
`basic_pay + grade_pay`, the fiscal-year `da_rate` (`get_da_rate`, `utils_da_rate.py:48`) and the
row's own `hra_rate` (`HRA_RATE_MAP`, `config.py:151`). **That is client-owned intra-sheet logic and
this feature does not change it.** The aggregator simply applies the same expression to each ड row it
scans and sums the results — the arithmetic प्रपत्र क's column is defined to hold.

Because the scan runs **per contribution space** and reads each row's own `hra_rate`, this works
correctly under taluka consolidation with no stored column: a taluka on `Z` and the district office
on `X` each contribute their own correctly-rated figure, and `consolidate_row()` sums the क
contributions. Storing an aggregate `hra_rate` on a consolidated ड row would have been wrong
(`_column_classes()` copies `CHAR` from the office row, `consolidation.py:30-42`) — the
per-contribution scan sidesteps that entirely.

**Per-row rounding, then sum — not sum then round.** Two reasons, both binding:
1. It is what प्रपत्र ड shows. Each ड row displays its own rounded महागाई भत्ता; क's total must be
   the sum of the numbers the user can see (the scope rule at the top of this document).
2. Per-row rounding is *exactly additive across taluka contributions*:
   `Σ_all rows = Σ_talukas Σ_that taluka's rows`. Summing first and rounding once is not, and would
   break the invariant `scripts/check_taluka_invariant.py` enforces.

**Bounded, stated drift.** प्रपत्र ड's गोषवारा totals a whole class in one expression, so its
महागाई भत्ता figure is `round((Σb + Σg) × rate)` while derived प्रपत्र क is
`Σ round((b + g) × rate)`. For a district with no active taluka these differ by at most 0.5 per
designation and in practice by ≤ 1 thousand per cell. **This is a consequence of प्रपत्र ड having two
of its own display paths, not something this feature introduces or may fix.** Stated here so it is
never filed as a propagation bug.

**प्रपत्र ड columns that connect to nothing:** `sanctioned_posts_prev1` (मंजूर पदे 2024-25, col D) —
प्रपत्र क has no prior-year dimension — and `hra_rate`, which is an input to a formula, not a
measure. **प्रपत्र क columns with no प्रपत्र ड source:** none. All nine are covered.

### 2.5 LINK 2 — प्रपत्र ड → प्रपत्र ब, and LINK 3 — प्रपत्र ब → प्रपत्र क

`Page_3`'s top table is **मंजूर पदे**, split into Filled and Vacant per class per category. So:

| प्रपत्र ब column | Ownership | Rule |
|---|---|---|
| `filled_posts` (भरलेली पदे) | **USER-OWNED** — the only Filled/Vacant input in the system | never rewritten; validated `≤ sanctioned` |
| `vacant_posts` (रिक्त पदे) | **DERIVED** | `max(0, Σ sanctioned_posts_curr(pay_class) − filled_posts)` — §4.1 STEP B explains why the floor is on `vacant` and never on `filled` |
| `medical_expenses`, `festival_advance`, `swagram_maharashtra_darshan`, `other`, NPS trio | **USER-OWNED** | **not connected**; the district-wide fan-out sync stays exactly as-is (`post_expenses_service.py:214-243`) |

**LINK 3** closes the loop: प्रपत्र क's `posts` Filled/Vacant split is प्रपत्र ब's post table rolled
up `{1,2} → Class-1 & 2`, `3 → Class-3`, `4 → Class-4`, per category. That is why **प्रपत्र ब is a
second trigger** (§4.1) — editing भरलेली पदे must move प्रपत्र क in the same request.

**The pay-class of a प्रपत्र ड row:**

```
class_type == 'Class-3'      → pay_class '3'
class_type == 'Class-4'      → pay_class '4'
class_type == 'Class-1 & 2'  → DESIGNATION_PAY_CLASS[designation]   ← [NEW] lookup
```

`DESIGNATION_PAY_CLASS` (to live in `config.py` beside `POSITION_ORDER`), **both spellings of every
post** (§2.3c):

```
'1' (Group A / राजपत्रित):
    Collector
    Additional Collector
    Deputy Collector
    Deputy Collector / Probationary Deputy Collector
    Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)
    Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar

'2' (Group B):
    Naib Tehsildar
    Naib Tehsildar/Probationary Naib Tehsildar
    Accounts Officer
    Asst. Accounts Officer
    Law Officer (Honorarium)
```

Every string is copied verbatim from `config.py:44-56` (`DESIGNATIONS`) and `config.py:79-81` (the
three Temporary-only variants). Unknown designation → `'2'` + a WARNING log (never a silent `'1'`,
which would inflate the gazetted count).

### 2.6 WHAT IS DELIBERATELY NOT CONNECTED

Stating this explicitly, because "connect everything" is the failure mode this section exists to
prevent:

| Not connected | Why |
|---|---|
| प्रपत्र ड `sanctioned_posts_prev1` (col D) | प्रपत्र क and ब have no prior-year dimension. Nothing to write it into |
| प्रपत्र ड `hra_rate` | an input to an intra-sheet formula, not a measure |
| प्रपत्र ड cols I and Q (the two `Total` columns) | display-only in the workbook; प्रपत्र क computes its own Total rows from the measures it already holds |
| प्रपत्र ड's helper row (post counts per class, e.g. `Page_1` D22/E22) | a manual cross-check aid; carries nothing beyond `Σ sanctioned_posts_curr` per class, which the derivation computes anyway |
| प्रपत्र क's two `Total` rows | display-only, 11 labels vs 9 stored columns (§2.1) |
| प्रपत्र ब's entire expense table (medical, festival, swagram, NPS trio, other) | no dimension in common with प्रपत्र ड — district-level only, no class, no category, no designation. Stays user-owned with its existing fan-out sync |
| प्रपत्र ब `filled_posts` | the **user's input**; deriving it would destroy the only Filled/Vacant data the system has (§2.8) |
| प्रपत्र अ (`unit_expenditure`, `Page_4`) | natural key is `(fiscal_year, district, unit_account)` — no `category`, `class_type` or `designation` dimension at all. No relationship exists |
| The Konkan Division roll-up blocks | verified to be the exact arithmetic sum of the 8 units on both `Page_1` and `Page_2`. Has no table of its own; `district_wise_abstract` already computes it |
| Every intra-sheet formula in the software | client-owned (see SCOPE BOUNDARY) |

### 2.7 EVIDENCE — the cross-sheet links, recovered from the numbers

There is not one cross-sheet formula in the workbook (§0.1), so every link below was recovered by
matching values against row and column headers across all 8 units × 2 categories, and then
re-checked against the seed migration.

**A. प्रपत्र ड class totals == प्रपत्र क (Filled + Vacant).** 8 units × 2 categories × 3 classes =
48 cells:

| प्रपत्र क measure | Result |
|---|---|
| Positions | **48 / 48 exact** |
| Salary | **48 / 48 exact** |
| Grade Pay | **48 / 48 exact** (zero workbook-wide) |
| Special pay | **48 / 48 exact** |
| Dearness Allowance | **48 / 48 exact** |
| St.P.B. | **48 / 48 exact** |
| House Rent | **48 / 48 exact** |
| Traveling Allowance | **48 / 48 exact** |
| Others (washing + cash + footwear) | **48 / 48 exact** |

LINK 1 is not approximate. Every one of the nine measures is an exact class-wise sum, in every cell.
This is the strongest possible mandate for automating it.

**B. प्रपत्र ब post counts roll up into प्रपत्र क** (`{1,2} → Class-1 & 2`, `3 → Class-3`,
`4 → Class-4`, per category, both Filled and Vacant): **95 / 96 exact**. The single miss is an
inconsistency *inside the workbook* — Mumbai Suburban / Temporary / Class-1 & 2 Vacant: `Page_3`
says 8, `Page_2` says 5. Test A shows `Page_2` is the one consistent with प्रपत्र ड, so `Page_3`'s
class-2 vacant figure is 3 too high. **The seed already corrects it** (stores 3, not 6).

**C. `DESIGNATION_PAY_CLASS` reproduces प्रपत्र ब's Class-1 vs Class-2 split.**
`Σ sanctioned_posts_curr` per `(unit, category, pay_class)` vs `filled + vacant` in `Page_3`:
**61 / 64 exact**; on the Class-1 & 2 cells alone, **28 / 32 exact**. Zero unmapped designations. The
three misses are fully accounted for:

- Mumbai Suburban / Temporary / class 2 (+3) — the `Page_3` error from test B, not a mapping error.
- Raigad / Temporary / classes 1 and 2 (−2 / +2) — derived 7 / 23, workbook 9 / 21. One district's own
  classification variance. This is D2 in §2.9.

**D. Seed migration fidelity** (does the DB already agree with the workbook?):

| Table | Cells compared | Mismatches |
|---|---|---|
| `budget_post_details_20530028` (10 stored columns × 248 rows) | 2,480 | **0** |
| `post_status_20530028` (9 measures × 96 rows) | 864 | **1** — Mumbai Suburban / Permanent / Class-1 & 2 / Filled: `special_pay` workbook 10, seed 0 |
| `post_expenses_20530028` (2 post columns × 64 rows) | 128 | **1** — the *deliberate* correction from test B |

The seed is an excellent transcription. Its one genuine defect is in प्रपत्र क, which this feature
overwrites anyway — propagation fixes it as a side effect, and `reconcile --dry-run` will show it as
`+10` on that one cell. Put it in the sign-off pack so it is not mistaken for a propagation bug.

### 2.8 THE ONE THING प्रपत्र ड CANNOT SUPPLY — the Filled/Vacant split

प्रपत्र ड has no Filled/Vacant dimension at all. It gives every प्रपत्र क **total**; it says nothing
about how that total divides between भरलेली and रिक्त. For each of the 42 non-empty cells the vacant
side was tested against two candidate rules:

| प्रपत्र क measure | `vacant = round(total × post-vacant-share)` | `vacant = round(total × salary-vacant-share)` |
|---|---|---|
| Salary | 9 / 42 | *(tautological)* |
| Dearness Allowance | **7 / 42** | **35 / 42** exact, 42 / 42 within ±1 |
| House Rent | **9 / 42** | **27 / 42** exact, 31 / 42 within ±1 |
| Traveling Allowance | 14 / 42 | 11 / 42 |
| St.P.B. | 13 / 28 | 12 / 28 |
| Others | 6 / 24 | 6 / 24 |

Two conclusions, and they bound the whole feature:

> **C1.** प्रपत्र ड *fully determines the total* of every प्रपत्र क measure and of प्रपत्र ब's
> sanctioned post count — exact in 48/48 cells on all 9 measures. **This part is safe to automate
> outright, and automating it is the client's entire request.**
>
> **C2.** The **split is real user data.** No formula reproduces it for `St.P.B.`,
> `Traveling Allowance` or `Others` at all. For post counts it lives in प्रपत्र ब (`filled_posts`);
> for money it lives in प्रपत्र क itself. **Propagation must preserve it, never invent it.** A
> version of this feature that recomputes the split from post counts would silently destroy every
> district's existing allocation.

Where a fallback *is* unavoidable (a brand-new all-zero cell), the **salary share is the right anchor,
not the post share**: for महागाई भत्ता and घर भाडे भत्ता — 92 % of all non-salary money in this
sub-scheme (₹800,044k of ₹872,708k) — the salary share is 4–5× more accurate. §2.9 D1 puts it in the
chain.

### 2.9 THREE BUSINESS DECISIONS — recommended defaults, each swappable

| # | Question | Recommended default | Where it lives | Cost to change |
|---|---|---|---|---|
| **D1** | When प्रपत्र ड changes, how is the new total split between Filled and Vacant *money* in प्रपत्र क? | **`PreserveShareSplit`** — keep each measure's current Filled fraction and rescale to the new total. Fallback chain, in order: (1) the measure's own `old_filled/(old_filled+old_vacant)`; (2) **the same cell's salary fraction** (§2.8); (3) the post fraction; (4) `1.0`. Preserves every district's existing figures on day one. | `derivation/split_policy.py` [NEW], one class | one line in `SPLIT_POLICY = …` |
| **D2** | Is `DESIGNATION_PAY_CLASS` (§2.5) the government's actual Group A/B boundary? | **Yes, as listed.** 61/64 workbook cells agree; the two genuine misses are one district's variance (Raigad/Temporary, ±2 posts) and one workbook arithmetic error. | `config.py` dict | edit the dict, re-run reconcile |
| **D3** | After propagation, may a district still hand-edit प्रपत्र क? | **Only the allocation, never the totals** (revised — see AMENDMENT 1). A district edits `Filled[m]` on the eight money measures; `Vacant[m]` is then forced to `total[m] − Filled[m]`, and `posts` stays locked on both rows. The class **total** of every measure remains owned by प्रपत्र ड and cannot be typed. The original "lock all nine" answer was wrong: §2.8 C2 proves the allocation is not derivable, so locking it deleted the only input the system has for it. | Phase 8 / Phase 11, `derivation/allocation.py` | narrowing again = mark the eight measures `readonly` on the `Filled` row too |

---

## 3. BLAST RADIUS

### 3.1 Complexity

**Rating: L** — cross-module (3 feature modules + `src/core`), no schema change, a new data-flow
invariant, a new reconciliation tool. Required sections: 3, 4, 5, 6.

### 3.2 Files affected

**New (7 source + 4 test):**

```
src/core/derivation/__init__.py
src/core/derivation/registry.py
src/schemes/s2053/subs/s20530028/derivation/__init__.py
src/schemes/s2053/subs/s20530028/derivation/mapping.py
src/schemes/s2053/subs/s20530028/derivation/aggregator.py
src/schemes/s2053/subs/s20530028/derivation/split_policy.py
src/schemes/s2053/subs/s20530028/derivation/service.py
src/schemes/s2053/subs/s20530028/derivation/allocation.py      # AMENDMENT 1 (STEP E)
scripts/reconcile_form_derivation.py
tests/test_s20530028_derivation_mapping.py
tests/test_s20530028_derivation_aggregator.py
tests/test_s20530028_derivation_split.py
tests/test_s20530028_derivation_e2e.py
```

**Modified (11):**

| File | Change | Phase |
|---|---|---|
| `static/js/post_levels.js` | page load must GET aggregates, not POST them (§3.3) | 0 |
| `.../s20530028/config.py` | `+ DESIGNATION_PAY_CLASS`, `+ PAY_CLASS_TO_STATUS_CLASS`, `+ DERIVED_*` field tuples | 1 |
| `.../budget_post_details/controllers/api_controller.py` | propagation hook after `consolidate_row` | 5 |
| `.../budget_post_details/controllers/ui_controller.py` | propagation hook after `consolidate_row` | 5 |
| `src/schemes/common/post_levels/api_router.py` | `apply-aggregates` calls the propagation hook | 6 |
| `src/core/secure_crud.py` | registry lookup after `consolidate_row` / `create_row_family` / `delete_row_family` | 6 |
| `.../post_expenses/utils/validators.py` | `filled ≤ sanctioned` | 7 |
| `.../post_expenses/services/post_expenses_service.py` | `vacant_posts` becomes derived | 7 |
| `.../post_expenses/controllers/{ui,api}_controller.py` | lock hoist + propagation hook; deterministic fan-out order | 7 |
| `.../post_status/controllers/{ui,api}_controller.py` | `posts` and `Vacant` rows rejected server-side; allocation writes accepted on `Filled` rows, then rebalanced (STEP E) | 8 / 11 |
| `.../s20530028/schemas.py` | narrow `PostStatusUpdate` (empty; `PUT` suppressed) and `PostExpensesUpdate` (drop `vacant_posts` only) | 8 |
| 4 templates (क and ब) | **derived** fields read-only in the UI; everything else stays editable | 8 / 11 |

**No schema change. No migration. No new column on any table.** A stored `house_rent_allowance` on
प्रपत्र ड is not needed and would be wrong: §2.4 shows the per-contribution scan reads each row's own
`hra_rate` and applies प्रपत्र ड's existing formula, which is both correct under taluka consolidation
and, by the scope rule, the only acceptable behaviour. Persisting the value would freeze a number the
client's intra-sheet formula owns.

**Explicitly NOT touched:**

- **Every intra-sheet formula** — `ui_budget_summary.py`, `budget_post_details_form.html`'s
  महागाई भत्ता / घर भाडे भत्ता boxes, `post_levels/service.py`'s aggregate arithmetic,
  `budget_post_service.py`'s column handling. Client-owned (see SCOPE BOUNDARY).
- **`excel_export/*`** — all four populators. `post_status.py` and `post_expenses.py` write the
  stored columns straight into the exact workbook cells (verified against `Page_2` rows
  7-16/22-31/40-49/… and `Page_3`), so they become correct for free.
  `budget_post_details.py` computes प्रपत्र ड's own महागाई भत्ता / घर भाडे भत्ता with its own
  expression — intra-sheet, untouched.
- `unit_expenditure/*`, `src/chatbot/*` (reads `v_*_district` views), `ui_abstract.py`,
  `ui_category_info.py`.

### 3.3 The one prerequisite defect — `apply-aggregates` zeroes posts that have no levels

`PostLevelsManager` is constructed for every प्रपत्र ड edit form that has an id
(`_levels_section.html:145-155`, no guard beyond `detail.id`); `init()` (line 28) calls `loadLevels()`
(210), which unconditionally calls `syncMainForm()` (218), which **POSTs** `/{id}/apply-aggregates`
(463). With no levels, `calculate_aggregates()` returns an all-zero `AggregatedTotals`
(`service.py:196-211`) and `apply_aggregates_to_budget_post()` assigns those zeros to all eight pay
columns (`service.py:279-287`); the endpoint then consolidates and commits
(`api_router.py:471-481`).

**Merely opening the प्रपत्र ड edit form on a post that has no levels zeroes its pay data.** All 248
seeded rows have no levels. This is live today and independent of this feature — but it is a hard
blocker for Phase 6, which hooks that exact endpoint: propagation would carry the zeros straight into
प्रपत्र क and प्रपत्र ब. Phase 0 fixes it, JS-only.

This is a **call-site bug, not a formula**: the page-load path must use the existing read-only
`GET /{id}/aggregates` (`api_router.py:376`) instead of the write endpoint. No calculation changes.

### 3.4 Dependency changes

**None.** Everything is stdlib + SQLAlchemy + Pydantic + FastAPI, all already in `requirements.txt`.
The workbook parser needed by Phase 9's reconcile script uses `zipfile` + `xml.etree` only —
**do not add `odfpy` or `xlrd`.**

---

## 4. DATA & RESILIENCE

### 4.1 The propagation algebra (normative)

**Two triggers, not one.** प्रपत्र ड determines every *total*; प्रपत्र ब's `filled_posts` determines
the Filled/Vacant *allocation* of post counts (LINK 3, verified 95/96). Both are user-editable, so
both must run the propagation — otherwise editing प्रपत्र ब's भरलेली पदे leaves प्रपत्र क's `posts`
stale until the next प्रपत्र ड save. The algebra is identical for both; only the entry point differs.

Let `t` be a **contribution** taluka value — `'__district_office__'` or an active taluka name.
**Never `''`.** Writing into the consolidated row directly would break the invariant
`row('') == Σ contributions` that `scripts/check_taluka_invariant.py` guards.

`t` comes from the caller's cookie via `_writable_taluka_value()` (`write.py:85-121`), **never** from
`row.taluka`: `create_row_family()` returns the *consolidated* row (`write.py:286`), so a hook that
read `row.taluka` would attempt to write into `''`. `district`, `fiscal_year` and `category` come from
the resolved row, **never** from `get_fiscal_year_from_request()` — the row being edited may belong to
a fiscal year other than the caller's active one, and `resolve_editable_row()` does not filter by
fiscal year.

For a fixed `(t, district, fiscal_year, category)`:

```
STEP A — scan प्रपत्र ड
  for each ड row r with r.taluka == t and matching district/fy/category:
      pc  = pay_class(r)                     # section 2.5
      PC[pc].sanctioned += r.sanctioned_posts_curr
      PC[pc].salary     += r.basic_pay                       (Decimal, exact)
      PC[pc].grade_pay  += r.grade_pay
      PC[pc].special_pay+= r.special_pay
      PC[pc].lsa        += r.local_supplementary_allowance
      PC[pc].travel     += r.vehicle_allowance
      PC[pc].other      += r.washing + r.cash + r.footwear
      PC[pc].da         += FORM_D_DA(r)      # प्रपत्र ड's own expression, per row
      PC[pc].hra        += FORM_D_HRA(r)     # प्रपत्र ड's own expression, per row, r.hra_rate
  salary is quantised to an integer once, at the end of the cell.

STEP B — write प्रपत्र ब  (4 rows: pay_class '1','2','3','4')
  sanctioned := PC[pc].sanctioned
  filled     := row.filled_posts                      # USER-OWNED, never rewritten
  vacant     := max(0, sanctioned - filled)           # DERIVED; chk_pe_20530028_vacant_posts >= 0
  # every money column untouched; WARN when filled > sanctioned (section 4.5)

STEP C — roll pay-classes up to प्रपत्र क classes
  C['Class-1 & 2'] = PC['1'] + PC['2']       (measure-wise)
  C['Class-3']     = PC['3']
  C['Class-4']     = PC['4']
  filled_posts(cc) / vacant_posts(cc) = sum of the ब rows that map to cc      # LINK 3

STEP D — write प्रपत्र क  (6 rows: 3 classes x {Filled, Vacant})
  posts:  Filled := filled_posts(cc);  Vacant := vacant_posts(cc)     # NOT ratio-split
  salary is resolved FIRST, because every other measure's fallback reads its share:
      share_f(salary) = SPLIT_POLICY.filled_share('salary', ...)
  for each remaining money measure m:
      total   = C[cc][m]
      share_f = SPLIT_POLICY.filled_share(m, old_filled, old_vacant,
                                          filled_posts(cc), vacant_posts(cc),
                                          salary_share_f)
      new_filled = int(round(total * share_f))
      new_vacant = total - new_filled          # by subtraction => sum is exact, always
```

**STEP E — the reverse path: a प्रपत्र क allocation edit** (AMENDMENT 1). STEPS A–D run when
प्रपत्र ड or प्रपत्र ब moves. STEP E runs when the **user re-allocates** a प्रपत्र क measure between
भरलेली and रिक्त. It is not propagation — no total changes — it is the maintenance of the one
invariant that lets an editable `Filled` coexist with a derived total:

```
INVARIANT I1   for every measure m of the 8, per (t, district, fy, category, class):
               Filled[m] + Vacant[m] == C[class][m]        # the प्रपत्र ड-derived total

STEP E — rebalance after the user writes Filled  (contribution space t)
  precondition: the edited row's status == 'Filled'      # 'Vacant' rows reject the write, 409
  C   = roll_up_to_status_classes(aggregate_pay_classes(db, taluka=t, ...))   # STEPS A + C, read-only
  for each money measure m of the 8:
      vacant[m] := max(0, C[class][m] - filled_row[m])    # floor on the DERIVED side only
      WARN when filled_row[m] > C[class][m]
  posts on both rows: NOT touched — owned by STEP D via LINK 3
```

**The floor is on `vacant`, never on `filled` — the same rule as STEP B, for the same reason.**
`filled_row[m]` is the number the user just typed; silently clamping it would rewrite their input.
Flooring `vacant` at 0 keeps the CHECK constraint satisfied and leaves the anomaly *visible*
(`Filled + Vacant > total`), which `reconcile --dry-run` reports. The up-front validator (§5.2)
rejects the same condition with a 400 while the user is still on the form and can act on it, so the
floor is a backstop for the district-total-vs-office-share edge case below, not the normal path.

**Space discipline — the single easiest thing to get wrong in STEP E.** STEP E runs **after**
`consolidate_row()` has rebased the edited row out of total space (§4.2), so both rows and the
प्रपत्र ड scan are in the *same* contribution space `t`. Do not mix: validating in total space
(§5.2) and rebalancing in contribution space is deliberate and correct — the first is what the user
typed, the second is what gets stored. Because the invariant is enforced per contribution and every
column is additive, `consolidate_row()` makes I1 hold on the consolidated rows for free:
`Σ_t Filled[m] + Σ_t Vacant[m] == Σ_t C[m]`.

**Bounded, stated consequence.** For a district *with active talukas*, the office share and each
taluka's share each keep their own allocation fraction. A later प्रपत्र ड edit rescales only the
space it touched, so the district-level Filled fraction can drift slightly from the one the user
typed at district level. This is inherent to per-contribution derivation and is already D1's
documented behaviour — stated here so it is never filed as an allocation bug.

**`FORM_D_DA` and `FORM_D_HRA` are the scope rule made concrete.** They are thin adapters that apply
**प्रपत्र ड's existing expressions** — `round((basic_pay + grade_pay) × get_da_rate(db, fiscal_year))`
and `round((basic_pay + grade_pay) × HRA_RATE_MAP[hra_rate])`, matching
`budget_post_details_form.html:158-166` — to one ड row. They live in `derivation/mapping.py` so the
propagation path has a single, testable definition of "what प्रपत्र ड says this row is worth".
**They must never be 'improved'**: not the rounding mode, not the rate source, not the treatment of
a missing `hra_rate`. If the client later changes प्रपत्र ड's intra-sheet formula, these two adapters
are the only place this feature needs to follow.

`new_vacant` by subtraction is deliberate and matches what the workbook's preparer did: it makes
`Filled + Vacant == total` an identity, not something a rounding rule has to be trusted to preserve.
**Salary must be resolved before the other measures** so its share is available as fallback tier 2;
this ordering is a correctness requirement of D1, not a convenience.

**Cardinality of one propagation run:** ≤ 4 प्रपत्र ब rows + 6 प्रपत्र क rows written, plus 10
`consolidate_row()` calls, for **one** `(t, district, fy, category)`. A प्रपत्र ड edit only ever
affects its own `category`, so the other category is never touched. Bounded and small.

### 4.2 Transaction boundaries

**One transaction, owned by the controller.** This extends write-path rule 2 verbatim:

```
resolve_editable_row(ड)                     # existing
   -> mutate ड                              # existing
   -> db.flush()                             # existing
   -> consolidate_row(BudgetPostDetails,...) # existing  -- MUST come first, see below
   -> derive_from_form_d(db, ड_row, request) # NEW
   -> db.commit()                            # existing
```

**Why propagation must run *after* `consolidate_row(BudgetPostDetails, …)` and never before.** For a
district or DCO caller, `resolve_editable_row()` returns the office row **lifted into total space** —
its additive columns temporarily hold *district totals*, flagged with `TOTAL_SPACE_FLAG`
(`write.py:197-208`). Its sibling ड rows in the same cell are **not** lifted; they hold office shares.
Scanning `taluka == '__district_office__'` in that state mixes one total-space row with N share-space
rows and produces garbage. `consolidate_row()` calls `_rebase_from_total_space()`
(`consolidation.py:93-115`), which converts the lifted row back to a share and clears the flag — so
the instant it returns, every ड row in that space is comparable again. **Ordering is a correctness
requirement, not a style preference.** The propagation entry point asserts
`not getattr(row, TOTAL_SPACE_FLAG, False)` and raises loudly if violated.

The `before_commit` backstop `_rebase_lifted_rows_before_commit()` (`write.py:211-224`) does **not**
rescue propagation that ran too early: it rebases at commit time, long after the bad scan.

**Failure ⇒ full rollback of the प्रपत्र ड edit too.** Intentional. A प्रपत्र ड save that "succeeded"
while its propagation failed leaves the three forms permanently disagreeing with no signal to the
user. Better to fail the save with a Marathi message.

### 4.3 Concurrency — and a real deadlock this feature would otherwise introduce

Two assistants of the same district editing two different designations of the *same*
`(category, class_type)` cell — e.g. `Clerk` and `Vehicle Driver`, both Class-3 — write to the
**same** प्रपत्र ब and प्रपत्र क rows.

Because propagation is a **full recomputation from प्रपत्र ड**, a lost update is self-healing: the
later writer recomputes everything from committed state. The genuine hazard is a **stale read** of
प्रपत्र ड under READ COMMITTED — B begins, A commits its ड change, B reads pre-A ड rows and writes a
stale क.

**Mitigation — lock first, then read:** at the top of the propagation, take `SELECT … FOR UPDATE` on
the **consolidated** (`taluka=''`) प्रपत्र ब and प्रपत्र क rows of the affected cells, *before* the
STEP A scan. Two runs for the same cell then serialise, and the second one's ड scan happens after the
first commits. This is the same lock `consolidate_row()` already takes
(`consolidation.py:132-142`, `.with_for_update()`), on the same rows — **no new lock object, only an
earlier acquisition.**

**Global lock order, documented in `derivation/service.py`:**

```
1. BudgetPostDetails consolidated row
2. PostExpenses  consolidated rows, pay_class ascending:  '1','2','3','4'
3. PostStatus    consolidated rows, ordered by VALID_CLASS_KEYS then ('Filled','Vacant')
```

**The प्रपत्र ब entry point violates that order unless the lock acquisition is hoisted.** On the
प्रपत्र ड path the first lock is on a *different table* (rank 1), so there is no conflict. On the
प्रपत्र ब path there is:

- Assistant A edits ब class `'3'`. `consolidate_row()` locks consolidated ब`'3'` first. Propagation
  then wants ब`'1'`, `'2'`, `'3'`, `'4'`.
- Assistant B edits ब class `'1'`. `consolidate_row()` locks consolidated ब`'1'` first. Propagation
  then wants ब`'1'`…`'4'`.
- A holds ब`'3'` and waits for ब`'1'`; B holds ब`'1'`, takes ब`'2'`, waits for ब`'3'`. **Deadlock.**
  Postgres aborts one transaction and the assistant gets a 500.

**Normative fix (Phase 7):** on the प्रपत्र ब path the ordered lock set is acquired **immediately
after `resolve_editable_row()` and before `consolidate_row()`**. Re-locking a row the transaction
already holds is a no-op, so `consolidate_row()` is unaffected. The प्रपत्र ड path needs no change.

**The प्रपत्र क allocation path violates the order in the same way, and takes the same fix**
(AMENDMENT 1). A प्रपत्र क save consolidates the edited row first — a rank-3 lock — and STEP E then
wants the rank-2 प्रपत्र ब rows plus the paired `Vacant` row. Two assistants editing
`Class-3 / Filled` and `Class-1 & 2 / Filled` of one district would deadlock exactly as the two
प्रपत्र ब assistants above do. **`acquire_derivation_locks(db, district, fiscal_year, category)` is
therefore called immediately after `resolve_editable_row()` on the प्रपत्र क write path too, before
any `consolidate_row()`.** It is the same function, the same rows and the same order — no new lock
object is introduced by unlocking the allocation.

**A second, pre-existing hazard in the same handler.** The district-wide fan-out at
`post_expenses/controllers/ui_controller.py:358-390` resolves every प्रपत्र ब row of the district
(8 rows: 4 classes × 2 categories) from an **unordered** query and consolidates them in whatever order
the DB returns. Two concurrent प्रपत्र ब saves in the same district can already deadlock on that loop
today. Phase 7 adds a deterministic `ORDER BY category, class_type`. Small change, same root cause.

### 4.4 Caching

`CacheService.invalidate_scheme_cache(district)` (`shared/services/cache_service.py:8-38`) is
**already called** by every प्रपत्र ड write handler, so no new invalidation call site is needed.

> **Pre-existing defect, in scope to flag, out of scope to fix here.**
> `invalidate_scheme_cache` matches cache keys by substring (`"post_status" in k`), but
> `MemoryCache._make_key()` returns a **blake2b hex digest** (`src/utils_cache.py:44-45`). No
> substring can ever match a hashed key, so the `@ttl_cache(ttl_seconds=180)` on the summary services
> is **never invalidated**. Consequence: प्रपत्र क's गोषवारा view can lag a propagation by up to
> 180 s. Acceptable — the edit view is uncached and correct immediately. Phase 10 pins the bound with
> a test so nobody mistakes it for a propagation bug; the real fix is a separate ticket touching every
> scheme and must not ride along here.

No new cache is introduced. Propagation reads at most ~31 प्रपत्र ड rows per call; caching that would
add invalidation surface for no measurable gain.

`get_da_rate()` is already memoised for 300 s (`utils_da_rate.py:16`). A DA-rate change therefore does
not retro-propagate — that is what `scripts/reconcile_form_derivation.py` is for (Phase 9), and the
DA-rate admin endpoint should call it.

### 4.5 Failure handling

| Failure | Behaviour |
|---|---|
| DB down mid-propagation | transaction rolls back; प्रपत्र ड edit is not persisted; handler returns 500 |
| `consolidate_row()` raises `HTTPException(400)` (district total below what talukas reported, `consolidation.py:100-110`) | **must propagate with status and Marathi detail intact** — write-path rule 4. Never wrap it in a bare `except Exception` |
| प्रपत्र ब / क contribution row missing for `t` | `ensure_contribution_row(db, Model, consolidated_row, t)` (`write.py:232-258`) — idempotent, lazily creates it zeroed |
| प्रपत्र ब / क **consolidated** row missing (twinless family) | log ERROR and raise. A structural breach owned by `scripts/check_taluka_invariant.py`, never something to silently repair mid-request |
| `filled_posts > sanctioned` after a प्रपत्र ड reduction | `vacant := 0`; `filled` is **left untouched** and a WARNING logged. Never clamp `filled` — that silently rewrites a number the user is not currently editing. The anomaly stays visible (क's `Filled + Vacant` then exceeds ड's sanctioned) and `reconcile --dry-run` reports it. The प्रपत्र ब save path rejects the same condition up-front with 400, which is where the user can act on it |
| Unknown designation | pay_class `'2'` + WARNING log with the designation string |
| प्रपत्र ड row with an unrecognised `class_type` | skip the row + WARNING, matching the precedent at `ui_budget_summary.py:64-66`. Must not `KeyError` into a 500 — that would make the ड row unsaveable |
| Deleted row's identity needed after `delete_row_family()` | capture `district`, `fiscal_year`, `category` **before** the delete; the ORM instance is expired afterwards (Phase 6) |

### 4.6 Idempotency

Guaranteed structurally, not by keys. Propagation is a pure function of
`(प्रपत्र ड rows, प्रपत्र ब.filled_posts, प्रपत्र क current split, da_rate)` → complete row values.
Running it twice with unchanged inputs writes identical values — the same guarantee `consolidate_row()`
gives ("Full recomputation, never delta: idempotent, self-healing after any crash, immune to
double-application" — `consolidation.py:5-8`).

**`PreserveShareSplit` reads प्रपत्र क's own previous output as its input — that is a fixed point, not
a drift.** With `total` unchanged, `round(total × old_filled / total) == old_filled` exactly, and
`new_vacant = total − new_filled` restores the other side, so a re-run reproduces the split
bit-for-bit. This matters because after Phase 0 the hook still fires on every level create, update and
delete; without the fixed-point property the split would creep by a unit per save. Phase 10 test 4
pins it.

---

## 5. SECURITY & OBSERVABILITY

### 5.1 Authorisation — propagation adds NO new authorisation surface

It is never a user-facing endpoint. It runs only inside a प्रपत्र ड or प्रपत्र ब mutation that has
**already** passed, in order:

1. `check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)` — `helpers.py:11`
2. `check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)` — `src/utils_timing.py`
3. `resolve_editable_row()` → `validate_access_control(row.district, level, unit, db)` +
   `_writable_taluka_value()` dispatch — `write.py:85-165`

The writable taluka value from (3) is the **only** input that decides which contribution space is
written. It comes from the auth cookie, never from the request body — the rule already stated at
`write.py:86-88`. Propagation must accept `t` as a parameter from the resolved row and must never take
a `taluka` from a form field.

Consequence: a taluka assistant's प्रपत्र ड edit writes **only that taluka's** प्रपत्र क/ब
contribution rows. A district or DCO assistant writes only `__district_office__`. Cross-district
writes are structurally impossible.

### 5.2 Input validation — exact bounds

| Input | Bound | Enforced where |
|---|---|---|
| `filled_posts` (प्रपत्र ब) | `0 ≤ filled_posts ≤ Σ sanctioned_posts_curr(pay_class)` | new check in `post_expenses/utils/validators.py`; 400 + Marathi message |
| the 8 allocatable measures (प्रपत्र क `Filled` row) | `0 ≤ Filled[m] ≤ C[class][m]`, the प्रपत्र ड-derived class total | new check beside `validate_post_status_inputs` in the existing `post_status/utils/validators.py`; 400 + Marathi message naming the measure and the ceiling |
| प्रपत्र क `status` on any write | must be `'Filled'` | `post_status` controllers; `409 CONFLICT` — `Vacant` is fully derived (§4.1 STEP E) |
| प्रपत्र क `posts` on any write | never accepted | absent from `PostStatusUpdate` and from the form; owned by STEP D |
| `sanctioned_posts_curr` (प्रपत्र ड) | `≥ level count` (existing, `budget_post_service.py:170-178`) and `≥ 0` (existing CHECK) | unchanged |
| `da_rate` | `0 ≤ rate ≤ 1`, already validated on write (`utils_da_rate.py:120-146`) | unchanged |
| derived money | every value written to प्रपत्र क is `≥ 0` because every source column is `≥ 0` by CHECK and `share_f ∈ [0,1]` | asserted in `service.py`; assertion failure = ERROR + raise |
| `share_f` | clamped to `[0.0, 1.0]` before use | `split_policy.py` |

No new Pydantic schema is exposed to the network — the internal DTOs are dataclasses.

### 5.3 Structured logging

Follow the key=value style of `src/core/taluka/` (`consolidation.py:183-189`, `write.py:97-110`) so the
same log greps keep working.

| Level | Event | Fields |
|---|---|---|
| `DEBUG` | every successful run | `form_derivation table=post_status district=… taluka=… fiscal_year=… category=… d_rows=N b_rows=4 c_rows=6 duration_ms=…` |
| `INFO` | value actually changed | `form_derivation_changed district=… taluka=… category=… class=… status=… field=… old=… new=…` — one line per changed field; the audit trail a district officer will demand when a number moves without them touching it |
| `WARNING` | `filled_posts` exceeds sanctioned | `form_derivation_clamp district=… taluka=… pay_class=… filled=… sanctioned=…` |
| `WARNING` | unknown designation | `form_derivation_unknown_designation designation='…' district=… → pay_class=2` |
| `ERROR` | twinless / missing consolidated row | `form_derivation_missing_consolidated table=… natural_key=…` then raise |

**Persistent audit.** Each changed प्रपत्र क / प्रपत्र ब row is also written to the existing audit log
via `AuditService.log_action(..., action='DERIVE', …)` — same call shape as
`post_status_service.py:173-182`. `action='DERIVE'` (not `'UPDATE'`) so a reviewer can tell machine
propagation from a human edit at a glance. Logged **before** `db.commit()`, because `log_action()` only
flushes; the comment at `post_expenses/controllers/ui_controller.py:369-371` records exactly this trap.
Skipped when `request is None` (the reconcile script's path); the structured log line is the record
there.

### 5.4 Metrics

Counters only, no new infrastructure — emit through the same logger:

- `form_derivation.runs` — tagged by `district`, `taluka_role ∈ {office, taluka}`
- `form_derivation.fields_changed` — the day-one signal for "is the client's data actually moving?"
- `form_derivation.clamps` — a rising count means districts are cutting sanctioned posts below their
  own filled counts: a data-quality conversation, not a bug
- `form_derivation.duration_ms` p95 — a regression means the STEP A scan lost its index

**Index check:** STEP A filters `(fiscal_year, district, category, taluka)` on
`budget_post_details_20530028`. The natural-key UNIQUE constraint
`uq_bpd_20530028_natural_key(fiscal_year, district, category, class_type, designation, taluka)`
(`models.py:28-29`) is a left-prefix match on `(fiscal_year, district, category)` and serves this
query. **No new index required.** Same for प्रपत्र ब/क. Confirm with `EXPLAIN` in Phase 10.

---

## 6. EXECUTION PHASES

Ground rules for every phase:
- 2–3 files. Independently verifiable — the suite is green after each.
- Three phases (7, 8 and 11) exceed three files. All are single behaviour switches that cannot be
  half-shipped — a read-only template in front of a still-writable endpoint is worse than either half
  — so they are kept whole and say so. No other phase exceeds three.
- Baseline before any work: **`python -m pytest tests/ -q` → `123 passed`** (measured 2026-08-25 on
  branch `Dev`). No phase may lower that count. After Phase 10 the baseline is **`209 passed`**
  (measured 2026-08-26, same branch); Phase 11 is held to that number.
- `python -c "import src.main"` must stay clean (model registry import side effect).
- **No phase changes an intra-sheet formula.** If an implementation step seems to require one, it is
  wrong — re-read the SCOPE BOUNDARY at the top.

---

### Phase 0: Stop `apply-aggregates` zeroing posts that have no levels
**Scope**: 1 file, ~10 LOC
**Verify**: open the प्रपत्र ड edit form for any seeded post (all have zero levels) — its eight pay
columns must be unchanged in the DB afterwards. Then add a level, delete it, and confirm the parent
does return to zero.

> Ships **first and alone**. It is a live data-destruction defect (§3.3) that exists today, and it is
> a hard prerequisite for Phase 6 — hooking propagation onto an endpoint that zeroes its own source
> would carry the zeros into प्रपत्र क and प्रपत्र ब too.

#### [MODIFY] `static/js/post_levels.js`
- What: `loadLevels()` gains a `persist` argument. `init()` (line 28) calls `loadLevels(false)`, which
  reads the existing `GET /{id}/aggregates` (`api_router.py:376`) to fill the display fields;
  `saveLevel()` (line 403) and `deleteLevel()` (line 423) call `loadLevels(true)`, which keeps the
  current `POST /{id}/apply-aggregates` (line 463). Split `syncMainForm()` accordingly — the
  field-assignment block (lines 470-482) is identical for both and stays shared.
- Pattern: `GET /{budget_post_id}/aggregates` already returns the same `AggregatedTotals` shape the
  POST returns under `result.aggregates`; no new endpoint, no server change, **no calculation change**.
- System design: **do not add a server-side `count == 0` guard.** "Never had levels" and "had levels,
  all now deleted" are the same server-side state, and the second must still zero the parent. The
  distinction only exists at the call site.

---

### Phase 1: Pay-class mapping and the two प्रपत्र ड value adapters
**Scope**: 3 files, ~190 LOC
**Verify**: `python -m pytest tests/test_s20530028_derivation_mapping.py -q`

#### [MODIFY] `src/schemes/s2053/subs/s20530028/config.py`
- What: add `DESIGNATION_PAY_CLASS` (§2.5), `PAY_CLASS_TO_STATUS_CLASS = {'1':CLASS_1_2_KEY,
  '2':CLASS_1_2_KEY, '3':CLASS_3_KEY, '4':CLASS_4_KEY}`, and two field tuples
  `DERIVED_POST_STATUS_FIELDS`, `DERIVED_POST_EXPENSES_FIELDS`.
- Pattern: place beside `POSITION_ORDER` (lines 118-131) and reuse the existing `CLASS_*_KEY`
  constants (lines 153-156) — do not re-spell the class strings.
- System design: pure module-level constants, no I/O. Every designation string copied verbatim from
  `DESIGNATIONS` (44-56) plus the three Temporary variants in `DESIGNATIONS_MR` (79-81). **Both
  spellings of every Class-1 & 2 post must be present** (§2.3c) — a missing Temporary variant is a
  silent misclassification, not an error.

#### [CREATE] `src/schemes/s2053/subs/s20530028/derivation/mapping.py`
- What: `pay_class_for(class_type, designation) -> str`; `status_class_for(pay_class) -> str`; the two
  value adapters `form_d_dearness_allowance(row, da_rate) -> int` and
  `form_d_house_rent_allowance(row) -> int`; and the frozen `MEASURE_MAP` of §2.4 as
  `(post_status_field, callable(ड_row) -> Decimal|int)` pairs.
- Pattern: stateless helpers in the style of
  `post_expenses/services/nps_component_service.py` — `@staticmethod`-only, no session.
- System design:
  - **The two adapters must reproduce प्रपत्र ड's own expressions exactly**, character for character
    where possible: `round((basic_pay + grade_pay) * da_rate)` and
    `round((basic_pay + grade_pay) * HRA_RATE_MAP[hra_rate])`, matching
    `budget_post_details_form.html:158-166` and `HRA_RATE_MAP` at `config.py:151`. **Do not change the
    rounding mode. Do not add a fallback rate the form does not have. Do not "fix" anything here.**
    These adapters are the seam that lets this feature follow a client-owned formula, not replace it —
    if प्रपत्र ड's calculation is ever changed, these two functions are the only place propagation
    needs to follow. Put that sentence in the module docstring.
  - **Zero DB access, zero imports from `models.py`.** Take a row-like object and read attributes.
    That is what makes the phase testable with `SimpleNamespace` and no database — the same trick
    `tests/test_taluka_phase14_15.py:36` already uses. `da_rate` is passed in, never fetched here.

#### [CREATE] `tests/test_s20530028_derivation_mapping.py`
- What: table-driven cases for all 22 `POSITION_ORDER` designations; **an assertion that every
  Permanent↔Temporary alias pair in `excel_export/populators/budget_post_details.py:71-87` maps to the
  same pay class** (the §2.3c trap, pinned); unknown designation → `'2'` + warning; `MEASURE_MAP`
  covers exactly the 8 money columns of `PostStatus20530028` (assert against
  `inspect(PostStatus).columns`, so a future column addition fails the test instead of being silently
  skipped); and **an adapter-fidelity test** — for a table of `(basic, grade, hra_rate)` inputs, the
  adapters return exactly what the प्रपत्र ड form template renders. This is the test that stops a
  future contributor from "improving" the arithmetic.
- Pattern: `pytest.mark.parametrize` as in `tests/test_taluka_phase14_15.py:59`.

---

### Phase 2: Cell aggregator (read-only)
**Scope**: 2 files, ~220 LOC
**Verify**: `python -m pytest tests/test_s20530028_derivation_aggregator.py -q`

#### [CREATE] `src/schemes/s2053/subs/s20530028/derivation/aggregator.py`
- What: `aggregate_pay_classes(db, *, taluka, district, fiscal_year, category, da_rate)
  -> dict[str, CellTotals]` implementing STEP A; `roll_up_to_status_classes(pay_class_totals)
  -> dict[str, CellTotals]` implementing STEP C. `CellTotals` is a frozen dataclass with the 8 measures
  + `sanctioned`.
- Pattern: query construction copies `active_taluka_sums()` (`consolidation.py:68-90`) — **one**
  `db.query(Model).execution_options(taluka_scope_all=True).filter(...)`.
- System design:
  - **`taluka_scope_all=True` is mandatory.** Without it the `do_orm_execute` listener
    (`orm_filter.py:40`) silently rewrites the query to `taluka == <caller scope>` and the office-space
    scan returns consolidated rows. This is the single most likely way to get this file wrong.
  - महागाई भत्ता and घर भाडे भत्ता accumulated **per row** through the Phase 1 adapters (§2.4
    rationale), never from the cell sum, and never recomputed inline.
  - `basic_pay` accumulated as `Decimal`, quantised once per cell; every other measure is already
    integral.
  - One query per `(taluka, district, fy, category)`; served by the natural-key UNIQUE left prefix
    (§5.4). No N+1.
  - No writes, no flush, no commit. This file is pure read.

#### [CREATE] `tests/test_s20530028_derivation_aggregator.py`
- What: in-memory SQLite fixture; assert against **real numbers from the seed** (which §2.7 D shows
  reproduces the workbook's प्रपत्र ड exactly, 0 / 2480 mismatches) — Mumbai City / Permanent:
  `Class-1 & 2 → posts 3, salary 4463, lsa 11, travel 130`; `Class-3 → posts 26, salary 8262,
  other 17`; `Class-4 → posts 32, salary 8953, other 96`. Pay-class split: Mumbai City / Temporary →
  `pc'1'.sanctioned == 4`, `pc'2'.sanctioned == 4`. Plus: an office-space scan must **not** see taluka
  rows, and vice versa.
- Pattern: SQLite session fixture from `tests/test_taluka_consolidation.py:71-95`.
- Note: महागाई भत्ता / घर भाडे भत्ता expectations are computed **from the Phase 1 adapters**, not
  hard-coded from the workbook — the aggregator's contract is "sum what प्रपत्र ड says", so the test
  must assert that, not a workbook figure the software may legitimately differ from.

---

### Phase 3: Filled/Vacant split policy
**Scope**: 2 files, ~150 LOC
**Verify**: `python -m pytest tests/test_s20530028_derivation_split.py -q`

#### [CREATE] `src/schemes/s2053/subs/s20530028/derivation/split_policy.py`
- What: `SplitPolicy` protocol with
  `filled_share(measure, old_filled, old_vacant, filled_posts, vacant_posts, salary_share) -> float`;
  `PreserveShareSplit` (default, D1); `PostRatioSplit` (the alternative);
  `SPLIT_POLICY = PreserveShareSplit()`.
- Pattern: no existing analogue — a deliberate new seam. Keep it a plain class with one method; no
  registry, no plugin loader.
- System design: fallback chain, in order —
  (1) `old_filled/(old_filled+old_vacant)` when that denominator > 0;
  (2) **`salary_share`** — the same cell's salary Filled fraction — when it is not `None`;
  (3) `filled_posts/(filled_posts+vacant_posts)` when that denominator > 0;
  (4) `1.0`.
  Result clamped to `[0,1]`. `new_vacant` is always `total − new_filled` (never independently rounded)
  so `Filled + Vacant == total` is an identity.
  **Tier 2 is evidence-driven**: §2.8 measured the post ratio reproducing the workbook's महागाई भत्ता
  split in 7/42 cells and its घर भाडे भत्ता split in 9/42, against 35/42 and 27/42 for the salary
  ratio — and those two measures are 92 % of all non-salary money here. `salary` itself is resolved
  first and passes `salary_share=None` for its own call.

#### [CREATE] `tests/test_s20530028_derivation_split.py`
- What: `Filled + Vacant == total` for every measure across a randomised sweep of totals and shares
  (the property that protects the taluka invariant); **each of the four fallback tiers fires in the
  right condition and no other**; a fresh all-zero cell with 0 posts lands 100 % on Filled;
  `PostRatioSplit` reproduces the post ratio exactly; the salary tier is skipped when
  `salary_share is None`.

---

### Phase 4: Propagation writer service
**Scope**: 2 files, ~280 LOC
**Verify**: `python -m pytest tests/test_s20530028_derivation_e2e.py -q -k writer`

#### [CREATE] `src/schemes/s2053/subs/s20530028/derivation/service.py`
- What: `derive_from_form_d(db, *, district, fiscal_year, category, taluka, request=None)
  -> DerivationResult` — STEPS B and D plus the `consolidate_row()` calls; and
  `derive_for_row(db, row, request)`, the thin adapter the controllers call.
- Adapter contract (§4.1): `derive_for_row` takes `district`, `fiscal_year` and `category` from `row`,
  and `taluka` from `_writable_taluka_value(db, row.district, get_auth_level(request),
  get_auth_unit(request))` — **not** from `row.taluka`, which is `''` when the caller is
  `create_row_family()`, and **not** from `get_fiscal_year_from_request()`, which can name a different
  year than the row.
- Pattern: the multi-row fan-out in `post_expenses/controllers/ui_controller.py:350-392` — resolve N
  rows, mutate, `db.flush()`, `consolidate_row()` per row, single commit **owned by the caller**.
- System design:
  - **Precondition assertion:** `assert not getattr(budget_post_row, TOTAL_SPACE_FLAG, False)` — §4.2.
    Raise `RuntimeError` with the offending table/id; do not silently continue.
  - **Lock-then-read (§4.3):** expose `acquire_derivation_locks(db, district, fiscal_year, category)`
    as a **public** function, because Phase 7's प्रपत्र ब controller must call it *before*
    `consolidate_row()`. `derive_from_form_d` calls it too (idempotent re-acquisition) so the
    प्रपत्र ड path needs no controller change.
  - **Never commits, never rolls back.** Same contract as `consolidate_row()`
    (`consolidation.py:6-8`). The controller owns the transaction.
  - Row lookup uses `taluka_scope_all=True` + `ensure_contribution_row()` (`write.py:232`) for a
    missing contribution; a missing **consolidated** row is an ERROR + raise (§4.5).
  - Writes **only** the columns §2.4 and §2.5 name. `filled_posts` and every प्रपत्र ब expense column
    are read-only to this service; assert that the write set is a subset of
    `DERIVED_POST_STATUS_FIELDS ∪ DERIVED_POST_EXPENSES_FIELDS` before flushing.
  - `AuditService.log_action(action='DERIVE', …)` per changed row, **before** commit (§5.3).
  - Returns `DerivationResult(rows_written, fields_changed, clamps)` so callers and the reconcile
    script can report without re-querying.

#### [CREATE] `src/schemes/s2053/subs/s20530028/derivation/__init__.py`
- What: re-export `derive_for_row` and `acquire_derivation_locks`; register with the core registry
  (Phase 5) at import time.
- Pattern: `src/core/taluka/__init__.py`.

---

### Phase 5: Core registry + the two प्रपत्र ड controllers
**Scope**: 3 files, ~90 LOC
**Verify**: `python -m pytest tests/ -q`; then `POST /ui/s20530028/budget-post-details/{id}/edit`
changing मंजूर पदे and confirm प्रपत्र ब `vacant_posts` and प्रपत्र क `posts` move, and
`check_taluka_invariant.py` stays clean

#### [CREATE] `src/core/derivation/registry.py`
- What: `register(model, fn)` / `run_for(db, model, row, request)`; a no-op when the model has no
  registration.
- Pattern: `src/core/registry.py` (the existing scheme registry) for the dict-of-model shape.
- System design: exists **only** so `src/core/secure_crud.py` — generic across all 40+ sub-schemes —
  can trigger 20530028's rules without importing them. No dynamic discovery, no entry points:
  registration happens at model-module import, which `src.main` already forces.

#### [MODIFY] `.../budget_post_details/controllers/api_controller.py`
- What: after the existing `consolidate_row(...)` (lines 322-328) and before `db.commit()` (line 329),
  call `derive_for_row(db, record, request)`.
- Pattern: the exact slot the file's own comment at lines 313-318 describes ("consolidation must run
  unconditionally or it silently never runs").
- System design: **do not widen the existing `except Exception` at line 372.** `HTTPException` is
  already caught first (line 355) and re-raised with its status — write-path rule 4. A 400 from a
  downstream `consolidate_row()` must reach the user as a 400 with its Marathi detail.

#### [MODIFY] `.../budget_post_details/controllers/ui_controller.py`
- What: same insertion after `consolidate_row(...)` (lines 462-469), before `db.commit()` (line 472).
- Pattern: identical to the API controller.
- System design: the existing `except HTTPException` at line 481 re-renders the form with `e.detail`
  for 400s — a propagation 400 therefore already surfaces correctly in the UI with no extra work.

---

### Phase 6: The remaining प्रपत्र ड write paths
**Scope**: 2 files, ~60 LOC
**Verify**: `python -m pytest tests/test_taluka_http.py -q` (it already exercises `apply-aggregates` at
line 454)

#### [MODIFY] `src/schemes/common/post_levels/api_router.py`
- What: in `apply_aggregates` (lines 414-495), after `consolidate_row(...)` (471-481) and before
  `db.commit()` (481), call `core.derivation.registry.run_for(db, budget_post_model,
  writable_budget_post, request)`.
- Pattern: the registry indirection keeps this shared module free of any 20530028 import — the other
  sub-schemes mounting `create_post_levels_router` are unaffected because they register nothing.
- System design: **the highest-traffic hook.** After Phase 0 it still fires after every level create,
  update and delete (`post_levels.js:403, 423`). Safe because propagation is a full recomputation
  (§4.6) — a no-change run writes identical values and logs nothing at INFO. Watch
  `form_derivation.duration_ms` p95 here first.

#### [MODIFY] `src/core/secure_crud.py`
- What: registry call after `consolidate_row(...)` in `update_item` (line 169, **before** the
  `db.refresh(db_item)` on line 170), after `create_row_family(...)` in `create_item` (line 141), and
  after `delete_row_family(...)` in `delete_item` (line 187).
- Pattern: same three-line shape at all three sites.
- System design: covers `PUT|POST|DELETE /api/schemes/2053/budget-post-details/*`, real endpoints
  (`router_api.py:20-24`) with no UI in front of them. Skipping them would let a scripted import leave
  the three forms silently out of sync — the exact failure mode this feature exists to remove. Four
  site-specific facts, each verified in the source:
  - **create**: `create_row_family()` returns the **consolidated** row (`write.py:286`), so the
    adapter's cookie-derived `taluka` (Phase 4) is what makes this site correct. Deriving only the
    caller's own space is sufficient: the new designation exists only in the office contribution —
    `create_row_family` writes one contribution row and does not call `ensure_contribution_rows`, so
    every taluka's aggregate is unchanged.
  - **delete**: `delete_row_family()` removes the row for **every** taluka of that natural key
    (`write.py:291-326`). Deriving only the caller's space would leave each taluka's प्रपत्र क/ब
    holding posts and pay for a designation that no longer exists, and the consolidated rows would
    inherit that. This site must derive for `[DISTRICT_OFFICE] + _active_taluka_values(db, district)`
    — the same list `consolidate_row()` itself builds (`consolidation.py:145`). The one site where the
    caller's space is not the full blast radius.
  - **delete ordering and identity**: there is no `consolidate_row()` to run after, because the family
    is gone; the hook runs directly after `delete_row_family()` and before `db.commit()`. **Capture
    `district`, `fiscal_year` and `category` from `db_item` before the delete** — the instance is
    expired afterwards (§4.5).
  - **update**: `update_data` already has every natural-key column popped (line 160), so `category` /
    `class_type` / `designation` cannot change under a PUT. One propagation call covers it.

---

### Phase 7: प्रपत्र ब — `vacant_posts` becomes derived, and प्रपत्र ब becomes the second trigger
**Scope**: 4 files (one atomic switch — see §6 ground rules), ~150 LOC
**Verify**: `python -m pytest tests/ -q`; edit प्रपत्र ब's भरलेली पदे and confirm प्रपत्र क's
`Filled`/`Vacant` posts move in the same request; `filled_posts` > sanctioned → 400 with a Marathi
message, not a 500; two concurrent saves of **different classes in the same district** both succeed
(the §4.3 deadlock regression)

#### [MODIFY] `.../post_expenses/utils/validators.py`
- What: `validate_filled_against_sanctioned(db, record, filled_posts) -> (bool, str|None)`.
- Pattern: `budget_post_service.py:170-178`, which already blocks
  `sanctioned_posts_curr < level_count` with a Marathi message — same shape, opposite direction.
- System design: **this check runs in *total* space, not contribution space.** At the point of
  validation `record` is the row `resolve_editable_row()` returned, which for a district or DCO caller
  is lifted (`write.py:197-208`) — `filled_posts` as the user typed it is a *district total*. It must
  therefore be compared against the **consolidated** (`taluka=''`) प्रपत्र ड sanctioned sum for that
  pay class, not against the office-space scan the aggregator uses. Comparing against the office scan
  would reject legitimate input from any district whose posts live in its talukas. Same
  total-vs-share distinction as §4.2, one layer up, and the single easiest thing to get wrong here.

#### [MODIFY] `.../post_expenses/services/post_expenses_service.py`
- What: in `update_inline` and `update_form`, stop accepting `vacant_posts` from the caller and stop
  writing it; call the new validator. **Leave the district-wide fan-out sync (lines 214-243) untouched**
  — those are the user-owned expense fields of §2.6, which this feature does not connect.
- Pattern: existing method structure, minimal delta.
- System design: **the service must not compute `vacant_posts` either.** It would have to write
  `sanctioned − filled` into a row that is still in total space, which `consolidate_row()` would then
  rebase a second time. `vacant_posts` is owned solely by the propagation, which runs after the rebase
  and therefore in contribution space (STEP B). `vacant_posts` remains a real stored column — the Excel
  populator and `ui_category_info.py:37` read it — only its *authorship* changes.

#### [MODIFY] `.../post_expenses/controllers/ui_controller.py` + `.../api_controller.py`
- What: three changes in each, in this order:
  1. **Immediately after `resolve_editable_row()`**, call
     `acquire_derivation_locks(db, district, fiscal_year, category)` (Phase 4).
  2. Add `ORDER BY category, class_type` to the fan-out query (`ui_controller.py:358-362`) so the
     `consolidate_row()` loop at 380-390 runs in a deterministic order.
  3. After that loop and before `db.commit()`, call the propagation once.
- Pattern: step 3 is identical to Phase 5's insertion in the प्रपत्र ड controllers.
- System design: **step 1 is the deadlock fix and is not optional** (§4.3). Step 2 fixes the same root
  cause in the pre-existing fan-out. The propagation runs **once**, for the edited row's
  `(district, category)`, because the fan-out only touches money columns and cannot change any post
  count.

---

### Phase 8: only the *derived* fields become read-only — प्रपत्र क and प्रपत्र ब
**Scope**: 6 files (one atomic switch — see §6 ground rules), ~230 LOC
**Verify**: `python -m pytest tests/ -q`; `रिक्त पदे` and प्रपत्र क `posts` reject direct writes;
a प्रपत्र क `Filled` allocation edit succeeds and leaves `Filled + Vacant` equal to the प्रपत्र ड
total; a write to a प्रपत्र क `Vacant` row returns `409`; every प्रपत्र ब expense field still saves

> **Rewritten by AMENDMENT 1.** The original Phase 8 locked प्रपत्र क wholesale. It now implements the
> AMENDMENT 1 table exactly: **read-only iff derived.** A deployment that already shipped the original
> Phase 8 applies **Phase 11** instead of re-running this one.

#### [CREATE] `.../s20530028/derivation/allocation.py`
- What: STEP E (§4.1). `class_totals_for(db, row, *, taluka) -> CellTotals` — the प्रपत्र ड-derived
  class total of `row`'s class in a named space; `rebalance_status_split(db, status_row, request)
  -> int` (fields changed on the `Vacant` sibling). The user-facing bound check lives in
  `post_status/utils/validators.py` and imports `class_totals_for` from here — the same split
  `post_expenses/utils/validators.py` already uses when it imports `derivation.mapping.pay_class_for`.
- Pattern: `derivation/service.py`'s `_record_changes` / `_natural_key` / `ensure_contribution_row` /
  `consolidate_row` sequence, reused verbatim. **Never commits, never rolls back** — same contract as
  `consolidate_row()` (`consolidation.py:6-8`).
- System design:
  - **Reads, never recomputes.** Totals come from `aggregate_pay_classes` + `roll_up_to_status_classes`
    (Phase 2), i.e. from प्रपत्र ड's own values through the Phase 1 adapters. This file introduces no
    arithmetic of its own beyond `total − filled` (SCOPE BOUNDARY).
  - **Two spaces, deliberately** (§4.1 STEP E): `validate_allocation` runs on the row as
    `resolve_editable_row()` returned it — total space for a district/DCO caller, so it scans
    `taluka == DISTRICT_LEVEL`, exactly like `validate_filled_against_sanctioned`
    (`post_expenses/utils/validators.py`). `rebalance_status_split` runs *after* `consolidate_row()`
    and therefore in contribution space, scanning `taluka == status_row.taluka`. Assert
    `not getattr(status_row, TOTAL_SPACE_FLAG, False)` at the top of the rebalance and raise loudly —
    the §4.2 trap, one form further along.
  - **`status != 'Filled'` ⇒ raise `HTTPException(409)`.** `Vacant` is fully derived.
  - **Write set assertion:** subset of `ALLOCATABLE_POST_STATUS_FIELDS`. `posts` must never appear.
  - `AuditService.log_action(action='DERIVE', …)` for the `Vacant` row, before commit (§5.3).

#### [MODIFY] `.../s20530028/config.py`
- What: `ALLOCATABLE_POST_STATUS_FIELDS` — `DERIVED_POST_STATUS_FIELDS` minus `posts`, i.e. the eight
  money measures the user may allocate. Two tuples, two meanings: `DERIVED_*` is what propagation
  writes; `ALLOCATABLE_*` is what a user may hand-allocate inside a derived total.
- Pattern: beside the tuples Phase 1 added.

#### [MODIFY] `.../post_status/controllers/api_controller.py` + `ui_controller.py`
- What: keep the update endpoints, narrowed. Order inside the handler is fixed:
  1. `resolve_editable_row()`
  2. `acquire_derivation_locks(db, district, fiscal_year, category)` — **the deadlock fix, not
     optional** (§4.3)
  3. `409` if `status != 'Filled'`; ignore any submitted `posts`
  4. `validate_allocation()` → `400` + Marathi detail on failure
  5. write the eight measures → `db.flush()` → `consolidate_row()` on the edited row
  6. `rebalance_status_split()` → `db.commit()`
- System design: 409, not 403, for the `Vacant`/`posts` rejections. The caller is authorised; the
  *resource state* forbids the edit. Distinguishable in logs from a genuine permission failure.
  Do not widen the existing `except HTTPException` — a 400 must reach the user with its Marathi
  detail (write-path rule 4).

#### [MODIFY] `src/schemes/s2053/subs/s20530028/schemas.py`
- What: `PostStatusUpdate` carries **the eight allocatable measures and nothing else** (no `posts`, no
  natural-key columns); `PostExpensesUpdate` carries every user-owned प्रपत्र ब field and drops only
  `vacant_posts`.
- **Implementation constraint — the current class hierarchy will not allow the obvious edit.**
  `PostStatusUpdate(PostStatusBase)` and `PostStatusResponse(PostStatusBase)` share one base
  (`schemas.py:41-68`). Removing fields from `PostStatusBase` would strip them from the **response**
  too and break every read. `PostStatusUpdate` must therefore stop inheriting `PostStatusBase` and
  become its own narrow model. Same for `PostExpensesUpdate`.
- Pattern: these two classes are passed as `update_schema` into `create_secure_crud_routes`
  (`router_api.py:26-36`), and `update_item` builds its write set from
  `data.model_dump(exclude_unset=True)` (`secure_crud.py:159`) — so a field absent from the schema is
  unwritable, with no change to the generic factory.
- System design: `PostStatusUpdate` remains an empty model and **`PUT /api/schemes/2053/post-status/{id}`
  stays suppressed** via `methods={"GET","POST","DELETE"}` on `create_secure_crud_routes`.

> **Why the allocation is NOT wired through the derivation registry — verified, not assumed.**
> The obvious move is `register(PostStatus, rebalance_status_split)`, letting the generic `PUT`
> maintain I1 through the hook `update_item` already calls. It does not work, because the registry's
> contract is *"recompute this cell"*, keyed on `(district, fiscal_year, category)`, while STEP E is
> *"fix this row's twin"*, keyed on a specific `(class_type, status)` row in a specific space. The two
> other call sites prove the mismatch:
> - `create_item` calls `run_for(db, model, db_item, request)` where `db_item` is the **consolidated**
>   row `create_row_family()` returns (`write.py:286`) — `taluka == ''`, a row STEP E must never write.
> - `delete_item` calls `run_for` with a `SimpleNamespace(district, fiscal_year, category)` and an
>   explicit `taluka=` — an object with **no `class_type` and no `status`**, so STEP E would
>   `AttributeError` into a 500 on every `DELETE`.
>
> Making the hook tolerate both shapes would mean two silent no-op branches inside a function whose
> whole job is to guarantee an invariant. **STEP E is therefore called explicitly from the two
> प्रपत्र क write handlers**, which is the same place Phase 5 calls `derive_for_row` from the
> प्रपत्र ड handlers. `PUT` stays suppressed because a generic writer that cannot maintain I1 is worse
> than no route — the original Phase 8's reasoning, still correct, for a different reason.

#### [MODIFY] `templates/.../post_status_form.html`, `post_status_list.html`, `post_expenses_form.html`, `post_expenses_list.html`
- What, per the AMENDMENT 1 table:
  - प्रपत्र क form — `Posts` `readonly`; the eight money inputs `readonly` **only when
    `item.status != 'Filled'`**; the `अपडेट रेकॉर्ड` button rendered **only** on a `Filled` row;
    सूचना line explaining that the class total comes from प्रपत्र ड and रिक्त is computed from भरलेली.
  - प्रपत्र क list — the द्रुत संपादन block **stays**, with `Posts` `readonly` and the eight inputs
    disabled while the selected `स्थिती` is not `भरलेली`.
  - प्रपत्र ब form + list — `रिक्त पदे` `readonly`; **भरलेली पदे and every expense field stay
    editable** (§2.6 — they are not connected to प्रपत्र ड at all and must never be locked).
- Pattern: `budget_post_details_form.html:117-155` for the `readonly` +
  `background:var(--muted)` treatment.
- **भरलेली पदे stays editable.** It is the user's only Filled/Vacant post input (§2.8 C2). Locking it
  would make the split unmaintainable.

> **Reversibility.** The only phase that removes a capability from users, and after AMENDMENT 1 it
> removes the minimum possible: nine cells per class (`posts` ×2, the eight `Vacant` measures) rather
> than a whole form. It is last among the behaviour changes on purpose.

---

### Phase 9: Reconciliation tool
**Scope**: 1 file, ~200 LOC
**Verify**: `python scripts/reconcile_form_derivation.py --dry-run --district "Mumbai City"` reports a
per-cell diff; `--fix` then re-run reports zero; `python scripts/check_taluka_invariant.py` clean

#### [CREATE] `scripts/reconcile_form_derivation.py`
- What: `--dry-run` (default) / `--fix` / `--district` / `--fiscal-year`; iterates every
  `(taluka, district, fiscal_year, category)` with at least one प्रपत्र ड contribution row and calls
  `derive_from_form_d`, printing a per-field before/after table.
- Pattern: `scripts/check_taluka_invariant.py` end to end — the `RUN_DB_CREATE_ALL=false` guard
  (line 40), the `import src.main` side-effect comment (line 44), argparse shape, `--fix` semantics, and
  the "idempotent, always safe to re-run" contract.
- System design:
  - **`--dry-run` is the default and is the client sign-off artefact.** Its output answers "what will
    change when we turn this on?" See §8 step 4 for the deltas to expect and how to present them.
  - Recovery path for the three events no request hook can see: a **DA-rate change**
    (`utils_da_rate.py:80` — every derived महागाई भत्ता goes stale at once), an edit to
    `DESIGNATION_PAY_CLASS` (D2), and any direct SQL or bulk import. **Document in the module docstring
    that the DA-rate admin endpoint should invoke it.**
  - Taluka activation, taluka deactivation and fiscal-year creation need **no** reconcile and must not
    be given hooks. Verified, not assumed: activation clones contribution rows with every numeric
    zeroed (`provisioning.py:28-46`); deactivation calls `consolidate_district` for every scoped model
    (`utils_taluka_user_management.py:168-180`), which drops the ड and क/ब contributions of the same
    taluka together; and `clone_table_for_fiscal_year` zeroes every numeric column of every cloned row
    (`fiscal_year.py:132-136`), so a new fiscal year starts with all four forms at zero. All three leave
    the forms consistent by construction.
  - Acquires locks in the §4.3 global order, same as the request path.
  - Commits per district, not per cell — bounded transactions on a run that may touch every row in the
    sub-scheme.

---

### Phase 10: End-to-end tests, index verification, documentation
**Scope**: 2 files, ~360 LOC
**Verify**: `python -m pytest tests/ -q` → **≥ 145 passed**

#### [CREATE] `tests/test_s20530028_derivation_e2e.py`
- What, at minimum:
  1. **No-taluka district (Mumbai City):** edit प्रपत्र ड → प्रपत्र ब `vacant_posts` and प्रपत्र क
     `posts` / `salary` land on the seed-verified values of §2.7.
  2. **District with talukas (Thane + 2, via `conftest.activate_talukas`):** office edit and taluka edit
     each land in their own space; the consolidated प्रपत्र क row equals the sum. **Runs
     `check_taluka_invariant`'s value check inline.**
  3. **Mixed `hra_rate` across contributions:** a taluka on `Z` and the office on `X` — consolidated
     प्रपत्र क `house_rent_allowance` must equal the sum of the two correctly-rated contributions.
     This is the test that proves no stored column is needed (§2.4) and that a future refactor cannot
     reintroduce one by accident.
  4. **Total-space guard:** calling propagation on a row still carrying `TOTAL_SPACE_FLAG` raises — the
     §4.2 trap, pinned so a future refactor cannot silently reintroduce it.
  5. **Idempotency:** two consecutive runs, identical values, zero INFO change lines.
  6. **`Filled + Vacant == total`** for all 8 measures after a प्रपत्र ड change, under both split
     policies.
  7. **`PreserveShareSplit` fidelity:** unchanged प्रपत्र ड ⇒ byte-identical प्रपत्र क.
  8. **Salary-share fallback:** a cell whose measure is all-zero but whose salary is not must take the
     salary share, not the post share (§2.9 D1).
  9. **Nothing outside the write set moves:** after a प्रपत्र ड save, प्रपत्र ब's `filled_posts`,
     `medical_expenses`, `festival_advance`, `swagram_maharashtra_darshan`, the NPS trio and `other` are
     **byte-identical**, and प्रपत्र ड's own columns are untouched. This is §2.6 pinned as a test —
     the guard against scope creep in every future change to this code.
  10. **400 passthrough:** a `consolidate_row()` 400 reaches the caller as 400 with its Marathi detail
      (write-path rule 4).
  11. **Cache staleness bound:** प्रपत्र क गोषवारा may lag ≤ 180 s (§4.4) — pinned so it is never
      mistaken for a propagation bug.
  12. **Delete blast radius:** `DELETE /api/schemes/2053/budget-post-details/{id}` on a district with
      two active talukas clears that designation from **every** taluka's प्रपत्र क/ब, not only the
      caller's (Phase 6). Pinned because deriving only the caller's space passes every single-district
      test and silently corrupts taluka districts.
  13. **प्रपत्र ब as a trigger:** editing only `filled_posts` moves प्रपत्र क's `Filled`/`Vacant` posts
      in the same request, with प्रपत्र ड untouched (LINK 3).
  14. **Lock ordering:** two interleaved प्रपत्र ब saves for different `class_type` in one district both
      commit. The §4.3 deadlock, pinned.

  Added by AMENDMENT 1 (delivered by Phase 8, or by Phase 11 on an already-shipped deployment):

  15. **Invariant I1 after an allocation edit:** writing `Filled[m]` on a प्रपत्र क row leaves
      `Filled[m] + Vacant[m]` **exactly** equal to the प्रपत्र ड class total, for all 8 measures.
  16. **The allocation survives propagation:** allocate, then save प्रपत्र ड **without changing any
      value** — the allocation is byte-identical afterwards (the `PreserveShareSplit` fixed point,
      §4.6, now load-bearing). Then change a प्रपत्र ड value and assert the allocation *fraction* is
      preserved while the totals move.
  17. **`Vacant` and `posts` stay locked:** `POST …/post-status/{id}/edit` on a `Vacant` row → `409`;
      a submitted `Posts` on a `Filled` row is ignored, not written.
  18. **Over-allocation is rejected, not clamped:** `Filled[m] > total[m]` → `400` with a Marathi
      detail; the stored row is unchanged. Separately, STEP E's `max(0, …)` floor fires without
      raising when the office share is the one out of range (§4.1 STEP E).
  19. **प्रपत्र ब's unconnected fields are untouched by all of this:** `medical_expenses`,
      `festival_advance`, `swagram_maharashtra_darshan`, the NPS trio and `other` still save through
      both the UI and the API after Phase 8/11. §2.6 pinned from the other direction.
- Pattern: `tests/test_taluka_integration.py` — real models, real `src.core.taluka`, SQLite, `conftest`
  fixtures.
- Note: SQLite ignores `FOR UPDATE`, so test 14 pins the *acquisition order* (assert the sequence of
  locked natural keys), not the DB's blocking behaviour. Say so in the test docstring.

#### [MODIFY] `docs/ARCHITECTURE.md`
- What: a "Cross-sheet propagation (20530028)" section next to "Taluka Data Consolidation"; a
  `Derived Forms` row in the Key Architectural Patterns table; extend **Write-path rules** with:
  - **rule 5** — *"a mutation of a propagation-source model must call the registry hook after
    `consolidate_row()` and before `commit()`; ordering is a correctness requirement (see §4.2 of
    `docs/plan-form-d-propagation.md`)."*
  - **rule 6** — *"a handler that will consolidate more than one row of a propagation-target table must
    acquire the derivation lock set, in the documented global order, before the first
    `consolidate_row()` (see §4.3)."*
- Also record the scope rule: **propagation consumes प्रपत्र ड's values as प्रपत्र ड produces them;
  `derivation/mapping.py`'s two adapters are the only place that follows an intra-sheet formula, and
  changing their arithmetic is a review-blocking defect.**

#### [VERIFY, no file] Index confirmation
- `EXPLAIN (ANALYZE, BUFFERS)` the STEP A query against production-sized data; confirm it uses the
  `uq_bpd_20530028_natural_key` left prefix (§5.4). Add an index only if it does not — do **not** add
  one speculatively.

---

### Phase 11: AMENDMENT 1 delta — unlock everything propagation does not write
**Scope**: 7 files, ~300 LOC
**Verify**: `python -m pytest tests/ -q` → **≥ 215 passed** (baseline after Phase 10 was
**209 passed**, measured 2026-08-26 on branch `Dev`);
`POST /ui/s20530028/post-status/{id}/edit` on a `Filled` row saves and `Filled + Vacant` still equals
the प्रपत्र ड class total; the same POST on a `Vacant` row returns `409`; प्रपत्र ब's expense fields
still save unchanged

> Apply this phase **only** to a deployment that already shipped the original (pre-amendment) Phase 8.
> A fresh implementation gets the same end state from the rewritten Phase 8 above and must skip this.

#### [CREATE] `.../s20530028/derivation/allocation.py` + [MODIFY] `.../s20530028/config.py` + `.../post_status/utils/validators.py`
- What: exactly as specified in the rewritten Phase 8. `config.py` also gains
  `POST_STATUS_FIELD_LABELS_MR` — the field → Marathi label map the 400 message needs.
  `METRICS_LABELS` cannot serve: it holds **11** display labels against **9** DB keys because it
  includes प्रपत्र क's two display-only `Total` rows (§2.1), so indexing it by measure is off by one
  from `एकूण वेतन` onward.

#### [MODIFY] `.../post_status/controllers/ui_controller.py` + `api_controller.py`
- What: restore the two update handlers the original Phase 8 replaced with `409` stubs, in the
  narrowed 6-step form of the rewritten Phase 8. Recover the pre-Phase-8 handler bodies from
  `git show HEAD:…` rather than re-deriving them — the `Form(...)` signature, the
  `check_data_filling_allowed` guard, the `strip_protected_update_fields` call and both error
  re-render blocks are all still correct and must come back byte-for-byte where they are not narrowed.
- **Also restore the `check_data_filling_allowed` guard on the GET edit form**, which the original
  Phase 8 removed as dead code once the form was read-only. With the form writable again it is live
  authorisation, not decoration.
- System design: the fan-out precedent is **not** applicable here — a प्रपत्र क allocation edit
  touches exactly two rows (`Filled` and its `Vacant` twin) in one `(district, category, class)`.

#### [UNCHANGED] `.../s20530028/schemas.py`, `router_api.py`, `src/core/secure_crud.py`, `derivation/__init__.py`
- Verified no edit is required. `PostStatusUpdate` stays empty and the API `PUT` stays suppressed, for
  the registry reason boxed in Phase 8. Listing them here so a reader does not "fix" them.

#### [MODIFY] `templates/.../post_status_form.html` + `post_status_list.html`
- What: restore the `अपडेट रेकॉर्ड` button (on `Filled` rows only) and the द्रुत संपादन block the
  original Phase 8 deleted; leave `Posts` and the `Vacant` side `readonly`. Recover the द्रुत संपादन
  markup with `git show HEAD:templates/…/post_status_list.html`, then apply the two narrowings.
- **Do not touch `post_expenses_form.html` / `post_expenses_list.html`.** Verified: the only field the
  original Phase 8 locked in प्रपत्र ब is `रिक्त पदे`, which **is** derived. Every unconnected
  प्रपत्र ब expense field was already left editable and is correct as shipped.

#### [MODIFY] `tests/test_s20530028_derivation_e2e.py`
- What: add tests 15–19 of Phase 10 below.

---

## 7. WHAT THIS DESIGN DELIBERATELY DOES NOT DO

| Not done | Why | What it would cost later |
|---|---|---|
| Change any intra-sheet formula — प्रपत्र ड's महागाई भत्ता / घर भाडे भत्ता expressions, the गोषवारा's totals, the level aggregator's arithmetic, the Excel export's own calculations | Client-owned and set to the client's requirement. This feature's contract is to *consume* प्रपत्र ड's values, not to audit them (SCOPE BOUNDARY) | Nothing. If the client later changes प्रपत्र ड's calculation, the two adapters in `derivation/mapping.py` are the only place propagation follows |
| Add a stored `house_rent_allowance` (or `dearness_allowance`) column to प्रपत्र ड | Unnecessary: the scan runs per contribution space and reads each row's own `hra_rate`, so प्रपत्र ड's existing per-row expression is both available and correct under consolidation (§2.4). A column would also freeze a value the client's formula owns | One column + one write-back line, if a future requirement ever needs per-row overrides |
| Connect प्रपत्र ब's expense table (medical, festival, swagram, NPS trio, other) | No dimension in common with प्रपत्र ड — district-level only (§2.6). Its existing fan-out sync already does what it needs | n/a |
| Connect प्रपत्र ड's `sanctioned_posts_prev1` | प्रपत्र क and ब have no prior-year dimension | n/a |
| Derive `filled_posts` | It is the user's only Filled/Vacant input; deriving it would destroy the split (§2.8 C2) | n/a |
| Lock any field propagation does not write — प्रपत्र ब's expense table, प्रपत्र ब's `filled_posts`, प्रपत्र क's Filled/Vacant allocation | AMENDMENT 1. Read-only is a statement that the software owns a number. Applying it to a number the software cannot compute deletes the only input the system has for it | n/a — the AMENDMENT 1 table is the complete lock list, and adding to it requires showing that propagation writes the field |
| Make प्रपत्र क's `Vacant` side editable as well as `Filled` | `Filled[m]` alone parameterises the split; a second editable side adds no expressive power and creates a two-way race | n/a |
| Per-level Filled/Vacant occupancy (`post_level_details.occupancy_status`) — the model that would make the split **exactly** derivable instead of policy-based | Requires every district to re-enter level data for every post; the levels table is optional today and mostly empty | Additive: one nullable column, one new `SplitPolicy` implementation, zero changes to the aggregator, writer, hooks or controllers. **The Phase 3 seam exists precisely to make this cheap** |
| Generalise propagation to sub-schemes 20530019 / 20530153 / … | Their designation sets and class vocabularies are not verified to match; speculative generality is how the class-vocabulary trap (§2.2) gets baked into a shared base class | The registry (Phase 5) is already generic; only a new `mapping.py` + `config` dict per sub-scheme |
| Make प्रपत्र क / ब SQL views instead of tables | Both carry user-owned columns (`filled_posts`, medical/festival/NPS); Excel populators, the chatbot views and `consolidate_row()` all assume tables | Would be a rewrite of the taluka layer for these tables |
| Fix `CacheService` substring-vs-hash invalidation (§4.4) | Touches every scheme's cache behaviour; unrelated blast radius | Separate ticket; the 180 s bound is pinned by a test so the regression is visible |
| Propagate to प्रपत्र अ (`unit_expenditure`) | No column relationship exists — its natural key has no `category` / `class_type` / `designation` dimension at all | n/a |

### 7.1 Two observations for the client — data questions, not software changes

Neither is a defect in the propagation design and neither blocks any phase. Both are raised because
turning propagation on makes them **visible** in प्रपत्र क, and the client should decide before
cutover rather than after.

**(a) `hra_rate` is `'X'` (30 %) on every row, and the form cannot change it.** The seed `INSERT` omits
the column, so all 248 rows carry the `server_default`; on the edit form `HraRate` is a **hidden input**
(`budget_post_details_form.html:168`), so `validate_hra_rate()` (`budget_post_service.py:206`) guards an
input no user can reach. It is settable per level in the levels UI (`post_levels.js:380`) and nowhere
else.

Consequence when propagation is enabled: प्रपत्र क's `house_rent_allowance` becomes
`Σ` प्रपत्र ड's 30 % figure. The seeded प्रपत्र क values imply a different band for four districts:

| District | Current क घर भाडे भत्ता | Σ प्रपत्र ड at 30 % | Change on cutover |
|---|---|---|---|
| Mumbai City | 13,060 | 13,790 | +6 % |
| Mumbai Suburban | 37,659 | 37,659 | none |
| Thane | 41,100 | 43,193 | +5 % |
| Palghar | 19,784 | 60,554 | **×3.06** |
| Raigad | 21,304 | 53,351 | **×2.50** |
| Ratnagiri | 18,040 | 55,406 | **×3.07** |
| Sindhudurg | 11,623 | 34,864 | **×3.00** |

**Client decision:** either accept प्रपत्र ड's current figure as authoritative (propagation makes क
agree with ड, which is the point of the feature), or set the correct `hra_rate` per row before cutover
— which needs the hidden input replaced by a visible select, a small UI change entirely inside the
existing intra-sheet mechanism. **Recommend raising it before §8 step 5**, because it is far cheaper to
decide once than to explain four districts' HRA jumping 3×.

**(b) The seed lost one `special_pay` value.** Mumbai Suburban / Permanent / Class-1 & 2 / Filled:
प्रपत्र ड (and the workbook) say 10, the seeded प्रपत्र क says 0. Propagation restores 10. Correct, but
put it in the sign-off pack so it is not read as a propagation bug.

---

## 8. ROLLOUT ORDER (operational, not code)

1. **Phase 0 ships first and alone, ahead of any sign-off.** It stops live data loss (§3.3) and is a
   hard prerequisite for Phase 6. Nothing else in this document depends on the client's decisions.
2. Phases 1-4 ship dark — new files, no behaviour change. Suite green at each step.
3. Raise §7.1(a) with the client. It needs no code and it is the only cutover surprise in the feature.
4. `scripts/reconcile_form_derivation.py --dry-run` on a **production snapshot**. Circulate the
   per-district diff. Expected non-zero deltas, all of which belong in the sign-off pack:
   - `house_rent_allowance` — per §7.1(a), large for Palghar / Raigad / Ratnagiri / Sindhudurg unless
     the rates are corrected first.
   - `dearness_allowance` — ±1 to ±2 on roughly ten cells, from per-row vs per-class rounding (§2.4).
   - `special_pay` +10 on one Mumbai Suburban cell — per §7.1(b).
   - `vacant_posts` — wherever a district's `filled_posts` no longer matches current sanctioned totals.
5. Client signs off D1, D2, D3 (§2.9).
6. Phases 5-6 enable propagation from प्रपत्र ड. Watch `form_derivation.fields_changed` and
   `form_derivation.duration_ms` for one data-filling cycle.
7. Phase 7 (includes the deadlock fix — **do not ship the प्रपत्र ब trigger without it**), then Phase 8
   (the only user-visible capability removal) last.
8. `--fix` in production, inside the existing maintenance window, then
   `python scripts/check_taluka_invariant.py` as the exit gate.
9. **AMENDMENT 1 only:** if the original Phase 8 is already in production, Phase 11 ships next. It is
   purely additive from a user's point of view — it returns capability, never removes it — so it needs
   no sign-off and no reconcile run. `check_taluka_invariant.py` stays the exit gate, joined by a
   `reconcile --dry-run` that must report **zero** प्रपत्र क deltas: a non-zero delta means an
   allocation edit broke I1, which is the one regression this phase can introduce.
