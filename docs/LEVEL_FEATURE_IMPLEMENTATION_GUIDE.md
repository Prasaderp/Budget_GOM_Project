# LEVEL Feature Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the **LEVEL** feature (multi-level data entry for budget posts) in subschemes of scheme 2053. The LEVEL feature allows detailed breakdown of salary components at individual levels, with automatic aggregation to the main budget post record.

## ⚠️ Critical Implementation Notes

1. **Template Path Variables**: Always use FULL paths in templates. Do NOT concatenate paths.
2. **Pay Matrix API**: The `pay_matrix_api_path` must end with `/api/pay-matrix` (not just `/api`).
3. **Post Levels API**: The `api_base_path` must end with `/api/post-levels` (full path).
4. **Template Safety**: Even if backend passes variables, set them explicitly in template to ensure correctness.

## Architecture

The LEVEL feature follows a modular architecture:

- **Common Module**: `src/schemes/common/post_levels/` - Contains reusable components
- **Subscheme-Specific**: Each subscheme has its own API controller and UI integration
- **Factory Pattern**: `create_post_levels_router()` generates subscheme-specific API routers

## Prerequisites

Before implementing, ensure you understand:
1. The subscheme's `budget_post_details` table structure
2. The subscheme's access control patterns (district/taluka validation)
3. The subscheme's configuration (`config.py`)

## Implementation Steps

### Step 1: Create API Controller

**File**: `src/schemes/s2053/subs/s{SUBSCHEME_CODE}/api_budget_details.py`

