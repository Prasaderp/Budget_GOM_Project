Enforce स्तर (Level) Limit Based on मंजूर पदे (Sanctioned Posts)
Problem
In प्रपत्र ड (Form D), each designation (budget post) has a sanctioned_posts_curr (मंजूर पदे for current fiscal year) field. The स्तर व्यवस्थापन (Level Management) section allows users to add unlimited sub-levels per designation. There is no validation — a user can add 10 levels even if मंजूर पदे is only 3. The limit must be: number of levels ≤ sanctioned_posts_curr.

Data Flow (Traced)
User clicks "+ स्तर जोडा" button
    → PostLevelsManager.showAddForm() in post_levels.js
    → PostLevelsManager.saveLevel()
    → POST to /api/post-levels (created by create_post_levels_router())
    → api_router.py::create_level() endpoint
    → PostLevelService.create_level()
    → PostLevelRepository.create()
    → INSERT into post_level_details table
Key fields:

BudgetPostDetails.sanctioned_posts_curr — The limit (मंजूर पदे current year)
PostLevelRepository.get_count() — Already exists, counts levels per budget_post_id
PostLevelsManager
 (JS class) — No limit knowledge currently
Proposed Changes
Component 1: Common Post Levels Module (Shared — affects ALL subschemas)
This is the core enforcement layer. Since ALL subschemas use 
create_post_levels_router()
 with the same 
api_router.py
, changes here propagate to every subschema automatically.

[MODIFY] 
api_router.py
What changes: Add level-count limit validation in the 
create_level
 endpoint and add a new /limit-info endpoint.

Change 1 — 
create_level
 endpoint (line ~87–150): After the budget_post is fetched and access is validated, add a limit check BEFORE creating the level:

python
# ---- NEW: Enforce level count limit based on sanctioned_posts_curr ----
current_count = service.repository.get_count(
    level_data.budget_post_id, sub_scheme_code, table_name, fiscal_year
)
max_allowed = budget_post.sanctioned_posts_curr  # None/0 = no levels allowed
if max_allowed is None or max_allowed <= 0:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="मंजूर पदे 0 आहे. कृपया प्रथम मंजूर पदे भरा."
    )
if current_count >= max_allowed:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"मंजूर पदे मर्यादा ({max_allowed}) पूर्ण झाली आहे. आणखी स्तर जोडता येणार नाहीत."
    )
# ---- END NEW ----
Why HTTP 409? It's a conflict between the current state (full count) and the requested action (add more). This is semantically correct and distinguishable from 400/403 on the frontend.

Change 2 — New GET /{budget_post_id}/limit-info endpoint: Add a new lightweight endpoint that returns the current count and the maximum allowed count. This is consumed by the frontend to show real-time remaining capacity.

python
@router.get("/{budget_post_id}/limit-info", response_model=dict)
async def get_level_limit_info(
    request: Request,
    budget_post_id: int,
    service: PostLevelService = Depends(get_service),
    db: Session = Depends(get_db)
):
    """Get level count and sanctioned limit for a budget post"""
    fiscal_year = get_fiscal_year_from_request(request, db)
    budget_post = service.db.query(budget_post_model).filter(
        budget_post_model.id == budget_post_id,
        budget_post_model.fiscal_year == fiscal_year
    ).first()
    if not budget_post:
        raise HTTPException(status_code=404, detail="Budget post not found")
    
    current_count = service.repository.get_count(
        budget_post_id, sub_scheme_code, table_name, fiscal_year
    )
    max_allowed = budget_post.sanctioned_posts_curr or 0
    
    return {
        "current_count": current_count,
        "max_allowed": max_allowed,
        "can_add": max_allowed > 0 and current_count < max_allowed
    }
No new model/schema needed — returns a simple dict. When max_allowed is 0, can_add is False — users MUST set मंजूर पदे before adding levels.

[MODIFY] 
service.py
What changes: Add a check_level_limit() method that encapsulates the limit-check business logic.

