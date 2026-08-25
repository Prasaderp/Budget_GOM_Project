# TDD — अपडेट रेकॉर्ड must return to the same संपादन form, not the list

**Role:** Principal Systems Architect
**Status:** Design. Zero implementation code below.
**Scope:** every UI edit form in the product — all schemes, all sub-schemes.
**Sibling document:** `docs/plan-form-d-propagation.md`. It is **not** superseded, and §0.2 below
records the one hard ordering dependency between the two.

---

## SCOPE BOUNDARY — read this before anything else

This feature changes **one thing**: where the browser lands after a successful
`POST /{id}/edit`. Today it lands on the list page ("main page"); it must land back on the same
edit form, showing the values that were just saved.

**In scope:**

```
POST /{id}/edit  succeeds  ──►  303  ──►  GET /{id}/edit  (same path)  + a success toast
```

**Explicitly OUT of scope — do not touch any of it:**

| Not touched | Why |
|---|---|
| The transaction: `resolve_editable_row` → mutate → `flush` → `consolidate_row` → derivation hook → `commit` | The redirect is chosen **after** `db.commit()` returns. Nothing about ownership, ordering or rollback changes. An implementation that moves a `commit`, a `consolidate_row` or a derivation hook to make the redirect work has misread this document |
| Validation, permissions, timing windows, audit logging | Unchanged at every one of the 73 sites |
| The **error** path | Every handler already re-renders its own form with `error=…` on a 400. That is already "stay on the form" and needs no change |
| Business logic, formulas, derived-field rules | Owned by `docs/plan-form-d-propagation.md` and by the client |
| The list pages, their filters, their `?view=edit` mode | Untouched |
| `POST /api/update-inline` (the द्रुत संपादन endpoints) | They are `fetch()` + `showNotification()` + `location.reload()` already — they never left the page, so they have no bug to fix |
| Create (`/new`) | **Verified: there is no create route anywhere in the product** — `grep -rn 'router.post("/new"' src` returns 0 across all schemes. Rows are seeded and cloned per fiscal year (`fiscal_year.py:clone_table_for_fiscal_year`). The `{{ '…/new' if not item }}` branch in the 75 form templates points at a route that does not exist; that latent 405 is pre-existing and out of scope |

The single rule that keeps this feature safe at 73 call sites:

> **The only thing that changes is the `url=` argument of a `RedirectResponse` that is already
> being constructed, on a line that is already only reached after a successful `commit()`.**
> If a diff at any site touches anything above that line, it is wrong.

---

## 0. WHAT THIS DOCUMENT ASSUMES YOU KNOW

| Concept | Source | Why it matters here |
|---|---|---|
| Post/Redirect/Get | — | Already the pattern in use: every site returns `303 SEE_OTHER`. Only the destination is wrong |
| Write redirection + total-space lift | `src/core/taluka/write.py:124-208` | **`resolve_editable_row()` can return a row whose `id` is not the `id` in the URL.** §0.1 — the single correctness trap in this feature |
| The shared render chokepoint | `src/core/templates.py:11-13` | 319 of the 320 HTML responses in the product go through `render()`; exactly one call site uses `templates.TemplateResponse` directly, and it is `render()` itself. This is what makes the caching fix (§4.3) one file instead of 73 |
| The global toast | `templates/base.html:2746` — `window.showNotification(message, type)` | Already loaded on every page that extends `base.html`. The success signal needs **no** new UI component and **no** template edits |
| `apply-aggregates` on the प्रपत्र ड form | `docs/plan-form-d-propagation.md` §3.3, Phase 0 | §0.2 — the hard ordering dependency |

### 0.1 THE ONE CORRECTNESS TRAP — `db_item.id` is not always the URL's `id`

For a **district or DCO** caller, `resolve_editable_row()` does not return the row the URL names. It
returns that row's **office contribution**, lifted into total space
(`write.py:176-181` → `_lift_to_total_space`). The consolidated row the district user was looking at
and the office row the handler mutates are **two different rows with two different primary keys**.

Consequently:

> **The redirect target must be built from the request path, never from `db_item.id`.**

Redirecting to `/{db_item.id}/edit` would send a district assistant to the office-contribution row —
a row its own read filter (`orm_filter.py`, `taluka == ''` for district scope) will not return, so
the follow-up GET raises **404** on a save that actually succeeded. It would work perfectly for every
taluka user and for every district that has no active taluka, and fail only for districts running
taluka consolidation. That is exactly the shape of bug that reaches production.

**This is why §6 Phase 0 uses `request.url.path` and not `url_path_for(..., id=db_item.id)`.**
`request.url.path` is the string the browser asked for; it is byte-identical to the GET twin's path
(§0.3), it cannot be wrong, and it is not derived from any mutable state.