**Template**:
```python
"""API controller for budget post details - sub-scheme {SUBSCHEME_CODE}"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.models import PayMatrix
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from src.utils_timing import check_data_filling_allowed
from src.schemes.common.post_levels.api_router import create_post_levels_router
from .models import BudgetPostDetails
from .config import (
    SCHEME_CONFIG, SUB_SCHEME_CODE, MARATHI_TO_ENGLISH_DESIGNATIONS
)
from .helpers import (
    check_edit_permission_for_scheme, invalidate_scheme_cache, log_audit_async,
    get_request_info, validate_numeric_inputs, validate_access_control
)

router = APIRouter(
    prefix="/ui/s{SUBSCHEME_CODE}/budget-post-details",
    tags=["API - Budget Post Details {SUBSCHEME_CODE}"],
    include_in_schema=False
)

# Access validator for post levels
def validate_budget_post_access(request: Request, budget_post, db: Session):
    """Validate user access to budget post based on district/taluka"""
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    return validate_access_control(budget_post.district, auth_level, auth_unit, db)

# Include post levels router for multi-level data entry
post_levels_router = create_post_levels_router(
    sub_scheme_code=SUB_SCHEME_CODE,
    budget_post_model=BudgetPostDetails,
    table_name="budget_post_details_{SUBSCHEME_CODE}",
    scheme_code=SCHEME_CONFIG.code,
    access_validator=validate_budget_post_access,
    prefix="/api/post-levels"
)
router.include_router(post_levels_router)

_BUDGET_COLUMNS = [
    'sanctioned_posts_2024_25', 'sanctioned_posts_2025_26', 'special_pay', 'basic_pay',
    'grade_pay', 'local_supplementary_allowance', 'vehicle_allowance',
    'washing_allowance', 'cash_allowance', 'footwear_allowance_other', 'hra_rate'
]

def _format_basic_pay(val):
    """Format basic pay value for display"""
    if val is None:
        return 0
    fval = float(val)
    if fval >= 1000:
        fval = round(round(fval / 100) / 10, 1)
    return int(fval) if fval == int(fval) else fval

def translate_marathi_designation_search(search_term: str) -> str:
    """Translate Marathi designation search to English"""
    if not search_term:
        return search_term
    search_lower = search_term.lower().strip()
    for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
        if m_term.lower() in search_lower or search_lower in m_term.lower():
            return e_desig
    for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
        m_words = m_term.lower().split()
        s_words = search_lower.split()
        for mw in m_words:
            for sw in s_words:
                if len(sw) >= 3 and (mw.startswith(sw) or sw.startswith(mw)):
                    return e_desig
    return search_term

@router.get("/api/pay-matrix/stages", response_class=JSONResponse)
async def api_get_pay_matrix_stages(db: Session = Depends(get_db)):
    """Get all pay matrix stages"""
    stages = db.query(PayMatrix.stage).distinct().order_by(PayMatrix.stage).all()
    sorted_stages = sorted([s[0] for s in stages], key=lambda x: int(x.split('-')[1]))
    return JSONResponse({"stages": sorted_stages})

@router.get("/api/pay-matrix/levels/{stage}", response_class=JSONResponse)
async def api_get_pay_matrix_levels(stage: str, db: Session = Depends(get_db)):
    """Get pay matrix levels for a stage"""
    levels = db.query(PayMatrix.level).filter(PayMatrix.stage == stage).order_by(PayMatrix.level).all()
    return JSONResponse({"levels": [l[0] for l in levels]})

@router.get("/api/pay-matrix/basic-pay", response_class=JSONResponse)
async def api_get_pay_matrix_basic_pay(request: Request, stage: str = Query(...), level: int = Query(...), db: Session = Depends(get_db)):
    """Get basic pay for stage and level, respecting salary mode"""
    from src.utils_salary_mode import get_salary_mode
    fiscal_year = get_fiscal_year_from_request(request, db)
    salary_mode = get_salary_mode(db, fiscal_year)
    record = db.query(PayMatrix).filter(PayMatrix.stage == stage, PayMatrix.level == level).first()
    if not record:
        return JSONResponse({"found": False, "basic_pay": 0})
    multiplier = 12 if salary_mode == 'annual' else 1
    basic_pay_full = record.basic_pay * multiplier
    basic_pay_thousands = basic_pay_full // 1000
    return JSONResponse({"found": True, "basic_pay": basic_pay_thousands, "basic_pay_full": basic_pay_full, "salary_mode": salary_mode})

@router.get("/api/designations", response_class=JSONResponse)
async def api_get_designations(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    db: Session = Depends(get_db)
):
    """Get distinct designations matching filters"""
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(BudgetPostDetails.designation).distinct().filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(BudgetPostDetails.district == district)
    if category:
        query = query.filter(BudgetPostDetails.category == category)
    if cls:
        query = query.filter(BudgetPostDetails.class_type == cls)
    designations = [row[0] for row in query.order_by(BudgetPostDetails.designation).all()]
    return JSONResponse({"designations": designations})

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(
    request: Request,
    district: str = Query(...),
    category: str = Query(...),
    cls: str = Query(..., alias="class"),
    designation: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get record data for a specific budget post detail"""
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.fiscal_year == fiscal_year,
        BudgetPostDetails.sub_scheme_code == sub_scheme,
        BudgetPostDetails.district == district,
        BudgetPostDetails.category == category,
        BudgetPostDetails.class_type == cls,
        BudgetPostDetails.designation == designation
    ).first()
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True, "id": record.id,
        "sanctioned_posts_2024_25": record.sanctioned_posts_2024_25 or 0,
        "sanctioned_posts_2025_26": record.sanctioned_posts_2025_26 or 0,
        "special_pay": record.special_pay or 0,
        "basic_pay": _format_basic_pay(record.basic_pay),
        "grade_pay": record.grade_pay or 0,
        "local_supplementary_allowance": record.local_supplementary_allowance or 0,
        "vehicle_allowance": record.vehicle_allowance or 0,
        "washing_allowance": record.washing_allowance or 0,
        "cash_allowance": record.cash_allowance or 0,
        "footwear_allowance_other": record.footwear_allowance_other or 0,
        "hra_rate": record.hra_rate or 'X'
    })

@router.post("/api/update-inline", response_class=JSONResponse)
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    SanctionedPosts202425: int = Form(0),
    SanctionedPosts202526: int = Form(0),
    SpecialPay: int = Form(0),
    BasicPay: float = Form(0),
    GradePay: int = Form(0),
    LocalSupplemetoryAllowance: int = Form(0),
    VehicleAllowance: int = Form(0),
    WashingAllowance: int = Form(0),
    CashAllowance: int = Form(0),
    FootWareAllowanceOther: int = Form(0),
    HraRate: str = Form('X')
):
    """Update budget post detail inline"""
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(BudgetPostDetails).filter(
        BudgetPostDetails.id == id,
        BudgetPostDetails.sub_scheme_code == sub_scheme
    ).first()
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    allowed, error_msg = validate_access_control(record.district, auth_level, auth_unit, db)
    if not allowed:
        return JSONResponse({"success": False, "message": error_msg}, status_code=403)
    
    vals_int = [
        SanctionedPosts202425, SanctionedPosts202526, SpecialPay, GradePay,
        LocalSupplemetoryAllowance, VehicleAllowance, WashingAllowance,
        CashAllowance, FootWareAllowanceOther
    ]
    is_valid, error_msg = validate_numeric_inputs(*vals_int, BasicPay)
    if not is_valid:
        return JSONResponse({"success": False, "message": error_msg}, status_code=400)
    
    if HraRate not in ('X', 'Y', 'Z'):
        HraRate = 'X'
    
    old_values = {k: getattr(record, k) for k in _BUDGET_COLUMNS}
    
    record.sanctioned_posts_2024_25 = SanctionedPosts202425
    record.sanctioned_posts_2025_26 = SanctionedPosts202526
    record.special_pay = SpecialPay
    record.basic_pay = BasicPay
    record.grade_pay = GradePay
    record.local_supplementary_allowance = LocalSupplemetoryAllowance
    record.vehicle_allowance = VehicleAllowance
    record.washing_allowance = WashingAllowance
    record.cash_allowance = CashAllowance
    record.footwear_allowance_other = FootWareAllowanceOther
    record.hra_rate = HraRate
    
    db.commit()
    
    invalidate_scheme_cache(record.district)
    
    new_values = {k: getattr(record, k) for k in _BUDGET_COLUMNS}
    req_info = get_request_info(request)
    log_audit_async("budget_post_details", id, auth_user, old_values, new_values, req_info)
    
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})
```