python
def check_level_limit(
    self,
    budget_post_id: int,
    sub_scheme_code: str,
    table_name: str,
    fiscal_year: str,
    max_allowed: int
) -> tuple[bool, int, int]:
    """Check if more levels can be added.
    
    Returns:
        (can_add, current_count, max_allowed)
    """
    current_count = self.repository.get_count(
        budget_post_id, sub_scheme_code, table_name, fiscal_year
    )
    if max_allowed <= 0:
        return (False, current_count, max_allowed)  # 0 = BLOCKED, not unlimited
    return (current_count < max_allowed, current_count, max_allowed)
Why a separate method? Single responsibility — the validation logic lives in the service, reusable from any caller (API router, batch imports, future tests). The 
api_router.py
 can call this directly, or inline the logic — either pattern works. However, keeping it in the service makes it testable and reusable.

No changes needed to:
repository.py
 — 
get_count()
 already exists and works correctly
models.py
 — No schema changes
schemas.py
 — No new schemas needed
Component 2: Frontend — JavaScript (
post_levels.js
)
[MODIFY] 
post_levels.js
What changes: 4 changes total.

Change 1 — Constructor: Add limit tracking properties (line ~4–20):

javascript
this.maxAllowed = config.maxLevelsAllowed || 0;  // 0 = BLOCKED (must set मंजूर पदे first)
this.currentCount = 0;
Change 2 — 
init()
: Load limit info after levels (line ~22–27):

javascript
async init() {
    this.bindEvents();
    await this.loadDaRate();
    await this.loadPayMatrixStages();
    await this.loadLevels();
    await this.loadLimitInfo();  // NEW
}
Change 3 — New method loadLimitInfo():

javascript
async loadLimitInfo() {
    try {
        const res = await fetch(
            `${this.apiBasePath}/${this.budgetPostId}/limit-info`,
            { cache: 'no-store' }
        );
        if (!res.ok) return;
        const data = await res.json();
        this.maxAllowed = data.max_allowed || 0;
        this.currentCount = data.current_count || 0;
        this.updateAddButtonState();
    } catch (e) {
        console.error('Failed to load limit info:', e);
    }
}
Change 4 — New method updateAddButtonState():

javascript
updateAddButtonState() {
    const btn = document.getElementById('addLevelBtn');
    if (!btn) return;
    
    if (this.maxAllowed <= 0) {
        // maxAllowed is 0 or not set → BLOCK completely
        btn.textContent = '+ स्तर जोडा (मंजूर पदे भरा)';
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
        btn.title = 'कृपया प्रथम मंजूर पदे भरा';
        return;
    }
    
    const remaining = this.maxAllowed - this.levels.length;
    btn.textContent = `+ स्तर जोडा (${this.levels.length}/${this.maxAllowed})`;
    
    if (remaining <= 0) {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
        btn.title = `मंजूर पदे मर्यादा (${this.maxAllowed}) पूर्ण झाली`;
    } else {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        btn.title = `${remaining} स्तर अजून जोडता येतील`;
    }
}
Change 5 — Modify 
showAddForm()
 to block when limit reached (line ~211–217):

javascript
showAddForm() {
    // Check limit before showing form
    if (this.maxAllowed <= 0) {
        const msg = 'कृपया प्रथम मंजूर पदे भरा. मंजूर पदे 0 असताना स्तर जोडता येत नाहीत.';
        alert(msg);
        if (typeof showNotification === 'function') {
            showNotification(msg, 'error');
        }
        return;
    }
    if (this.levels.length >= this.maxAllowed) {
        const msg = `मंजूर पदे मर्यादा (${this.maxAllowed}) पूर्ण झाली आहे.\nआणखी स्तर जोडता येणार नाहीत.`;
        alert(msg);
        if (typeof showNotification === 'function') {
            showNotification(msg, 'error');
        }
        return;
    }
    this.editingLevelId = null;
    this.resetForm();
    // ... rest unchanged
}
Change 6 — Modify 
saveLevel()
 to handle 409 response (line ~291–342): In the catch block after the fetch, add specific handling for 409:

javascript
if (!res.ok) {
    const err = await res.json();
    if (res.status === 409) {
        // Limit reached — reload limit info and update button
        await this.loadLimitInfo();
    }
    throw new Error(err.detail || 'जतन अयशस्वी');
}
Change 7 — Modify 
loadLevels()
 to update button state after load (line ~162–176): After this.updatePreview(), add:

javascript
this.updateAddButtonState();
Change 8 — Modify 
deleteLevel()
 to update button state after delete: After await this.loadLevels(), add:

javascript
await this.loadLimitInfo();
Change 9 — Modify 
updatePreview()
 to include limit info (line ~365–380): Update the preview text to show the limit:

javascript
const limitText = this.maxAllowed > 0 
    ? ` | <strong>मर्यादा:</strong> ${this.levels.length}/${this.maxAllowed}`
    : ' | <strong style="color:var(--danger,#dc2626)">⚠ मंजूर पदे भरा</strong>';
preview.innerHTML = `<strong>एकूण स्तर:</strong> ${this.levels.length}${limitText} | ...`;

Change 10 — New method updateMaxAllowed() for live मंजूर पदे changes:
When the user changes the SanctionedPostsCurr input field on the form page, the JS must react immediately:

javascript
updateMaxAllowed(newMax) {
    this.maxAllowed = parseInt(newMax) || 0;
    this.updateAddButtonState();
    this.updatePreview();
}
Component 3: Frontend — Shared HTML Template
[MODIFY] 
_levels_section.html
What changes: Pass sanctioned_posts_curr as maxLevelsAllowed config to 
PostLevelsManager
.

Change 1 — Update PostLevelsManager initialization (line ~147–154):

javascript
postLevelsManager = new PostLevelsManager({
    budgetPostId: {{ detail.id }},
    apiBasePath: '{{ api_base_path|default("/ui/s20530028/budget-post-details/api/post-levels") }}',
    payMatrixApiPath: '{{ pay_matrix_api_path|default("/ui/s20530028/budget-post-details/api/pay-matrix") }}',
    subSchemeCode: '{{ sub_scheme_code|default("20530028") }}',
    tableName: '{{ table_name|default("budget_post_details_20530028") }}',
    fiscalYear: '{{ request.cookies.get("fiscal_year", "2025-26") }}',
    maxLevelsAllowed: {{ detail.sanctioned_posts_curr|default(0) }}  // NEW
});
This gives the JS class an initial limit value from the server-rendered template. The loadLimitInfo() API call then refreshes this from the backend (source of truth) — so even if the DOM is stale, the API enforces the real limit.

Change 2 — Event listener on SanctionedPostsCurr input (add after PostLevelsManager init):
This is CRITICAL: when the user changes मंजूर पदे on the form page, the स्तर section must react LIVE:

javascript
// Live-sync मंजूर पदे changes to post levels manager
const sanctionedInput = document.getElementById('SanctionedPostsCurr');
if (sanctionedInput && postLevelsManager) {
    sanctionedInput.addEventListener('change', function() {
        postLevelsManager.updateMaxAllowed(this.value);
    });
    sanctionedInput.addEventListener('input', function() {
        postLevelsManager.updateMaxAllowed(this.value);
    });
}

This handles the edge case where a user has 3 levels, then edits मंजूर पदे from 3 to 2 — the button immediately disables and shows (3/2) with a visual warning.

Optional Change — Add limit indicator badge next to the header:

html
<div id="levelLimitBadge" style="display:none;padding:4px 12px;background:var(--warning-bg,#fef3cd);
    color:var(--warning-text,#856404);border-radius:var(--radius-md);font-size:13px;font-weight:600;">
</div>
Component 4: s20530028 — Micro-Architecture Sample
These are the files that need attention for s20530028 specifically. The common post_levels module handles the create-level limit automatically, but we also need to validate when sanctioned_posts_curr ITSELF is being reduced.

[NO CHANGE] 
api_controller.py
Already uses create_post_levels_router() which gets the limit check automatically on level creation.

[MODIFY] api_controller.py — api_update_inline endpoint
The inline update API (POST /api/update-inline) allows changing SanctionedPostsCurr. We MUST validate that the new value is not less than the current level count.

After the record is fetched and before updating (around line 240-255), add:

python
# ---- NEW: Validate sanctioned_posts_curr reduction ----
from src.schemes.common.post_levels.repository import PostLevelRepository
post_level_repo = PostLevelRepository(db)
current_level_count = post_level_repo.get_count(
    record.id, sub_scheme, "budget_post_details_20530028", fiscal_year
)
if SanctionedPostsCurr < current_level_count:
    return JSONResponse({
        "success": False,
        "message": f"मंजूर पदे {SanctionedPostsCurr} पेक्षा {current_level_count} स्तर आधीच अस्तित्वात आहेत. कृपया प्रथम स्तर हटवा."
    }, status_code=400)
# ---- END NEW ----

[MODIFY] budget_post_service.py — update_inline and update_form methods
Both update methods need a level-count guard. Add level count validation in update_inline() (line ~154-155) and update_form() (line ~193-197):

In update_inline(), before setting record.sanctioned_posts_curr:

python
# ---- NEW: Prevent reducing sanctioned_posts_curr below existing level count ----
if update_dto.sanctioned_posts_curr is not None:
    from src.schemes.common.post_levels.repository import PostLevelRepository
    post_level_repo = PostLevelRepository(self.repository.session)
    level_count = post_level_repo.get_count(
        record.id, sub_scheme_code,
        record.__tablename__, record.fiscal_year
    )
    if update_dto.sanctioned_posts_curr < level_count:
        raise ValueError(
            f"मंजूर पदे {update_dto.sanctioned_posts_curr} ठेवता येत नाही कारण {level_count} स्तर आधीच आहेत. प्रथम स्तर हटवा."
        )
# ---- END NEW ----

Same logic for update_form().

[NO CHANGE] 
ui_controller.py
Already passes detail (which includes sanctioned_posts_curr) to the template.

[NO CHANGE] 
budget_post_details_form.html
Already includes _levels_section.html. The shared template changes propagate automatically.

[NO CHANGE] Other s20530028 files
models.py — sanctioned_posts_curr already exists
schemas.py — No changes
config.py — No changes
helpers.py — No changes
router_api.py, router_ui.py — No changes
All export files — No changes
Component 5: s20530019 — Monolithic Sample
Same situation — level creation is guarded by the common module. But we also need the sanctioned_posts_curr reduction validation here.

[NO CHANGE] Level creation
Already uses create_post_levels_router(). Gets the limit check automatically.

[MODIFY] api_budget_details.py — api_update_inline endpoint
The inline update (POST /api/update-inline, line 160-243) sets record.sanctioned_posts_curr directly at line 217. Add validation BEFORE that line:

python
# ---- NEW: Validate sanctioned_posts_curr reduction ----
from src.schemes.common.post_levels.repository import PostLevelRepository
post_level_repo = PostLevelRepository(db)
fiscal_year = get_fiscal_year_from_request(request, db)
current_level_count = post_level_repo.get_count(
    record.id, sub_scheme, "budget_post_details_20530019", fiscal_year
)
if SanctionedPostsCurr < current_level_count:
    return JSONResponse({
        "success": False,
        "message": f"मंजूर पदे {SanctionedPostsCurr} पेक्षा {current_level_count} स्तर आधीच अस्तित्वात आहेत. कृपया प्रथम स्तर हटवा."
    }, status_code=400)
# ---- END NEW ----

[MODIFY] ui_budget_details.py — ui_update_budget_detail (form POST)
The form update (POST /{id}/edit, line 276-401) sets sanctioned_posts_curr via update_dict at line 337. Add validation BEFORE the update loop:

python
# ---- NEW: Validate sanctioned_posts_curr reduction ----
if SanctionedPostsCurr is not None:
    from src.schemes.common.post_levels.repository import PostLevelRepository
    post_level_repo = PostLevelRepository(db)
    current_level_count = post_level_repo.get_count(
        db_detail.id, sub_scheme, "budget_post_details_20530019", db_detail.fiscal_year
    )
    if SanctionedPostsCurr < current_level_count:
        raise HTTPException(
            status_code=400,
            detail=f"मंजूर पदे {SanctionedPostsCurr} ठेवता येत नाही कारण {current_level_count} स्तर आधीच आहेत. प्रथम स्तर हटवा."
        )
# ---- END NEW ----

[NO CHANGE] 
budget_post_details_form.html
Already includes _levels_section.html. The shared template changes propagate automatically.

[NO CHANGE] Other s20530019 files
models.py, schemas.py, config.py, helpers.py, router_api.py, router_ui.py — No changes
excel_export/ — No changes
Component 6: Cache Considerations
[NO CHANGE] — No cache invalidation changes needed
The existing cache invalidation (CacheService.invalidate_scheme_cache() / invalidate_scheme_cache()) is already called when levels are created/updated/deleted and when sanctioned_posts_curr is updated. The new /limit-info endpoint uses cache: 'no-store' on the frontend, and the backend reads directly from DB.

The 
PostLevelsManager
 JS class fetches limit info fresh on every page load and after every create/delete operation (see Change 2, 7, 8). No stale cache issues.

Summary of ALL Files That Need Changes

# Common (propagates to ALL subschemas)
1. src/schemes/common/post_levels/api_router.py — Backend: Add limit check in create_level (0=blocked), add /limit-info endpoint
2. src/schemes/common/post_levels/service.py — Backend: Add check_level_limit() method (0=blocked)
3. static/js/post_levels.js — Frontend JS: Add limit tracking, button state, form guard, 409 handling, updateMaxAllowed(), 0=blocked state
4. templates/schemes/common/post_levels/_levels_section.html — Frontend HTML: Pass maxLevelsAllowed, event listener on SanctionedPostsCurr input, limit badge

# s20530028 Micro-Architecture (sample)
5. src/schemes/s2053/subs/s20530028/budget_post_details/controllers/api_controller.py — Backend: Validate sanctioned_posts_curr reduction in inline update
6. src/schemes/s2053/subs/s20530028/budget_post_details/services/budget_post_service.py — Backend: Level-count guard in update_inline() and update_form()

# s20530019 Monolithic (sample)
7. src/schemes/s2053/subs/s20530019/api_budget_details.py — Backend: Validate sanctioned_posts_curr reduction in inline update
8. src/schemes/s2053/subs/s20530019/ui_budget_details.py — Backend: Validate sanctioned_posts_curr reduction in form update

Total: 8 files. 4 common (all subschemas), 2 per-subschema for reduction validation.

Files That Do NOT Change (Confirmed)
These are explicitly listed so a less-experienced developer doesn't waste time looking at them:

src/schemes/s2053/subs/s20530028/budget_post_details/controllers/ui_controller.py ✅ No change
src/schemes/s2053/subs/s20530028/models.py ✅ No change
src/schemes/s2053/subs/s20530019/models.py ✅ No change
ALL budget_post_details_form.html templates ✅ No change (they include _levels_section.html)
src/schemes/common/post_levels/repository.py ✅ No change (get_count() already exists)
src/schemes/common/post_levels/models.py ✅ No change
src/schemes/common/post_levels/schemas.py ✅ No change
Replicating to Other Subschemas
Since all subschemas share:

The common 
create_post_levels_router()
 from 
api_router.py
 (backend)
The shared 
_levels_section.html
 template (frontend)
The shared 
post_levels.js
 (JavaScript)
No additional changes are needed for any other subschema. All s2053 subschemas (s20530153, s20530233, s20530304, s20530378, s20530162, s20530242, s20530313, s20530387), all s2029 subschemas, and all s2045 subschemas automatically get this feature.

Edge Cases Handled

1. sanctioned_posts_curr = 0 or NULL → BLOCKED. Button shows "मंजूर पदे भरा", API returns 409. Users MUST fill मंजूर पदे before adding ANY levels.

2. Race condition (concurrent tabs) → Two tabs open, both try to add the last allowed level. Backend is source of truth — get_count() runs inside the create endpoint BEFORE insert. Only one succeeds, the other gets 409.

3. Reducing sanctioned_posts_curr AFTER levels exist:
   - User has 3 levels, tries to set मंजूर पदे to 2 → BLOCKED with error message: "3 स्तर आधीच आहेत, प्रथम स्तर हटवा"
   - Backend validation in BOTH inline update API and form POST prevents the DB write
   - Existing levels are NEVER auto-deleted (protects user data)
   - User must manually delete excess levels first, then reduce मंजूर पदे

4. Live form field change → When user changes the SanctionedPostsCurr input on the form page:
   - The event listener fires immediately (both 'change' and 'input' events)
   - PostLevelsManager.updateMaxAllowed() updates the limit in-memory
   - Button state updates instantly (e.g., if reducing from 3→2 while 3 levels exist, button shows "3/2" and disables)
   - This is CLIENT-SIDE only — the actual save is still guarded by backend validation

5. Inline edit on list page → The api/update-inline endpoint validates the new sanctioned_posts_curr against existing level count BEFORE writing to DB.

6. Fiscal year switch → Existing FY mismatch detection (already in form templates) redirects the user. Levels are FY-scoped in DB, so no cross-FY pollution.

7. Page reload after adding levels → loadLimitInfo() fetches fresh data from /limit-info API on every page load. No stale state.

8. Deleting levels then re-checking → After deleteLevel(), loadLimitInfo() is called, which refreshes currentCount and re-enables the button if under limit.

9. Form submitted without saving levels first → On form POST (sanctioned_posts_curr update), backend checks level count. If user set मंजूर पदे = 2 but had previously added 3 levels, the form POST itself is rejected.

10. Browser dev tools / API bypass → Even if someone sends a direct POST to the create_level API, the backend check_level_limit runs before insert. Cannot bypass.

11. Multiple designations → Each designation (budget_post_id) has its OWN independent limit (its own sanctioned_posts_curr). Levels for designation A don't affect designation B.

12. Admin vs Assistant roles → Level creation is already gated by auth_role and data_filling_period checks. The new limit check runs AFTER those checks, so admins/officers who can't create data won't get confusing limit messages.

Verification Plan
Manual Verification (Browser Testing)
No existing test suite was found in the project (only vendor tests in venv/). All verification must be manual via browser.

Test Case 1: Basic limit enforcement
1. Login as assistant → Navigate to s20530028 → प्रपत्र ड → Edit view
2. Click a designation with मंजूर पदे 2026-27 = 3
3. Verify button shows "+ स्तर जोडा (0/3)"
4. Add 3 levels → each succeeds
5. Verify button shows "(3/3)" and is disabled
6. Try clicking → alert with limit message
7. Direct POST via dev tools → HTTP 409

Test Case 2: Zero मंजूर पदे blocks everything
1. Set मंजूर पदे = 0 for a designation
2. Navigate to edit form → button shows "+ स्तर जोडा (मंजूर पदे भरा)" and is disabled
3. Try clicking → alert says "कृपया प्रथम मंजूर पदे भरा"
4. Direct POST → HTTP 409

Test Case 3: Reducing मंजूर पदे after levels exist
1. Have 3 levels with मंजूर पदे = 3
2. Try to change मंजूर पदे field to 2 on the form page → button instantly shows "3/2" and disables
3. Submit the form → rejected with "3 स्तर आधीच आहेत, प्रथम स्तर हटवा"
4. Try inline update on list page with SanctionedPostsCurr=2 → rejected (400)

Test Case 4: Delete then reduce
1. Have 3 levels with मंजूर पदे = 3
2. Delete 1 level → button shows "2/3" and re-enables
3. Now change मंजूर पदे to 2 → succeeds (2 ≤ 2)
4. Button shows "2/2" and disables

Test Case 5: Live मंजूर पदे changes
1. Have 0 levels, मंजूर पदे = 0 → button disabled
2. Type "3" in मंजूर पदे field → button instantly shows "0/3" and enables
3. Add 2 levels → button shows "2/3"
4. Change मंजूर पदे to 1 → button instantly shows "2/1" and disables

Test Case 6: Same test on s20530019 (monolithic)
Repeat all above for the monolithic subschema to confirm the pattern works identically.

Automated Test (Proposed — to write during execution)
Create a test script at tests/test_post_level_limit.py that:

1. Creates a BudgetPostDetails record with sanctioned_posts_curr = 2
2. POSTs 2 levels via API → both succeed (201)
3. POSTs a 3rd level → fails (409)
4. DELETEs one level → POSTs again → succeeds (201)
5. Creates a record with sanctioned_posts_curr = 0 → POST level fails (409)
6. Creates a record with sanctioned_posts_curr = 2, adds 2 levels → tries to update sanctioned_posts_curr to 1 → fails (400)
7. Deletes 1 level → update sanctioned_posts_curr to 1 → succeeds