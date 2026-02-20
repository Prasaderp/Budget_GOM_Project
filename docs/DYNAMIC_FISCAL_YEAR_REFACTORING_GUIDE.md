# Dynamic Fiscal Year Refactoring Guide — s2053 Sub-Schemes

> **Purpose**: This guide documents the complete implementation pattern used to replace hardcoded fiscal year strings with dynamic `relative_years` Jinja2 expressions across the s2053 sub-schemes. Use this as a step-by-step reference when applying the same refactoring to any remaining sub-schemes.

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [The `relative_years` Object](#2-the-relative_years-object)
3. [Completion Status](#3-completion-status)
4. [Sub-Schemes Sharing s20530019 Architecture](#4-sub-schemes-sharing-s20530019-architecture)
5. [Step-by-Step Implementation Checklist](#5-step-by-step-implementation-checklist)
6. [Backend Changes — Python Files](#6-backend-changes--python-files)
7. [Frontend Changes — HTML Templates](#7-frontend-changes--html-templates)
8. [Year Format Mapping Reference](#8-year-format-mapping-reference)
9. [What NOT to Change](#9-what-not-to-change)
10. [Verification & Testing](#10-verification--testing)
11. [Common Pitfalls](#11-common-pitfalls)

---

## 1. Overview & Architecture

### Problem
Fiscal year labels like `2024-25`, `2025-2026`, `25-26` etc. were hardcoded in:
- HTML template headers, labels, chart titles
- Jinja2 display text visible to end users

When the active fiscal year changes (e.g., from `2024-25` to `2025-26`), all these labels become stale, requiring manual updates across dozens of files.

### Solution
A utility function `get_relative_fiscal_years(base_fy)` generates a dictionary of relative fiscal year labels. This dictionary (`relative_years`) is:
1. Computed in the **Python backend** from the active fiscal year
2. Passed to every **template context**
3. Referenced in **Jinja2 templates** using expressions like `{{ relative_years.fy_curr.short }}`

### Architecture Pattern
```
┌──────────────────────────────────────────────────────────────┐
│ Python Backend (ui_*.py)                                      │
│                                                                │
│   fiscal_year = get_fiscal_year_from_request(request, db)     │
│   relative_years = get_relative_fiscal_years(fiscal_year)     │
│   context["relative_years"] = relative_years                  │
│                                                                │
│   templates.TemplateResponse("template.html", context)        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ HTML/Jinja2 Template                                          │
│                                                                │
│   Before:  <th>2024-25</th>                                   │
│   After:   <th>{{ relative_years.fy_prev1.short }}</th>       │
│                                                                │
│   Before:  <label>प्रत्यक्ष खर्च 2021-2022</label>            │
│   After:   <label>प्रत्यक्ष खर्च {{ relative_years.fy_prev4.full }}</label> │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. The `relative_years` Object

**Source**: `src/utils_fiscal_year.py` → `get_relative_fiscal_years(base_fy: str) -> dict`

Given `base_fy = "2025-26"`, the function returns:

```python
{
    "fy_curr":  {"short": "2025-26",  "full": "2025-2026",  "compact": "25-26"},
    "fy_prev1": {"short": "2024-25",  "full": "2024-2025",  "compact": "24-25"},
    "fy_prev2": {"short": "2023-24",  "full": "2023-2024",  "compact": "23-24"},
    "fy_prev3": {"short": "2022-23",  "full": "2022-2023",  "compact": "22-23"},
    "fy_prev4": {"short": "2021-22",  "full": "2021-2022",  "compact": "21-22"},
    "fy_next1": {"short": "2026-27",  "full": "2026-2027",  "compact": "26-27"},
}
```

### Format Reference
| Format    | Example      | Use Case                                    |
|-----------|--------------|---------------------------------------------|
| `short`   | `2024-25`    | Standard labels, chart titles               |
| `full`    | `2024-2025`  | Formal headings, summary titles             |
| `compact` | `24-25`      | Compact table headers, inline edit labels   |

### Relative Year Mapping
| Key         | Meaning                    | Example (when base = 2025-26) |
|-------------|----------------------------|-------------------------------|
| `fy_curr`   | Current / budgeting year   | 2025-26                       |
| `fy_prev1`  | Previous year (N-1)        | 2024-25                       |
| `fy_prev2`  | Two years ago (N-2)        | 2023-24                       |
| `fy_prev3`  | Three years ago (N-3)      | 2022-23                       |
| `fy_prev4`  | Four years ago (N-4)       | 2021-22                       |
| `fy_next1`  | Next year (N+1)            | 2026-27                       |

---

## 3. Completion Status

| Sub-Scheme   | Architecture   | Status        | Notes                           |
|-------------|---------------|---------------|---------------------------------|
| `s20530028` | Micro-folder  | ✅ DONE       | Different architecture (controllers/) |
| `s20530019` | Monolithic    | ✅ DONE       | Reference implementation         |
| `s20530162` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |
| `s20530153` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |
| `s20530233` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |
| `s20530242` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |
| `s20530304` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |
| `s20530313` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |
| `s20530378` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |
| `s20530387` | Monolithic    | ⬜ PENDING    | Same arch as s20530019          |

---

## 4. Sub-Schemes Sharing s20530019 Architecture

All monolithic sub-schemes have **identical file structure**:

### Python Backend Files (in `src/schemes/s2053/subs/<SUB_SCHEME>/`)
```
ui_budget_details.py     ← Budget post details (Form D) — LIST + EDIT FORM
ui_budget_summary.py     ← Budget summary report — SUMMARY VIEW
ui_unit_expenditure.py   ← Unit expenditure (Form A) — LIST + EDIT FORM  
ui_post_status.py        ← Post status (Form C) — LIST + EDIT FORM
ui_post_expenses.py      ← Post expenses (Form B) — LIST + EDIT FORM
ui_category_info.py      ← Category-wise info (may/may not have hardcoded years)
ui_abstract.py           ← District-wise abstract (may/may not have hardcoded years)
```

### HTML Template Files (in `templates/schemes/s2053/subs/<SUB_SCHEME>/`)
```
budget_post_details_form.html   ← Edit form for budget post details
budget_post_details_list.html   ← List/summary view for budget post details
unit_expenditure_form.html      ← Edit form for unit expenditure
unit_expenditure_list.html      ← List/summary view for unit expenditure
post_status_form.html           ← Edit form for post status
post_status_list.html           ← List/summary view for post status
post_expenses_form.html         ← Edit form for post expenses
post_expenses_list.html         ← List/summary view for post expenses
category_wise_info.html         ← Category-wise info view
district_wise_abstract.html     ← Abstract view
base.html                       ← Base layout (no fiscal years)
```

---

## 5. Step-by-Step Implementation Checklist

For each sub-scheme `<CODE>` (e.g., `s20530153`), execute these steps **in order**:

### Phase 1: Identify Hardcoded Years
```bash
# Run this grep to find all hardcoded years in the sub-scheme's templates
grep -rn -E "2024-25|2025-26|2021-2022|2022-2023|2023-2024|2024-2025|2025-2026|21-22|22-23|23-24|24-25|25-26" \
  templates/schemes/s2053/subs/<CODE>/
```

### Phase 2: Backend Changes (5 files)
- [ ] `ui_budget_details.py` — import + 3 context injections
- [ ] `ui_budget_summary.py` — import + 1 context injection
- [ ] `ui_unit_expenditure.py` — import + 4 context injections
- [ ] `ui_post_status.py` — import + 1 context injection (base context)
- [ ] `ui_post_expenses.py` — import + 1 context injection (base context)

### Phase 3: Template Changes (6 files)
- [ ] `budget_post_details_form.html` — form labels
- [ ] `budget_post_details_list.html` — inline edit labels, chart titles, summary headings, table headers
- [ ] `unit_expenditure_form.html` — form labels
- [ ] `unit_expenditure_list.html` — inline edit labels, table headers, chart labels, summary headings
- [ ] `post_status_list.html` — summary heading
- [ ] `post_expenses_list.html` — summary heading

### Phase 4: Verify
- [ ] Run grep again — only data-key references should remain
- [ ] Test the app renders correctly

---

## 6. Backend Changes — Python Files

### 6.1 Import Pattern

In **every** `ui_*.py` file, find the line:
```python
from src.utils_fiscal_year import get_fiscal_year_from_request
```
Replace with:
```python
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
```

> **Note**: `ui_budget_summary.py` may also import `get_default_fiscal_year`. Just append `get_relative_fiscal_years` to the existing import list.

---

### 6.2 `ui_budget_details.py` — 3 Context Injection Points

#### Injection Point 1: List view context (edit + summary)
Find the main `context = { ... }` dict that has `"da_rate"` as the last key. Add `relative_years`:

```python
# BEFORE the context dict, add:
relative_years = get_relative_fiscal_years(fiscal_year)

# IN the context dict, add as last entry:
    "da_rate": da_rate,
    "relative_years": relative_years   # ← ADD THIS
}
```

#### Injection Point 2: Edit form (`/{id}/edit` GET handler)
Find the `templates.TemplateResponse("...budget_post_details_form.html", { ... })` call. Add `relative_years`:

```python
# BEFORE the TemplateResponse, add:
relative_years = get_relative_fiscal_years(fiscal_year)

# IN the dict, add as last entry:
    "table_name": "budget_post_details_<CODE>",
    "relative_years": relative_years    # ← ADD THIS
})
```

#### Injection Point 3: Error re-render (POST handler exception block)
Find the error `templates.TemplateResponse("...budget_post_details_form.html", { ... }, status_code=400)`. Add:

```python
    "auth_level": auth_level,
    "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))  # ← ADD THIS
}, status_code=400)
```

---

### 6.3 `ui_budget_summary.py` — 1 Context Injection Point

Find the `template_context = { ... }` dict inside `ui_budget_summary_report()`. Add `relative_years`:

```python
template_context = {
    "request": request,
    "resource_name": "...",
    "view_mode": "summary",
    "chart_data": {},
    "auth_level": auth_level,
    "da_rate": da_rate,
    "relative_years": get_relative_fiscal_years(fiscal_year),   # ← ADD THIS
    **summary_data
}
```

---

### 6.4 `ui_unit_expenditure.py` — 4 Context Injection Points

#### Injection Point 1: Summary view (`view == "summary"` block)
```python
if view == "summary":
    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)    # ← ADD THIS
    ...
    context.update({
        ...
        "internal_keys_ordered": data["internal_keys_ordered"],
        "relative_years": relative_years    # ← ADD THIS
    })
```

#### Injection Point 2: Edit list view (`view == "edit"` block)
```python
elif view == "edit":
    fiscal_year = get_fiscal_year_from_request(request, db)
    relative_years = get_relative_fiscal_years(fiscal_year)    # ← ADD THIS
    ...
    context.update({
        ...
        "can_edit": can_edit,
        "relative_years": relative_years    # ← ADD THIS
    })
```

#### Injection Point 3: Edit form GET handler
```python
fiscal_year = get_fiscal_year_from_request(request, db)
relative_years = get_relative_fiscal_years(fiscal_year)    # ← ADD THIS
return templates.TemplateResponse("...unit_expenditure_form.html", {
    ...
    "auth_level": auth_level,
    "relative_years": relative_years    # ← ADD THIS
})
```

#### Injection Point 4: Error re-render POST handler
```python
    "auth_level": auth_level,
    "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))  # ← ADD
}, status_code=400)
```

---

### 6.5 `ui_post_status.py` — 1 Context Injection Point (Base Context)

Find the base `context = { ... }` dict built before the `if view == "summary"` branch. Add:

```python
context = {
    ...
    "statuses_mr": STATUSES_MR,
    "auth_level": auth_level,
    "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))  # ← ADD
}
```

This single injection covers BOTH summary and edit views since both use the same base context.

---

### 6.6 `ui_post_expenses.py` — 1 Context Injection Point (Base Context)

Find the base `context = { ... }` dict built before the `if view == "summary"` branch. Add:

```python
context = {
    ...
    "auth_level": auth_level,
    "auth_unit": auth_unit,
    "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))  # ← ADD
}
```

---

## 7. Frontend Changes — HTML Templates

### 7.1 `budget_post_details_form.html` — Form Labels (2 replacements)

| Find (hardcoded)                | Replace with (dynamic)                                    |
|--------------------------------|-----------------------------------------------------------|
| `मंजूर पदे 2024-25`            | `मंजूर पदे {{ relative_years.fy_prev1.short }}`           |
| `मंजूर पदे 2025-26`            | `मंजूर पदे {{ relative_years.fy_curr.short }}`            |

---

### 7.2 `budget_post_details_list.html` — Multiple Sections (~8 replacements)

#### Inline Edit Labels
| Find                    | Replace                                              |
|------------------------|------------------------------------------------------|
| `मंजूर पदे 2024-25`    | `मंजूर पदे {{ relative_years.fy_prev1.short }}`      |
| `मंजूर पदे 2025-26`    | `मंजूर पदे {{ relative_years.fy_curr.short }}`       |

#### Chart Titles
| Find                                                   | Replace                                                                      |
|--------------------------------------------------------|------------------------------------------------------------------------------|
| `{{ districts_mr.get(...) }} - मंजूर पदे 2025-26`      | `{{ districts_mr.get(...) }} - मंजूर पदे {{ relative_years.fy_curr.short }}` |
| `जिल्ह्यानिहाय मंजूर पदे 2025-26`                      | `जिल्ह्यानिहाय मंजूर पदे {{ relative_years.fy_curr.short }}`                |

#### Summary Heading
| Find                                     | Replace                                                                        |
|------------------------------------------|--------------------------------------------------------------------------------|
| `अर्थसंकल्पीय अंदाजपत्रक सन 2025-2026` | `अर्थसंकल्पीय अंदाजपत्रक सन {{ relative_years.fy_curr.full\|default('') }}`   |

#### Summary Table Headers (3 table sections: permanent, temporary, class-wise)
| Find            | Replace                                       |
|----------------|-----------------------------------------------|
| `<th>2024-25</th>` | `<th>{{ relative_years.fy_prev1.short }}</th>` |
| `<th>2025-26</th>` | `<th>{{ relative_years.fy_curr.short }}</th>`  |
| `<th>2023-24</th>` | `<th>{{ relative_years.fy_prev2.short }}</th>` |

---

### 7.3 `unit_expenditure_form.html` — Form Labels (6 replacements)

| Find                               | Replace                                                        |
|------------------------------------|------------------------------------------------------------|
| `प्रत्यक्ष खर्च 2021-2022`          | `प्रत्यक्ष खर्च {{ relative_years.fy_prev4.full }}`         |
| `प्रत्यक्ष खर्च 2022-2023`          | `प्रत्यक्ष खर्च {{ relative_years.fy_prev3.full }}`         |
| `प्रत्यक्ष खर्च 2023-2024`          | `प्रत्यक्ष खर्च {{ relative_years.fy_prev2.full }}`         |
| `अर्थसंकल्पीय अंदाज 2024-2025`     | `अर्थसंकल्पीय अंदाज {{ relative_years.fy_prev1.full }}`     |
| `सुधारित अंदाज 2024-2025`           | `सुधारित अंदाज {{ relative_years.fy_prev1.full }}`           |
| `अर्थसंकल्पीय अंदाज 2025-26` (h3)  | `अर्थसंकल्पीय अंदाज {{ relative_years.fy_curr.short }}` (h3) |

---

### 7.4 `unit_expenditure_list.html` — Multiple Sections (~21 replacements)

#### Inline Edit Labels (9 labels)
| Find                           | Replace                                                            |
|-------------------------------|-------------------------------------------------------------------|
| `प्रत्यक्ष खर्च 2021-22`       | `प्रत्यक्ष खर्च {{ relative_years.fy_prev4.short }}`              |
| `प्रत्यक्ष खर्च 2022-23`       | `प्रत्यक्ष खर्च {{ relative_years.fy_prev3.short }}`              |
| `प्रत्यक्ष खर्च 2023-24`       | `प्रत्यक्ष खर्च {{ relative_years.fy_prev2.short }}`              |
| `अर्थसंकल्पीय अंदाज 24-25`    | `अर्थसंकल्पीय अंदाज {{ relative_years.fy_prev1.compact }}`       |
| `संभाव्य 24-25`               | `संभाव्य {{ relative_years.fy_prev1.compact }}`                   |
| `अंदाज अधिकारी 25-26`         | `अंदाज अधिकारी {{ relative_years.fy_curr.compact }}`              |
| `नियंत्रण अधिकारी 25-26`      | `नियंत्रण अधिकारी {{ relative_years.fy_curr.compact }}`           |
| `प्रशासकीय विभाग 25-26`       | `प्रशासकीय विभाग {{ relative_years.fy_curr.compact }}`            |
| `वित्त विभाग 25-26`           | `वित्त विभाग {{ relative_years.fy_curr.compact }}`                |

#### Edit Table Headers (3 column headers)
| Find                          | Replace                                                            |
|------------------------------|-------------------------------------------------------------------|
| `प्रत्यक्ष खर्च 22-23`       | `प्रत्यक्ष खर्च {{ relative_years.fy_prev3.compact }}`            |
| `प्रत्यक्ष खर्च 23-24`       | `प्रत्यक्ष खर्च {{ relative_years.fy_prev2.compact }}`            |
| `अर्थसंकल्पीय अंदाज 24-25`   | `अर्थसंकल्पीय अंदाज {{ relative_years.fy_prev1.compact }}`       |

#### Chart Titles
| Find                                               | Replace                                                                                    |
|----------------------------------------------------|---------------------------------------------------------------------------------------------|
| `{{ ... }} - बजेट वितरण 2024-25`                    | `{{ ... }} - बजेट वितरण {{ relative_years.fy_prev1.short }}`                                |
| `Budget Distribution 2024-25`                       | `Budget Distribution {{ relative_years.fy_prev1.short }}`                                   |
| `Budget Estimates 2025-26`                          | `Budget Estimates {{ relative_years.fy_curr.short }}`                                       |

#### Summary Section Heading
| Find                                     | Replace                                                                        |
|------------------------------------------|--------------------------------------------------------------------------------|
| `अर्थसंकल्पीय अंदाजपत्रक सन 2025-2026` | `अर्थसंकल्पीय अंदाजपत्रक सन {{ relative_years.fy_curr.full\|default('') }}`   |

#### Summary Table Headers (6 headers in `<thead>`)
| Find                             | Replace                                                    |
|---------------------------------|------------------------------------------------------------|
| `अर्थसंकल्पीय अंदाज 2024-2025` (rowspan) | `अर्थसंकल्पीय अंदाज {{ relative_years.fy_prev1.full }}`  |
| `सुधारीत अंदाज 2024-2025` (rowspan)      | `सुधारीत अंदाज {{ relative_years.fy_prev1.full }}`        |
| `अर्थसंकल्पीय अंदाज 2025-2026` (colspan) | `अर्थसंकल्पीय अंदाज {{ relative_years.fy_curr.full }}`   |
| `<th>2021-2022</th>`                     | `<th>{{ relative_years.fy_prev4.full }}</th>`              |
| `<th>2022-2023</th>`                     | `<th>{{ relative_years.fy_prev3.full }}</th>`              |
| `<th>2023-2024</th>`                     | `<th>{{ relative_years.fy_prev2.full }}</th>`              |

#### Chart.js Dataset Labels (5 labels in `<script>`)
| Find                    | Replace                                               |
|------------------------|-------------------------------------------------------|
| `label: '2021-22',`    | `label: '{{ relative_years.fy_prev4.short }}',`       |
| `label: '2022-23',`    | `label: '{{ relative_years.fy_prev3.short }}',`       |
| `label: '2023-24',`    | `label: '{{ relative_years.fy_prev2.short }}',`       |
| `label: 'Budget 2024-25',`   | `label: 'Budget {{ relative_years.fy_prev1.short }}',`  |
| `label: 'Forecast 2024-25',` | `label: 'Forecast {{ relative_years.fy_prev1.short }}',` |

---

### 7.5 `post_status_list.html` — Summary Heading (1 replacement)

| Find                                     | Replace                                                                      |
|------------------------------------------|------------------------------------------------------------------------------|
| `अर्थसंकल्पीय अंदाजपत्रक सन 2025-2026` | `अर्थसंकल्पीय अंदाजपत्रक सन {{ relative_years.fy_curr.full\|default('') }}` |

---

### 7.6 `post_expenses_list.html` — Summary Heading (1 replacement)

| Find                                     | Replace                                                                      |
|------------------------------------------|------------------------------------------------------------------------------|
| `अर्थसंकल्पीय अंदाजपत्रक सन 2025-2026` | `अर्थसंकल्पीय अंदाजपत्रक सन {{ relative_years.fy_curr.full\|default('') }}` |

---

## 8. Year Format Mapping Reference

When you encounter a hardcoded year, use this mapping to decide which `relative_years` key and format to use:

### By Hardcoded Value (when base fiscal year = 2025-26)
| Hardcoded String | → Key          | → Format   | → Jinja2 Expression                        |
|-----------------|----------------|------------|-------------------------------------------|
| `2021-22`       | `fy_prev4`     | `short`    | `{{ relative_years.fy_prev4.short }}`     |
| `2021-2022`     | `fy_prev4`     | `full`     | `{{ relative_years.fy_prev4.full }}`      |
| `21-22`         | `fy_prev4`     | `compact`  | `{{ relative_years.fy_prev4.compact }}`   |
| `2022-23`       | `fy_prev3`     | `short`    | `{{ relative_years.fy_prev3.short }}`     |
| `2022-2023`     | `fy_prev3`     | `full`     | `{{ relative_years.fy_prev3.full }}`      |
| `22-23`         | `fy_prev3`     | `compact`  | `{{ relative_years.fy_prev3.compact }}`   |
| `2023-24`       | `fy_prev2`     | `short`    | `{{ relative_years.fy_prev2.short }}`     |
| `2023-2024`     | `fy_prev2`     | `full`     | `{{ relative_years.fy_prev2.full }}`      |
| `23-24`         | `fy_prev2`     | `compact`  | `{{ relative_years.fy_prev2.compact }}`   |
| `2024-25`       | `fy_prev1`     | `short`    | `{{ relative_years.fy_prev1.short }}`     |
| `2024-2025`     | `fy_prev1`     | `full`     | `{{ relative_years.fy_prev1.full }}`      |
| `24-25`         | `fy_prev1`     | `compact`  | `{{ relative_years.fy_prev1.compact }}`   |
| `2025-26`       | `fy_curr`      | `short`    | `{{ relative_years.fy_curr.short }}`      |
| `2025-2026`     | `fy_curr`      | `full`     | `{{ relative_years.fy_curr.full }}`       |
| `25-26`         | `fy_curr`      | `compact`  | `{{ relative_years.fy_curr.compact }}`    |

### Quick Decision Rule
1. **Count the position** from the current budgeting year (2025-26):
   - Same year → `fy_curr`
   - 1 year back → `fy_prev1`
   - 2 years back → `fy_prev2`
   - 3 years back → `fy_prev3`
   - 4 years back → `fy_prev4`
2. **Match the format** of the original string:
   - `YYYY-YY` (e.g., `2024-25`) → `.short`
   - `YYYY-YYYY` (e.g., `2024-2025`) → `.full`
   - `YY-YY` (e.g., `24-25`) → `.compact`

---

## 9. What NOT to Change

### ❌ Dictionary Key Lookups (Data Access)
Lines like these reference backend data dictionary keys — NOT display text:
```html
<!-- DO NOT CHANGE THESE — they are data keys, not display labels -->
{{ item.get('Approved Posts 2024-25', 0) }}
{{ permanent_totals_render.get('Approved Posts 2025-26', 0) }}
{{ row.get('Approved Posts 2024-25', 0) }}
```
These keys are defined in `_process_budget_query_results()` in Python and match database column mappings. Changing them breaks data access.

### ❌ HTML Input Names / IDs
```html
<!-- DO NOT CHANGE — these are form field identifiers -->
<input name="SanctionedPosts202425" id="SanctionedPosts202425" ...>
<input name="Budget202526EstimatingOfficer" ...>
```

### ❌ JavaScript Variable Names
```javascript
// DO NOT CHANGE — these are variable/property names
chartData.exp_2021_22
chartData.budget_2024_25
```

### ❌ Python Internal Column Keys
```python
# DO NOT CHANGE — these are internal data processing keys
internal_col_keys = [
    "Approved Posts 2024-25", "Approved Posts 2025-26", ...
]
```

### ❌ Cookie Fallback Defaults
```javascript
// DO NOT CHANGE — this is a JS fallback value
const initialFiscalYear = '{{ request.cookies.get("fiscal_year", "2025-26") }}';
```

### Rule of Thumb
> **Change only text that is VISIBLE to the end user** — labels, headers, chart titles, headings.
> **Never change** identifiers, keys, variable names, or form field names.

---

## 10. Verification & Testing

### Step 1: Grep for Remaining Hardcoded Years
After completing changes, run:
```bash
grep -rn -E "2024-25|2025-26|2021-2022|2022-2023|2023-2024|2024-2025|2025-2026" \
  templates/schemes/s2053/subs/<CODE>/
```

**Expected**: Only data-key lookups (`item.get(...)`, `totals_render.get(...)`) and form field names should remain.

### Step 2: Check for Template Rendering Errors
1. Start the dev server: `uvicorn main:app --reload`
2. Navigate to each view:
   - `http://localhost:8000/ui/<CODE>/budget-post-details?view=edit`
   - `http://localhost:8000/ui/<CODE>/budget-post-details?view=summary`
   - `http://localhost:8000/ui/<CODE>/unit-expenditure?view=edit`
   - `http://localhost:8000/ui/<CODE>/unit-expenditure?view=summary`
   - `http://localhost:8000/ui/<CODE>/post-status?view=summary`
   - `http://localhost:8000/ui/<CODE>/post-expenses?view=summary`
3. Open an edit form for each feature
4. Verify all year labels render correctly (not as empty or `{{ ... }}`)

### Step 3: Verify Downloads
Test Excel downloads from each summary view to confirm they still work.

---

## 11. Common Pitfalls

### Pitfall 1: Missing `relative_years` in Error Re-render
If you forget to pass `relative_years` in the error `TemplateResponse` (POST handler `except` block), the form will crash when an update fails. Always add:
```python
"relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
```

### Pitfall 2: Using Wrong Format
- Table headers that use `22-23` format → use `.compact` not `.short`
- Summary headings that use `2025-2026` format → use `.full` not `.short`
- Chart labels that use `2024-25` format → use `.short` not `.compact`

### Pitfall 3: Forgetting the `|default('')` Filter
For summary headings, always use the safe filter:
```html
{{ relative_years.fy_curr.full|default('') }}
```
This prevents template errors if `relative_years` is somehow empty.

### Pitfall 4: Breaking Chart.js Labels
When replacing labels inside JavaScript `<script>` blocks, the Jinja2 expression must be inside single quotes:
```javascript
// CORRECT
label: '{{ relative_years.fy_prev4.short }}',

// WRONG — will cause JS syntax error
label: {{ relative_years.fy_prev4.short }},
```

### Pitfall 5: Pre-existing Lint Errors
The codebase has pre-existing Pyre2 type annotation errors across all `ui_budget_summary.py` files (related to `defaultdict` usage). These are **NOT caused by our changes** and should be ignored during this refactoring.

---

## Quick-Start Template

Copy-paste this import line into any `ui_*.py`:
```python
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
```

Copy-paste this into any context dict:
```python
"relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
```

Or if `fiscal_year` is already available:
```python
"relative_years": get_relative_fiscal_years(fiscal_year)
```

---

*Last updated: 2026-02-20*
*Reference implementation: s20530019, s20530028*