**Replacements**:
- `{SUBSCHEME_CODE}` → Actual subscheme code (e.g., `20530162`, `20530387`)
- `{table_name}` → Actual table name (e.g., `budget_post_details_20530162`)

### Step 2: Refactor UI Controller

**File**: `src/schemes/s2053/subs/s{SUBSCHEME_CODE}/ui_budget_details.py`

**Changes Required**:

1. **Remove API endpoints** (lines that start with `@router.get("/api/...")` or `@router.post("/api/...")`):
   - `/api/pay-matrix/stages`
   - `/api/pay-matrix/levels/{stage}`
   - `/api/pay-matrix/basic-pay`
   - `/api/designations`
   - `/api/record-data`
   - `/api/update-inline`

2. **Remove unused imports**:
   - `from src.models import PayMatrix` (if no longer used)

3. **Update form route** (`@router.get("/{id}/edit")`):
   - Add template variables (OPTIONAL - template sets them explicitly for safety):
     ```python
     "api_base_path": "/ui/s{SUBSCHEME_CODE}/budget-post-details/api/post-levels",
     "pay_matrix_api_path": "/ui/s{SUBSCHEME_CODE}/budget-post-details/api/pay-matrix",
     "sub_scheme_code": SUB_SCHEME_CODE,
     "table_name": "budget_post_details_{SUBSCHEME_CODE}"
     ```
   - **Note**: Even if passed from backend, template should set them explicitly to ensure they're correct
   - Add no-cache headers:
     ```python
     response = templates.TemplateResponse(...)
     response.headers.update(get_no_cache_headers())
     return response
     ```

4. **Update imports**:
   - Add `SUB_SCHEME_CODE` to imports from `.config`

### Step 3: Update Form Template

**File**: `templates/schemes/s2053/subs/s{SUBSCHEME_CODE}/budget_post_details_form.html`

**Changes Required**:

1. **Add fiscal year change detection script** (at the top, after error block):
   ```html
   <script>
   // Fiscal year change detection and redirect
   (function() {
       const initialFiscalYear = '{{ request.cookies.get("fiscal_year", "2025-26") }}';
       
       function getCookie(name) {
           const value = `; ${document.cookie}`;
           const parts = value.split(`; ${name}=`);
           if (parts.length === 2) return parts.pop().split(';').shift();
           return null;
       }
       
       document.addEventListener('visibilitychange', function() {
           if (!document.hidden) {
               const currentFY = getCookie('fiscal_year');
               if (currentFY && currentFY !== initialFiscalYear) {
                   console.log('Fiscal year changed, redirecting to list...');
                   window.location.href = '/ui/s{SUBSCHEME_CODE}/budget-post-details';
               }
           }
       });
       
       setInterval(function() {
           const currentFY = getCookie('fiscal_year');
           if (currentFY && currentFY !== initialFiscalYear) {
               console.log('Fiscal year changed, redirecting to list...');
               window.location.href = '/ui/s{SUBSCHEME_CODE}/budget-post-details';
           }
       }, 2000);
   })();
   </script>
   ```

2. **Update salary section header**:
   ```html
   <div style="grid-column:1/-1;">
       <h3 style="margin:0 0 8px 0;font-size:16px;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:0.03em;">वेतन आणि भत्ते (एकूण)</h3>
       <p style="margin:0;font-size:13px;color:var(--text-muted);">
           <strong>सूचना:</strong> खालील फील्ड स्वयंचलितपणे स्तर डेटा वरून गणना केले जातात. कृपया खाली स्तर व्यवस्थापन विभागात डेटा प्रविष्ट करा.
       </p>
   </div>
   ```

3. **Make salary fields readonly** (add `readonly` attribute and `style="background:var(--muted);"`):
   - `SpecialPay`
   - `BasicPay` (also change `step="1"` to `step="0.1"` if needed)
   - `GradePay`
   - `LocalSupplemetoryAllowance`
   - `VehicleAllowance`
   - `WashingAllowance`
   - `CashAllowance`
   - `FootWareAllowanceOther`

4. **Update DA and HRA fields** (make them readonly with calculated values):
   ```html
   <div class="form-group">
       <label for="Da64">महागाई भत्ता 64%</label>
       <input type="number" id="Da64" readonly value="{{ ((detail.basic_pay|float + detail.grade_pay|float) * 0.64)|round|int if detail else 0 }}" style="background:var(--muted);">
   </div>
   <div class="form-group">
       <label for="Hra">घर भाडे भत्ता (HRA)</label>
       <input type="number" id="Hra" readonly value="{{ ((detail.basic_pay|float + detail.grade_pay|float) * (0.30 if detail.hra_rate == 'X' else (0.20 if detail.hra_rate == 'Y' else 0.10)))|round|int if detail else 0 }}" style="background:var(--muted);">
   </div>
   <input type="hidden" name="HraRate" value="{{ detail.hra_rate if detail else 'X' }}">
   ```

5. **Remove old JavaScript** (remove all `<script>` blocks related to pay matrix, allowances, etc.)

6. **Add levels section** (before the submit button):
   ```html
   {# Include Post Levels Management Section #}
   {% if detail and detail.id %}
   {% set api_base_path = '/ui/s{SUBSCHEME_CODE}/budget-post-details/api/post-levels' %}
   {% set pay_matrix_api_path = '/ui/s{SUBSCHEME_CODE}/budget-post-details/api/pay-matrix' %}
   {% set sub_scheme_code = '{SUBSCHEME_CODE}' %}
   {% set table_name = 'budget_post_details_{SUBSCHEME_CODE}' %}
   {% include "schemes/common/post_levels/_levels_section.html" %}
   {% endif %}
   ```
   
   **CRITICAL**: Use FULL paths, not concatenation. The paths must be:
   - `api_base_path`: Full path ending with `/api/post-levels`
   - `pay_matrix_api_path`: Full path ending with `/api/pay-matrix`
   - `sub_scheme_code`: The subscheme code as string (e.g., `'20530387'`)
   - `table_name`: The table name (e.g., `'budget_post_details_20530387'`)

7. **Replace submit button** with "परत जा" link:
   ```html
   <div style="display:flex;gap:16px;justify-content:flex-start;padding-top:8px;">
       <a href="/ui/s{SUBSCHEME_CODE}/budget-post-details" style="display:inline-flex;align-items:center;justify-content:center;padding:16px 40px;background:var(--muted);color:var(--text);text-decoration:none;border-radius:var(--radius-lg);font-size:16px;font-weight:700;border:1px solid var(--border);transition:var(--transition);box-shadow:var(--shadow-sm);">परत जा</a>
   </div>
   ```