### 0.2 HARD DEPENDENCY — this feature was unsafe before Phase 0 of the sibling plan

Returning the user to `GET /budget-post-details/{id}/edit` re-runs that form, which constructs
`PostLevelsManager` (`_levels_section.html:145-155`) and calls `loadLevels()` on init. **Before**
Phase 0 of `docs/plan-form-d-propagation.md`, that path unconditionally `POST`ed
`/{id}/apply-aggregates`, which zeroed all eight pay columns of any post with no levels
(that plan's §3.3). Landing the user back on that form after every save would have turned a
one-off defect into a guaranteed one, on every प्रपत्र ड save, for all 248 seeded rows.

**Phase 0 of the sibling plan is shipped** (`static/js/post_levels.js` now reads
`GET /{id}/aggregates` on page load). Verify that before starting — the check is in §6 Phase 0's
verification block. Do not start this feature against a branch where it is missing.

### 0.3 THE MEASUREMENTS THIS DESIGN RESTS ON

Every number below was measured against the current tree on branch `Dev` (2026-08-26), not assumed:

| Measurement | Result | How |
|---|---|---|
| `POST /{id}/edit` **source** sites | **73** | 72 in per-sub-scheme routers + 1 in the shared factory `s2045/common/district_expenditure/base_router.py:161` |
| `POST /{id}/edit` **mounted** routes | **75** | the shared factory is called by 3 sub-schemes (`s20450182`, `s20450251`, `s20450262`) |
| `GET /{id}/edit` mounted routes | **75** | |
| POST paths with **no** GET twin at the identical path | **0 / 75** | this is what makes `request.url.path` a valid redirect target with no lookup |
| POST handlers that already take `request: Request` | **75 / 75** | the helper needs no new parameter at any site |
| `RedirectResponse(` constructions inside `POST /{id}/edit` handlers | **73** | exactly one per site — no site has a second success path |
| The same, in any other POST handler in `src/schemes` | **0** | the sweep cannot hit an unrelated redirect |
| Existing tests asserting a redirect `Location` | **0** | no test breaks on the destination change |
| `GET /{id}/edit` handlers setting no-cache headers | **15 / 73** | §4.3 — the one genuine technical risk |
| Test baseline | **`215 passed`** | `python -m pytest tests/ -q` |

**Handler families and their current (wrong) destinations — the complete inventory:**

| Family | Sites | Current `url=` |
|---|---|---|
| `ui_update_budget_detail` | 15 | `router.url_path_for("ui_list_budget_details") + "?view=edit"` |
| `ui_update_post_expense` | 15 | `router.url_path_for("ui_list_post_expenses") + "?view=edit"` |
| `ui_update_post_status` | 15 | `router.url_path_for("ui_list_post_status") + "?view=edit"` |
| `ui_update_unit_expenditure` | 15 | `router.url_path_for("ui_list_unit_expenditure") + "?view=edit"` |
| `ui_update_district_expenditure` | 10 + 1 | `router.url_path_for("ui_list_district_expenditure")` / `f"/ui/s{sub_scheme_code}/district-expenditure"` |
| `ui_update_section1` | 2 | `router.url_path_for("ui_list_section1")` |
| | **73** | |

Six families, seven distinct expressions, **one** replacement.

---

## 1. MISSING CONTEXT

**Context sufficient.** All 73 write sites, all 75 mounted route pairs, the shared render helper, the
global notification function, the taluka write path and the full test suite were read and measured
(§0.3). Nothing further is required to implement this.

Two product decisions are open. Both are isolated in §2 with a recommended default, and neither
blocks any phase.

---

## 2. TWO DECISIONS — recommended defaults

| # | Question | Recommended default | Where it lives | Cost to change |
|---|---|---|---|---|
| **D1** | How does the reloaded form tell the user the save worked? | **`?saved=1` on the redirect URL**, read once by a snippet in `base.html` that calls the existing `showNotification(…, 'success')` and then strips the parameter with `history.replaceState`. Stateless, survives the 303, needs no cookie, no session, and **no edits to any of the 75 form templates**. The alternative — a flash cookie — adds a write/read/expire cycle and a same-site attribute to get right, for the same pixel. | `templates/base.html`, ~10 lines | swap the snippet; the server side is unchanged either way |
| **D2** | Should `रद्द करा` / `मागे जा` carry the list filters the user came from? | **No — out of scope.** It is a separate improvement to the *cancel* link, it needs the filter state threaded through the GET form (a query string on every list-row `संपादन` link), and it touches the same 75 templates this design deliberately does not open. Ship the landing fix first. | n/a | additive later; nothing here blocks it |

---

## 3. BLAST RADIUS

### 3.1 Complexity

**Rating: L** — 73 files across every scheme in the product, a new shared helper, a behaviour change
on the single most-used interaction in the application. No schema change, no new invariant, no new
dependency. Required sections: 3, 4, 5, 6.

The *logic* is S. The *reach* is L, and the reach is what governs how this must be sequenced and
verified.

### 3.2 Files affected

**New (2):**

```
src/core/ui_redirects.py                 [NEW]  the one helper
tests/test_post_save_redirect.py         [NEW]  the structural guard
```

**Modified (75):**

| File(s) | Count | Change | Phase |
|---|---|---|---|
| `templates/base.html` | 1 | the `?saved=1` → `showNotification` snippet (D1) | 0 |
| `src/core/templates.py` | 1 | `render()` sets no-store headers (§4.3) | 0 |
| `.../s20530028/{budget_post_details,post_expenses,post_status,unit_expenditure}/controllers/ui_controller.py` | 4 | pilot: swap the redirect | 1 |
| `src/schemes/*/subs/*/ui_budget_details.py` + the 20530028 controller | 15 | swap the redirect | 2 |
| `.../ui_post_expenses.py` (+ 20530028) | 15 | swap the redirect | 3 |
| `.../ui_post_status.py` (+ 20530028) | 15 | swap the redirect | 4 |
| `.../ui_unit_expenditure.py` (+ 20530028) | 15 | swap the redirect | 5 |
| 10 × `router_ui.py` + `s2045/common/district_expenditure/base_router.py` | 11 | swap the redirect | 6 |
| `s0029/subs/s0029/router_ui.py` | 1 (2 sites) | swap the redirect | 6 |
| `docs/ARCHITECTURE.md` | 1 | record the UI write-path convention | 7 |

(Phases 2–5 each include the corresponding 20530028 controller already changed in Phase 1; the counts
above are per family, and Phase 1's four files are not re-edited.)

**No schema change. No migration. No new dependency.** Everything is FastAPI + Starlette + Jinja2,
already in `requirements.txt`. `RedirectResponse` and `status.HTTP_303_SEE_OTHER` are already
imported at all 73 sites.

### 3.3 Explicitly NOT touched

- **Every `POST /api/update-inline`** handler in every scheme. They return JSON, the page never
  navigated, and they already call `showNotification()` + `location.reload()` client-side.
- **`src/core/secure_crud.py`** — the REST API returns models, not redirects.
- **The excel export, chatbot, summary and abstract routes.**
- **`src/schemes/s2075/router_ui.py` and `s2215/.../router_ui.py`** — their `POST /update` endpoints
  return `JSONResponse`, not a redirect. Confirmed, not assumed (§0.3: zero `RedirectResponse`
  constructions outside `POST /{id}/edit`).

---

## 4. DATA & RESILIENCE

### 4.1 Transaction boundaries — **unchanged, and that is a requirement**

Every affected site has the identical shape, and the change is strictly below the last line of it:

```
    ...validate / mutate / audit...
    db.flush()
    consolidate_row(...)             # taluka roll-up
    [derivation hook]                # 20530028 only, plan-form-d-propagation.md rule 5
    db.commit()
    ─────────────────────────────── everything above this line is untouched
    return RedirectResponse(url=<CHANGED>, status_code=303)
```

The redirect is a pure function of `request.url.path`. It reads no session, opens no transaction and
touches no ORM object — so it cannot fail, cannot raise inside a live transaction, and cannot leave a
half-committed state. **A diff that touches anything above the line is out of scope by definition.**

### 4.2 Concurrency

**None introduced.** No lock is taken, extended or reordered. The lock discipline documented in
`docs/plan-form-d-propagation.md` §4.3 (Form D → Form B → Form C, and the `acquire_derivation_locks`
hoist) is entirely above the changed line and is unaffected.

The follow-up `GET /{id}/edit` is a fresh request in a fresh transaction. It re-runs
`resolve_editable_row()`, which for a **safe method** returns the *consolidated* row
(`write.py:166-172`) — so a district user sees the district total it just typed, and a taluka user
sees its own contribution. Both are the values the user expects to be looking at. This is not a
behaviour change; it is the behaviour the existing GET route already has.

### 4.3 Caching — the one genuine technical risk in this feature

A 303 sends the browser to a URL it may have loaded seconds earlier (the user opened the form, typed,
saved, and is now being sent back to the same URL). **Only 15 of the 73 `GET /{id}/edit` handlers set
cache-prevention headers** (§0.3). The other 58 return a bare `200 text/html` with no
`Cache-Control`, no `ETag` and no `Last-Modified`, which leaves freshness to browser heuristics and
leaves the back/forward cache free to replay the **pre-save** DOM.

Landing the user back on a stale copy of the form they just saved is a worse bug than the one this
feature fixes, because it is silent and it looks exactly like a failed save.

**Fix, and why it is one file:** `src/core/templates.py:render()` is the single chokepoint for 319 of
the product's 320 HTML responses (§0.3). Adding the existing header set there covers all 73 forms —
and every other authenticated page — in one place.

- **Header set:** reuse `get_no_cache_headers()` (`src/schemes/common/excel_export.py:89-105`) —
  `Cache-Control: no-cache, no-store, must-revalidate, private`, `Pragma`, `Expires: 0`,
  `X-Content-Type-Options: nosniff`. Do not invent a second header set.
- **Blast radius of doing it centrally, stated honestly:** it changes response headers for every HTML
  page, not only the 73 forms. That is correct for this product — every page `render()` serves is
  authenticated, per-user, per-district and per-fiscal-year, and 15 handlers already do this by hand,
  which is direct evidence of the intended policy. It is also strictly *more* conservative: no-store
  can make a page load slower, never wrong.
- **Do not override a handler's own headers.** The 15 handlers that call
  `response.headers.update(get_no_cache_headers())` set the same values; `render()` must set its
  defaults such that those calls remain no-ops rather than conflicting. Set the headers on the
  response `render()` builds, before returning it.
- **Narrower fallback if the central change is rejected in review:** a `Depends()` no-cache
  dependency added to the 73 `GET /{id}/edit` route decorators. Same effect, 73 files instead of 1.
  Recommend the central change; record the fallback so the reviewer has the alternative in hand.

### 4.4 Idempotency and the double-submit problem

**Improved, not merely preserved.** Post/Redirect/Get already protects against a browser re-POSTing
on refresh, and that protection is unchanged. What changes is that the user is now *on* the resource
they edited, so a refresh re-issues the **GET** — safe and idempotent — instead of returning them to
a list they then have to navigate back from.

**The `?saved=1` parameter must not survive a manual reload**, or every refresh re-fires the success
toast and the user is told a save happened when nothing did. The `base.html` snippet must call
`history.replaceState()` to strip the parameter immediately after firing the toast, so the URL in the
address bar becomes the clean `/{id}/edit` before the user can reload. This is the one behavioural
detail in D1 that is not optional.

### 4.5 Failure handling

| Failure | Behaviour |
|---|---|
| Validation error / `consolidate_row()` 400 | **Unchanged.** The handler's existing `except HTTPException` re-renders its own form with `e.detail`. No redirect is issued, so no `?saved=1`, so no false success toast |
| 403 (permission, timing window) | **Unchanged** — raised before any mutation, surfaced by the existing handler |
| The row is deleted between the commit and the follow-up GET | The GET raises the 404 it already raises for a missing id. Vanishingly rare, correct, and not new |
| A district caller's follow-up GET | Resolves the **consolidated** row by the URL's own id — the id it was already using. §0.1 is what guarantees this; there is no new failure mode as long as `request.url.path` is the source |
| JavaScript disabled | The redirect and the reloaded form still work; only the toast is missing. The saved values are visible in the fields, which is the primary signal. **No server behaviour depends on the toast** |

---

## 5. SECURITY & OBSERVABILITY

### 5.1 Open redirect — the only security-relevant line in this design

A redirect whose target is influenced by user input is an open redirect. This design is immune by
construction, and the immunity must be stated as a rule so a later "improvement" cannot remove it:

> **The redirect target is `request.url.path` — the path the router already matched. It is never
> built from a form field, never from a query parameter, never from a `next=` / `return_to=` value,
> and never from a database column.**

`request.url.path` is server-controlled: it is the routed path, it always begins with `/`, it carries
no scheme or host, and it cannot be steered to another origin. The helper in Phase 0 must **not**
accept a caller-supplied destination — no optional `next` argument, not even "for flexibility". A
helper that cannot express an off-site redirect cannot be misused into one.

### 5.2 Authorisation — no new surface

The redirect grants nothing. The follow-up `GET /{id}/edit` re-runs, from scratch and in a new
request:

1. the router's auth dependency,
2. `resolve_editable_row()` → `validate_access_control(row.district, level, unit, db)` +
   `_writable_taluka_value()` dispatch (`write.py:124-165`),
3. the handler's own `check_data_filling_allowed()` guard where it has one.

A user who could not open that form before the save still cannot open it after. **Nothing about
authorisation is inherited across the redirect** — that is precisely the property that makes PRG safe
here.

### 5.3 Input validation

No new input. The helper takes a `Request` and returns a `RedirectResponse`. The only value read is
`request.url.path`, produced by Starlette's own routing, not by the client body.

### 5.4 Structured logging and metrics

**No new log line, and that is deliberate.** Every affected handler already logs its successful
update (`logger.info("Successfully updated …")` and the `AuditService` record). A second line saying
where the browser was sent would be pure noise at 73 sites.

The one signal worth watching for one release, from the existing access log rather than new code:

- **`303 → GET /{id}/edit` pairs** should replace `303 → GET /<list>` pairs 1:1 after each phase. A
  `303` followed by a **404** on the same path is the §0.1 trap having been reintroduced — that is
  the single alert worth defining, and Phase 1 exists to catch it on four routes before the sweep
  touches 69 more.

---

## 6. EXECUTION PHASES

Ground rules for every phase:

- Baseline: **`python -m pytest tests/ -q` → `215 passed`** (measured 2026-08-26, branch `Dev`,
  after `docs/plan-form-d-propagation.md` Phase 11). No phase may lower that count.
- `python -c "import src.main"` must stay clean.
- **Phases 2–6 exceed three files and cannot be split further.** Each is one mechanical substitution
  repeated across a family of identical handlers, guarded by an automated invariant check
  (Phase 7's test, runnable from Phase 2 onward). Splitting 15 identical one-line edits into five
  phases would leave the product in five partially-migrated states — more risk, not less. This is the
  documented exception; no phase does anything a reviewer must reason about site by site.
- **No phase changes anything above the `db.commit()` line** (§4.1). If a step seems to require it,
  it is wrong — re-read the SCOPE BOUNDARY.

---

### Phase 0: The helper, the toast, and the caching fix
**Scope**: 3 files, ~40 LOC
**Verify**:
1. **Prerequisite check first (§0.2):** `grep -n "apply-aggregates" static/js/post_levels.js` must
   show it reached only from `saveLevel()` / `deleteLevel()`, never from `init()`/page load. If it is
   still on the load path, **stop** and ship `docs/plan-form-d-propagation.md` Phase 0 first.
2. `python -m pytest tests/ -q` → `215 passed` (nothing calls the helper yet — this phase is inert).
3. `curl -sI <any UI page> | grep -i cache-control` → `no-cache, no-store, must-revalidate, private`.

> Ships **first and alone**. It is inert: the helper has no callers and the toast has no trigger until
> Phase 1. That is the point — the risky shared edits land and are observed before 73 sites depend on
> them.

#### [CREATE] `src/core/ui_redirects.py`
- What: one public function,
  `redirect_after_update(request: Request) -> RedirectResponse` — returns
  `303 SEE_OTHER` to `request.url.path` with the D1 success marker appended.
- Pattern: `src/core/templates.py` — a tiny, dependency-light shared module in `src/core/`, imported
  by every scheme, importing no scheme.
- System design:
  - **Takes a `Request` and nothing else.** No `id`, no router, no route name, no destination
    parameter. Every POST handler already has `request` in scope (75/75, §0.3), and the POST path is
    byte-identical to its GET twin (75/75, §0.3), so there is nothing left to get wrong at a call
    site. **§0.1 is enforced by the signature**: there is no way to pass `db_item.id`.
  - **No `next` / `return_to` argument, now or ever** (§5.1). The absence of the parameter *is* the
    open-redirect defence.
  - Preserve any existing query string on the POST path — currently always empty for these routes,
    but appending blindly with `?` would corrupt a URL the day one is added. Compose the marker with
    `urlencode` onto the parsed query, the way `ui_controller.py` already builds
    `export_query_string_list` (`post_status/controllers/ui_controller.py:192-194`).
  - Module docstring states the §0.1 trap in two sentences. It is the reason this module exists.

#### [MODIFY] `templates/base.html`
- What: a small script beside the existing `window.showNotification` definition (line 2746): on
  `DOMContentLoaded`, if `URLSearchParams(location.search)` carries the D1 marker, fire
  `showNotification('रेकॉर्ड यशस्वीरित्या अपडेट झाला', 'success')` and immediately
  `history.replaceState({}, '', <url without the marker>)`.
- Pattern: `showNotification` is already global and already used from list templates
  (`post_status_list.html`'s inline-edit handler). Reuse it — do **not** add a banner element, a CSS
  class, or a second notification mechanism.
- System design:
  - **The `replaceState` call is mandatory, not cosmetic** (§4.4). Without it, every manual refresh
    re-announces a save that did not happen.
  - Placed in `base.html`, so **all 75 form templates get it with zero edits**. Do not put it in a
    form template; there are 75 of them and they would drift.
  - Guard on the element `showNotification` writes into (`notification-container`) existing, so a page
    that does not extend the full base chrome degrades to silence, not a JS error.

#### [MODIFY] `src/core/templates.py`
- What: `render()` sets the no-cache header set on the response it returns (§4.3).
- Pattern: reuse `get_no_cache_headers()` (`src/schemes/common/excel_export.py:89-105`) — the exact
  header set 15 handlers already apply by hand. Do not define a second one.
- System design: the 15 existing `response.headers.update(get_no_cache_headers())` calls must remain
  correct no-ops. Set the headers on the constructed response before returning, so a handler that
  updates them afterwards writes identical values. **This is the widest-reaching edit in the whole
  plan — one function, every HTML response — which is exactly why it ships alone in Phase 0 and is
  verified with `curl -I` before anything depends on it.**

---

### Phase 1: Pilot — sub-scheme 20530028, all four forms
**Scope**: 4 files, ~8 LOC
**Verify**: `python -m pytest tests/ -q` → `215 passed`; then **by hand in the browser**, for each of
प्रपत्र ड / प्रपत्र क / प्रपत्र ब / प्रपत्र अ: edit a value, click **अपडेट रेकॉर्ड**, and confirm
(a) the URL is still `/{id}/edit`, (b) the field shows the new value, (c) the success toast appears
once, (d) a manual refresh does **not** re-fire the toast, (e) `python scripts/check_taluka_invariant.py`
is clean.

> **The one phase a human must actually click through**, and the reason it is separated from the
> sweep. 20530028 is the only sub-scheme with taluka consolidation *and* cross-form derivation live,
> so it exercises §0.1 (district total-space lift), §4.2 (consolidated read-back) and the sibling
> plan's propagation hook on the same four routes. If `request.url.path` were the wrong choice, it
> fails here, at four sites, before 69 more adopt it.
>
> **Test it as a district user of a district with at least one active taluka.** A district with no
> taluka never exercises the lift and would pass even with the §0.1 bug present.

#### [MODIFY] the four `.../s20530028/*/controllers/ui_controller.py`
- Files: `budget_post_details/`, `post_expenses/`, `post_status/`, `unit_expenditure/`.
- What: in each `POST /{id}/edit` success path, replace the `RedirectResponse(...)` construction with
  `return redirect_after_update(request)`. **One line each. Nothing else in the handler changes.**
- Pattern: the sites are `budget_post_details/controllers/ui_controller.py:479-482`,
  `post_expenses/controllers/ui_controller.py:415-418`, `post_status/controllers/ui_controller.py`
  (the `ui_update_post_status` success return), and `unit_expenditure/controllers/ui_controller.py`.
- System design:
  - `post_status`'s form is reachable for editing **only on `Filled` rows** — `Vacant` rows render
    without a submit button (`docs/plan-form-d-propagation.md` AMENDMENT 1). The redirect therefore
    only ever fires on a row whose GET form the user can act on. No special case needed; noted so it
    is not mistaken for a gap.
  - `post_expenses`'s handler fans out to every प्रपत्र ब row of the district before committing. The
    redirect still targets the row the user opened. Correct: that is the row whose form is on screen.
  - Leave the now-unused `RedirectResponse` / `status` imports alone if other routes in the file still
    use them; remove them only where they become genuinely unreferenced. Do not let an import cleanup
    turn a 1-line diff into a 5-line one.

---

### Phase 2: `ui_update_budget_detail` — 14 remaining sites
**Scope**: 14 files, ~28 LOC
**Verify**: `python -m pytest tests/ -q` → `215 passed`; `python -m pytest tests/test_post_save_redirect.py -q`
(Phase 7's guard, written early and run from here on) reports **0** remaining list-redirects in this
family; spot-check one legacy sub-scheme in the browser.

#### [MODIFY] `src/schemes/*/subs/*/ui_budget_details.py` × 14
- What: the identical one-line replacement from Phase 1.
- Pattern: every site currently reads
  `url=router.url_path_for("ui_list_budget_details") + "?view=edit"`. One literal, 14 occurrences.
- System design: **mechanical, and must stay mechanical.** These 14 files differ in validation, in
  their audit calls and in their error rendering — none of which is being touched. If a site's
  redirect does not match the literal above, **stop and read that handler** rather than adapting the
  replacement; a divergent redirect means a divergent success path, which this design has not
  accounted for. (Measured: no such site exists today — §0.3 — so any divergence is new.)

---

### Phase 3: `ui_update_post_expense` — 14 remaining sites
**Scope**: 14 files, ~28 LOC
**Verify**: as Phase 2, for this family.

#### [MODIFY] `src/schemes/*/subs/*/ui_post_expenses.py` × 14
- What / Pattern / System design: identical to Phase 2; current literal is
  `url=router.url_path_for("ui_list_post_expenses") + "?view=edit"`.

---

### Phase 4: `ui_update_post_status` — 14 remaining sites
**Scope**: 14 files, ~28 LOC
**Verify**: as Phase 2, for this family.

#### [MODIFY] `src/schemes/*/subs/*/ui_post_status.py` × 14
- What / Pattern / System design: identical to Phase 2; current literal is
  `url=router.url_path_for("ui_list_post_status") + "?view=edit"`.

---

### Phase 5: `ui_update_unit_expenditure` — 14 remaining sites
**Scope**: 14 files, ~28 LOC
**Verify**: as Phase 2, for this family.

#### [MODIFY] `src/schemes/*/subs/*/ui_unit_expenditure.py` × 14
- What / Pattern / System design: identical to Phase 2; current literal is
  `url=router.url_path_for("ui_list_unit_expenditure") + "?view=edit"`.

---

### Phase 6: The two families with a different shape — district expenditure and section 1
**Scope**: 12 files, ~26 LOC
**Verify**: `python -m pytest tests/ -q` → `215 passed`; the Phase 7 guard reports **0** remaining
list-redirects **product-wide**; browse-test one `s7610` sub-scheme and `s0029`.

> Kept last and kept together because these are the only two families whose current redirect is **not**
> the `+ "?view=edit"` literal, and the only place a shared factory is involved. Sweeping them with
> the same `sed` as Phases 2–5 would silently miss them.

#### [MODIFY] `src/schemes/s2045/common/district_expenditure/base_router.py`
- What: the one-line replacement at `ui_update_district_expenditure`'s success return (line 228).
- System design: **this single site serves 3 mounted sub-schemes** (`s20450182`, `s20450251`,
  `s20450262`). Its current target is an f-string, `f"/ui/s{sub_scheme_code}/district-expenditure"` —
  hand-built, not `url_path_for` — which is exactly why the family-literal sweep cannot reach it.
  After the change it uses `request.url.path` like every other site and no longer needs
  `sub_scheme_code` to build a URL at all.

#### [MODIFY] 10 × `src/schemes/{s2235,s6245,s6401,s7610}/subs/*/router_ui.py`
- What: the identical replacement; current literal is
  `url=router.url_path_for("ui_list_district_expenditure")` — **no `?view=edit` suffix**.
- System design: these 10 sub-schemes each carry their own copy of the handler rather than using the
  factory above. That duplication is pre-existing and **out of scope** — do not consolidate them into
  the factory while here. Note it for a separate ticket.

#### [MODIFY] `src/schemes/s0029/subs/s0029/router_ui.py`
- What: **two** sites in this one file (`ui_update_section1`, `url_path_for("ui_list_section1")`).
  The only file with more than one site — check for both.

---

### Phase 7: The structural guard and the documented convention
**Scope**: 2 files, ~90 LOC
**Verify**: `python -m pytest tests/ -q` → **≥ 219 passed**

#### [CREATE] `tests/test_post_save_redirect.py`
- What, at minimum:
  1. **Pairing invariant:** every mounted `POST /{id}/edit` route has a `GET` route at the **identical
     path** — the property `request.url.path` depends on. Asserted over `src.main.app.routes`, so a
     future route added without its GET twin fails here rather than in production. Currently
     **75 / 75**.
  2. **`request` in scope:** every mounted `POST /{id}/edit` endpoint takes a `request` parameter.
     Currently **75 / 75**. This is what lets the helper stay parameterless.
  3. **No list-redirect survives:** static scan of `src/schemes` — **zero** `RedirectResponse(`
     constructions remain inside any `POST /{id}/edit` handler body. This is the sweep's completion
     proof and the regression guard for every future sub-scheme, and it is the assertion Phases 2–6
     run after each family.
  4. **§0.1 pinned:** the helper, given a `Request` for `/ui/sX/post-expenses/7/edit`, returns a `303`
     whose `Location` path is exactly `/ui/sX/post-expenses/7/edit` — **independently of any row id**.
     Docstring must name the trap: redirecting to `db_item.id` 404s for district callers under taluka
     consolidation.
  5. **No open redirect:** the helper's signature accepts no destination, and its `Location` is always
     relative and always begins with `/` (§5.1). A `next=`/`return_to=` parameter added later fails
     this test.
  6. **`?saved=1` fires the toast once:** `base.html` contains both the marker read **and** a
     `history.replaceState` call (§4.4). A static assertion — cheap, and it pins the one detail whose
     absence is invisible until a user refreshes.
- Pattern: `tests/test_s20530028_derivation_e2e.py`'s route-introspection test
  (`test_form_c_put_route_stays_suppressed`) for the `app.routes` walk, and its
  `test_templates_lock_derived_fields_and_only_those` for the static template assertions.
- System design: **tests 1–3 are the real deliverable of this phase.** They convert a 73-site
  convention into an invariant the suite enforces, which is the only thing that stops the next
  sub-scheme from copy-pasting the old redirect back in.

#### [MODIFY] `docs/ARCHITECTURE.md`
- What: extend the **Write-path rules** list (beside rules 1–6 added by
  `docs/plan-form-d-propagation.md`) with:
  - **rule 7** — *"a UI `POST /{id}/edit` returns `redirect_after_update(request)`
    (`src/core/ui_redirects.py`) after `commit()`. The destination is the request path, never
    `db_item.id`: `resolve_editable_row()` can return a different row than the URL names, and that row
    is invisible to a district caller's read filter (see §0.1 of
    `docs/plan-post-save-return-to-form.md`)."*
- Also record that `render()` sets no-store headers for every HTML response (§4.3), so a future
  handler does not add a third header set by hand.

---

## 7. WHAT THIS DESIGN DELIBERATELY DOES NOT DO

| Not done | Why | What it would cost later |
|---|---|---|
| Redirect to `url_path_for("ui_edit_…_form", id=db_item.id)` | §0.1 — `db_item.id` is the office-contribution row for district callers, which their own read filter hides. It 404s exactly on the districts running taluka consolidation and passes everywhere else | n/a — this is the bug, not an alternative |
| Give the helper a `next` / `return_to` parameter | §5.1 — a redirect helper that cannot express an off-site destination cannot be turned into an open redirect. The absence of the parameter is the control | n/a |
| A flash cookie / server-side session message | D1 — same pixel, plus a write/read/expire cycle and a `SameSite` attribute to get right. `?saved=1` + `replaceState` is stateless and survives the 303 | swap the `base.html` snippet; the server side is unchanged |
| Edit the 75 `*_form.html` templates to add a success banner | `showNotification` is already global in `base.html:2746`. 75 template edits for something one shared snippet does is how drift starts | n/a |
| Preserve list filters on `रद्द करा` | D2 — a separate improvement to the *cancel* link, needing filter state threaded through 75 templates | additive; nothing here blocks it |
| Change the `POST /api/update-inline` handlers | They never navigate away; there is no landing to fix | n/a |
| Add a create (`/new`) route so the create branch of the form templates works | **Verified: no create route exists in any scheme.** Rows are seeded and cloned per fiscal year. The dead `{{ '…/new' }}` action is pre-existing | separate ticket, and a product decision first — does the client want ad-hoc row creation at all? |
| Consolidate the 10 duplicated `ui_update_district_expenditure` handlers into the shared factory they already have | Real duplication, real cleanup — and completely unrelated blast radius to ride along on a redirect change | separate ticket; Phase 6 records it |
| Apply no-store per-route instead of in `render()` | 73 files instead of 1, for identical behaviour on the forms and *less* correct behaviour everywhere else (§4.3) | the fallback is written down in §4.3 if review prefers it |

---

## 8. ROLLOUT ORDER (operational, not code)

1. **Confirm the §0.2 prerequisite.** `static/js/post_levels.js` must not `POST` `apply-aggregates` on
   page load. This is a hard gate, not a checklist item.
2. **Phase 0 ships alone.** It is inert for this feature but changes cache headers product-wide.
   Watch for one day: no stale-page reports, no broken export downloads (the exports set their own
   headers and are unaffected — confirm, don't assume).
3. **Phase 1 (pilot) ships alone, and a human clicks through all four 20530028 forms as a district
   user of a district with an active taluka.** This is the §0.1 gate. Do not proceed on a green test
   suite alone — no automated test in this plan exercises a real browser 303 → GET → session cookie
   round trip.
4. Phases 2–6, one family per deploy if the release cadence allows, each followed by the Phase 7
   guard. The families are independent; a partially-migrated product is fully functional, with some
   forms returning to the list and some to themselves.
5. Phase 7 last. Its tests 1–3 are what stop the convention from decaying.
6. **Watch the access log for one data-filling cycle:** a `303` followed by a `404` on the same path
   is the §0.1 trap. Expected count: zero.