### Step 4: Update Router

**File**: `src/schemes/s2053/subs/s{SUBSCHEME_CODE}/router_ui.py`

**Changes Required**:

1. **Add import**:
   ```python
   from .api_budget_details import router as budget_details_api_router
   ```

2. **Combine routers** (before creating main router):
   ```python
   # Combine budget details UI and API routers
   budget_details_router = APIRouter()
   budget_details_router.include_router(budget_details_ui_router)
   budget_details_router.include_router(budget_details_api_router)
   ```

3. **Update main router** to use combined router (if needed)

## Security Considerations

### Data Isolation

The implementation ensures strict isolation:

1. **Subscheme Isolation**: Each subscheme uses its own `sub_scheme_code` and `table_name`
2. **Fiscal Year Isolation**: All queries filter by `fiscal_year`
3. **Access Control**: District/taluka validators prevent unauthorized access
4. **Defense in Depth**: Multiple validation layers at API, Service, and Repository levels

### Validation Points

- **API Layer**: Validates `sub_scheme_code`, `table_name`, `fiscal_year` in all requests
- **Service Layer**: Validates budget post belongs to correct subscheme/fiscal year
- **Repository Layer**: All queries filter by `table_name`, `budget_post_id`, `sub_scheme_code`, `fiscal_year`

## Testing Checklist

After implementation, verify:

- [ ] API endpoints are accessible at correct paths
- [ ] Form loads with readonly salary fields
- [ ] Levels section appears when editing existing record
- [ ] Can add/edit/delete levels
- [ ] Aggregates update main form fields correctly
- [ ] Access control works (district/taluka restrictions)
- [ ] Fiscal year isolation works
- [ ] No data leaks between subschemes
- [ ] Cache invalidation works
- [ ] Audit logging works

## Common Issues

### Issue: Pay Matrix dropdown not showing / Levels section not working

**CRITICAL BUG**: This happens when template variables are not set correctly.

**Root Cause**: 
- Using incomplete paths (e.g., `/ui/s20530387/budget-post-details` instead of `/ui/s20530387/budget-post-details/api/post-levels`)
- Trying to concatenate paths in template instead of using full paths
- Missing `pay_matrix_api_path` or incorrect path

**Solution**: 
1. In template, set FULL paths explicitly:
   ```jinja
   {% set api_base_path = '/ui/s{SUBSCHEME_CODE}/budget-post-details/api/post-levels' %}
   {% set pay_matrix_api_path = '/ui/s{SUBSCHEME_CODE}/budget-post-details/api/pay-matrix' %}
   ```
2. Do NOT concatenate: `api_base_path + '/api/post-levels'` ❌
3. Use full paths: `'/ui/s20530387/budget-post-details/api/post-levels'` ✅
4. Verify paths match your API router prefix exactly

### Issue: Template variables not found

**Solution**: Ensure `api_base_path`, `pay_matrix_api_path`, `sub_scheme_code`, and `table_name` are set in the template (even if passed from backend, set them explicitly for safety).

### Issue: Levels section not appearing

**Solution**: Check that `detail.id` exists and the include path is correct.

### Issue: Salary fields not updating

**Solution**: Verify `PostLevelsManager` is initialized with correct `apiBasePath` and `budgetPostId`. Check browser console for JavaScript errors.

### Issue: Access denied errors

**Solution**: Verify `validate_access_control` function matches the subscheme's access patterns.

## Reference Implementations

- **20530028**: Original implementation
- **20530162**: First replication
- **20530242**: Second replication
- **20530313**: Third replication
- **20530387**: Fourth replication

## Notes

- All salary fields in the main form become **readonly** and are populated from aggregated levels
- The submit button is **removed** - saving is handled by the `PostLevelsManager`
- Old pay matrix and allowance calculation JavaScript is **removed**
- Fiscal year change detection ensures users don't edit records from wrong fiscal year

## Support

For questions or issues, refer to:
- Common module: `src/schemes/common/post_levels/`
- Reference implementations listed above
- This documentation

