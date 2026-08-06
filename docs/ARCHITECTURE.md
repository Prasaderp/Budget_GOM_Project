# Budget Making System — Project File Architecture

> **Purpose:** Quick-reference file-structure map for developers & AI models.  
> Each file gets a one-liner. Schemes → Sub-schemes → Features are shown hierarchically.

---

## Root Directory

```
MAIN_PROJECT/
├── main.py                      # App entry-point; runs uvicorn server
├── requirements.txt             # Python dependencies list
├── .env                         # Environment variables (DB creds, secrets, API keys)
├── .gitignore                   # Git ignore rules
├── logincredentials.txt         # Login credentials reference for testing/dev
├── ARCHITECTURE.md              # This file
│
├── src/                         # All backend source code
├── templates/                   # Jinja2 HTML templates
├── static/                      # Static assets (CSS, JS, images)
├── excel_templates/             # Original Excel templates for export (.xlsx)
├── migrations/                  # SQL migration & data insertion scripts
├── deployment/                  # Deployment config files
├── docs/                        # Project documentation & GR references
└── Prompt Eng/                  # AI prompt engineering guides
```

---

## `src/` — Backend Source Code

### Top-Level Files

```
src/
├── __init__.py
├── main.py                      # FastAPI app creation, middleware setup, all router includes
├── config.py                    # App-wide settings (DB URL, CORS, session config)
├── config_schemes.py            # Master registry of all schemes, sub-schemes, charged/voted types
├── database.py                  # Database engine, session factory, connection pool
├── models.py                    # Core SQLAlchemy models (User, FiscalYear, DataFillingPeriod, etc.)
├── schemas.py                   # Pydantic schemas for auth, user, fiscal year
├── chatbot.py                   # Chatbot router mount entry-point
│
├── audit_middleware.py          # Request-level audit logging middleware
├── audit_service.py             # Audit trail CRUD operations & querying
├── email_service.py             # Email notification sending (SMTP)
├── notification_service.py      # In-app notification system (create, read, mark-read)
│
├── utils_auth.py                # Auth helpers (JWT token creation, password hashing, role checks)
├── utils_cache.py               # In-memory caching utilities with TTL
├── utils_da_rate.py             # DA (Dearness Allowance) rate lookup & computation
├── utils_district.py            # District master-data fetch & validation
├── utils_fiscal_year.py         # Fiscal year resolution, active-year helpers & get_relative_fiscal_years()
├── utils_migrations.py          # SQL migration runner (auto-applies migration files on startup)
├── utils_performance.py         # Performance timing decorators & logging
├── utils_salary_mode.py         # Salary mode (7th Pay / old) utility
├── utils_scheme.py              # Scheme info lookup, completion % calculation
├── utils_static.py              # Static data helpers (categories, designations)
├── utils_taluka.py              # Taluka master-data fetch
├── utils_taluka_user_management.py  # Taluka-level user assignment & permission management
└── utils_timing.py              # Data-filling period open/close timing logic
```

### `src/core/` — Base Framework

```
src/core/
├── __init__.py                  # Exports core classes
├── base_config.py               # Abstract scheme config class (columns, labels, table names)
├── base_models.py               # Abstract SQLAlchemy model mixin for scheme tables — inherits TalukaScopedMixin
├── base_router.py               # Generic CRUD router factory for schemes
├── base_schemas.py              # Base Pydantic schemas for scheme data
├── registry.py                  # Scheme registry — auto-discovers & registers scheme modules
├── secure_crud.py               # Secure CRUD operations with role-based access control — routes through taluka/write.py
├── template_context.py          # Common template context builder for Jinja2
├── templates.py                 # Jinja2 template environment setup
│
└── taluka/                      # Taluka-level data consolidation (see "Taluka Data Consolidation" below)
    ├── __init__.py               # Public surface: constants, models, scope re-exported
    ├── constants.py              # DISTRICT_LEVEL, DISTRICT_OFFICE, RESERVED_TALUKA_VALUES
    ├── models.py                 # TalukaScopedMixin, iter_scoped_models(), natural_key_columns()
    ├── scope.py                  # DataScope, request-scoped contextvar, resolve_scope_from_request()
    ├── orm_filter.py              # do_orm_execute listener — the single ORM read-isolation interception point
    ├── middleware.py              # TalukaScopeMiddleware — sets/resets the scope contextvar per request
    ├── consolidation.py           # consolidate_row() / consolidate_district() — the roll-up recompute
    ├── write.py                   # resolve_editable_row() (Recipe R), create_row_family()/delete_row_family() (Recipe D)
    └── provisioning.py            # provision_taluka_rows(), ensure_contribution_rows() — activation/FY seeding
```

### `src/routers/` — API & UI Routers

```
src/routers/
├── __init__.py
├── admin.py                     # Admin panel routes (user management, system settings)
├── api_assistant.py             # AI chatbot assistant API endpoints
├── auth.py                      # Login, logout, session, token refresh routes
├── completion_status.py         # Scheme-wise data completion status API
├── fiscal_year.py               # Fiscal year CRUD & switching routes
├── messages.py                  # Notification/message system routes
├── settings.py                  # User settings & preferences routes
├── timing_management.py         # Data-filling period open/close management
├── training.py                  # Training module routes (help, onboarding)
├── ui_scheme_selection.py       # UI — scheme selection page (charged/voted → scheme → sub-scheme)
├── ui_shashan_niryan.py         # UI — GR (Government Resolution) reference page
├── ui_taluka_selection.py       # UI — taluka selection & dashboard; activation/deactivation provisions taluka rows
├── ui_taluka_breakdown.py       # UI — read-only per-taluka contribution breakdown (district/DCO only, taluka gets 403)
└── warnings.py                  # System warnings/alerts routes
```

### `src/chatbot/` — AI Budget Assistant

```
src/chatbot/
├── __init__.py                  # Chatbot module init & router export
├── main.py                      # Chatbot FastAPI router & conversation handler
├── config.py                    # LLM configuration (model, temperature, prompts)
├── database.py                  # Chatbot DB operations (conversation history, query logs)
├── llm.py                       # LLM client initialization (OpenAI/Azure)
├── cache.py                     # Chatbot response caching
│
├── processors/
│   ├── __init__.py
│   └── query_execution.py       # SQL query execution engine (sanitized, read-only)
│
├── security/
│   ├── __init__.py
│   └── policies.py              # Security policies (query validation, injection prevention)
│
├── utils/
│   ├── __init__.py
│   └── validation.py            # Input validation & sanitization
│
└── schemas/                     # Per-scheme chatbot knowledge (see below)
    ├── __init__.py
    ├── registry.py              # Chatbot schema registry (maps scheme → context generator)
    ├── prompt_registry.py       # Prompt template registry for LLM
    │
    ├── s2053/                   # Each scheme folder follows this pattern:
    │   ├── __init__.py
    │   ├── context_generator.py # Generates DB context for LLM about this scheme
    │   ├── processors/          # Query pre/post-processing for this scheme
    │   │   ├── __init__.py
    │   │   ├── preprocessing.py # Query preprocessing & intent detection
    │   │   ├── sql_generation.py# SQL generation from natural language
    │   │   └── response_generation.py # Natural language response formatting
    │   ├── prompts/             # LLM prompt templates (empty/configured)
    │   └── subs/                # Per-subscheme chatbot config
    │       └── 20530028/        # Example subscheme
    │           ├── __init__.py
    │           ├── prompt_config.py   # Subscheme-specific prompt tuning
    │           └── security_policy.py # Subscheme-specific query restrictions
    │
    ├── s2029/                   # Same pattern: context_generator + processors + subs
    ├── s2045/
    ├── s2235/
    ├── s7610/
    ├── s0029/
    ├── s2075/
    ├── s2215/
    ├── s2245/
    ├── s6245/
    └── s6401/
```

---

## `src/schemes/` — Scheme Business Logic

> **Hierarchy:** `schemes/ → {scheme}/ → subs/ → {subscheme}/ → {feature}/`  
> **Charged** = Constitutionally mandated expenditure. **Voted** = Legislature-approved expenditure.

### `src/schemes/common/` — Cross-Scheme Shared Code

```
src/schemes/common/
├── __init__.py
├── excel_export.py              # Shared Excel export logic across schemes
├── utils.py                     # Shared utility functions
└── post_levels/                 # Post-level (pay grade) management
    ├── __init__.py
    ├── api_router.py            # Post-level CRUD API
    ├── models.py                # PostLevel SQLAlchemy model
    ├── repository.py            # Post-level DB queries
    ├── schemas.py               # Post-level Pydantic schemas
    └── service.py               # Post-level business logic
```

### Scheme Overview — Charged/Voted & Sub-Schemes

| Scheme | Name | Type | Sub-Schemes | Structure |
|--------|------|------|-------------|-----------|
| **2053** | District Administration | Charged: 5, Voted: 5 | 20530019(C), 20530153(C), 20530233(C), 20530304(C), 20530378(C), 20530028(V), 20530162(V), 20530242(V), 20530313(V), 20530387(V) | Feature-modular (refactored) or monolithic |
| **2029** | Land Revenue | Charged: 1, Voted: 3 | 20290037(C), 20290046(V), 20290182(V), 20290262(V) | Monolithic |
| **2045** | Other Taxes & Duties | Voted: 4 | 20450091(V)★, 20450182(V), 20450251(V), 20450262(V) | Monolithic + common layer (district_expenditure) |
| **2235** | Social Security & Welfare | Voted: 4 | 22350311(V), 22350338(V), 22353195(V), 22353408(V) | District expenditure |
| **7610** | Government Advances | Voted: 4 | 76100149(V), 76100158(V), 76100167(V), 76101871(V) | District expenditure |
| **2075** | Misc. General Services | Voted (unified) | Unified (no sub-selection) | Unified expenditure table |
| **2215** | Water Scarcity | Voted (unified) | Unified (no sub-selection) | Section-based (index + totals) |
| **2245** | Natural Calamity Relief | Voted (unified) | Unified (no sub-selection) | Section-based (sec1, sec2, sec3) |
| **0029** | Land Revenue Receipts | Voted (unified) | Unified (no sub-selection) | Section-based (sec1, sec2) |
| **6245** | Loans for Natural Calamities | Voted: 1 | 62450017(V) | District expenditure |
| **6401** | Loans for Crop Husbandry | Voted: 1 | 64010018(V) | District expenditure |

> ★ = fully implemented with all features. C = Charged, V = Voted.

---

### Scheme `2053` — District Administration (Largest, Most Complex)

#### Common layer

```
src/schemes/s2053/
├── __init__.py                  # Registers all s2053 sub-scheme routers
├── config.py                    # Scheme-level config constants
└── common/
    ├── __init__.py
    ├── fiscal_year_labels.py    # FiscalYearLabels class — dynamic column headers for all s2053 sub-schemes
    └── services/
        ├── __init__.py
        └── abstract_service.py  # Shared abstract/budget-summary computation logic
```

#### Sub-scheme structure — Refactored pattern (s20530028 — flagship)

> s20530028 has been refactored into a layered architecture with separate feature modules.  
> Each feature (budget_post_details, post_expenses, post_status, unit_expenditure) follows:  
> `controllers/ → services/ → repositories/ → dto/ → utils/`

```
src/schemes/s2053/subs/s20530028/
├── __init__.py                  # Sub-scheme router aggregation & registration
├── config.py                    # Column definitions, table names, Excel mappings, category config
├── models.py                    # SQLAlchemy models (BudgetPost, PostExpense, PostStatus, UnitExpenditure)
├── schemas.py                   # Pydantic request/response schemas
├── helpers.py                   # Sub-scheme specific helpers
├── router_api.py                # API router (mounts feature API controllers)
├── router_ui.py                 # UI router (mounts feature UI controllers)
├── ui_abstract.py               # District-wise abstract summary page logic
├── ui_budget_summary.py         # Budget summary page with totals & roll-ups
├── ui_category_info.py          # Category-wise information display logic
│
├── budget_post_details/         # Feature: Budget Post Details (Sanctioned/Filled posts)
│   ├── __init__.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── api_controller.py    # REST API for budget post CRUD
│   │   └── ui_controller.py     # UI form/list rendering for budget posts
│   ├── services/
│   │   ├── __init__.py
│   │   ├── budget_post_service.py     # Core budget post business logic
│   │   ├── designation_service.py     # Designation (post name) lookup
│   │   ├── export_service.py          # Excel export for budget posts
│   │   └── pay_matrix_service.py      # Pay matrix (7th CPC) salary lookup
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── budget_post_repository.py  # Budget post DB queries (insert, update, delete, list)
│   ├── dto/
│   │   ├── __init__.py
│   │   ├── budget_post_dto.py         # Data transfer object for budget post
│   │   └── filter_dto.py             # Filter criteria DTO
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py             # Number/currency formatting
│       └── validators.py            # Input validation rules
│
├── post_expenses/               # Feature: Post-wise Expenses (Salary + allowances)
│   ├── __init__.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── api_controller.py    # REST API for post expense CRUD
│   │   └── ui_controller.py     # UI form/list rendering for expenses
│   ├── services/
│   │   ├── __init__.py
│   │   ├── post_expenses_service.py   # Expense calculation logic (basic pay, DA, HRA, NPS)
│   │   ├── charts_service.py          # Chart data generation for expense visualization
│   │   ├── nps_component_service.py   # NPS (National Pension Scheme) computation
│   │   ├── export_service.py          # Excel export for expenses
│   │   └── summary_service.py         # Expense summary aggregation
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── post_expenses_repository.py # Post expense DB queries
│   ├── dto/
│   │   ├── __init__.py
│   │   ├── post_expenses_dto.py       # Expense data transfer object
│   │   └── filter_dto.py             # Filter criteria DTO
│   └── utils/
│       ├── __init__.py
│       └── validators.py            # Expense-specific validation
│
├── post_status/                 # Feature: Post Status (Sanctioned/Working/Vacant tracking)
│   ├── __init__.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── api_controller.py    # REST API for post status CRUD
│   │   └── ui_controller.py     # UI form/list rendering for post status
│   ├── services/
│   │   ├── __init__.py
│   │   ├── post_status_service.py     # Status tracking logic
│   │   ├── export_service.py          # Excel export for post status
│   │   └── summary_service.py         # Status summary (vacant count, filled count, etc.)
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── post_status_repository.py  # Post status DB queries
│   ├── dto/
│   │   ├── __init__.py
│   │   ├── post_status_dto.py         # Status data transfer object
│   │   └── filter_dto.py             # Filter criteria DTO
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py             # Status display formatting
│       └── validators.py            # Status validation rules
│
├── unit_expenditure/            # Feature: Unit-wise Expenditure (Non-salary spending)
│   ├── __init__.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── api_controller.py    # REST API for unit expenditure CRUD
│   │   └── ui_controller.py     # UI form/list rendering for unit expenditure
│   ├── services/
│   │   ├── __init__.py
│   │   ├── unit_expenditure_service.py # Unit expenditure business logic
│   │   ├── export_service.py           # Excel export for unit expenditure
│   │   └── summary_service.py          # Unit expenditure summary & totals
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── unit_expenditure_repository.py # Unit expenditure DB queries
│   ├── dto/
│   │   ├── __init__.py
│   │   ├── unit_expenditure_dto.py     # Unit expenditure data transfer object
│   │   └── filter_dto.py              # Filter criteria DTO
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py              # Amount formatting (lakh, crore conversions)
│       └── validators.py             # Unit expenditure validation
│
├── shared/                      # Shared utilities within this sub-scheme
│   ├── __init__.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── pay_matrix_repository.py   # Pay matrix data access
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audit_service.py           # Sub-scheme level audit logging
│   │   └── cache_service.py           # Sub-scheme level caching
│   └── utils/
│       ├── __init__.py
│       ├── request_utils.py           # Request parsing helpers
│       ├── response_utils.py          # Response formatting helpers
│       └── validators.py             # Cross-feature validators
│
└── excel_export/                # Excel export engine for this sub-scheme
    ├── __init__.py
    ├── template_export_service.py   # Orchestrates full Excel workbook export
    ├── populators/                  # Sheet-level data populators
    │   ├── __init__.py
    │   ├── budget_post_details.py   # Populates budget post details sheet
    │   ├── post_expenses.py         # Populates post expenses sheet
    │   ├── post_status.py           # Populates post status sheet
    │   └── unit_expenditure.py      # Populates unit expenditure sheet
    └── processors/                  # District-specific Excel processors
        ├── __init__.py
        ├── dco_staff.py             # DCO staff district processor
        ├── mumbai_city.py           # Mumbai City district processor
        ├── mumbai_suburban.py       # Mumbai Suburban district processor
        ├── palghar.py               # Palghar district processor
        ├── raigad.py                # Raigad district processor
        ├── ratnagiri.py             # Ratnagiri district processor
        ├── sindhudurg.py            # Sindhudurg district processor
        └── thane.py                 # Thane district processor
```

#### Sub-scheme structure — Monolithic pattern (e.g., s20530019, s20530153, etc.)

> Older sub-schemes use a flat/monolithic file layout (no feature folders).  
> All `ui_*.py` files inject `relative_years` (from `get_relative_fiscal_years()`) into the template context for dynamic fiscal year rendering.

```
src/schemes/s2053/subs/s20530019/      # (Charged) — same pattern for s20530153, s20530233, s20530304, s20530378
├── __init__.py                  # Router registration
├── config.py                    # Column definitions, table names, category config
├── models.py                    # SQLAlchemy models
├── schemas.py                   # Pydantic schemas
├── helpers.py                   # Helper functions
├── router_api.py                # API endpoints
├── router_ui.py                 # UI page routes
├── api_budget_details.py        # Budget details API logic
├── ui_abstract.py               # Abstract/summary page
├── ui_budget_details.py         # Budget details page logic
├── ui_budget_summary.py         # Budget summary page logic
├── ui_category_info.py          # Category info page logic
├── ui_post_expenses.py          # Post expenses page logic (salary computation)
├── ui_post_status.py            # Post status page logic
├── ui_unit_expenditure.py       # Unit expenditure page logic
├── shared/                      # Shared utils (some sub-schemes)
│   ├── __init__.py
│   ├── services/                # Shared services
│   └── utils/                   # Shared utilities
└── excel_export/                # Excel export (same populator/processor pattern)
    ├── __init__.py
    ├── template_export_service.py
    ├── populators/
    └── processors/
```

> **All 10 s2053 sub-schemes** follow either the refactored (s20530028) or monolithic pattern.

---

### Scheme `2029` — Land Revenue

```
src/schemes/s2029/
├── __init__.py                  # Registers all s2029 sub-scheme routers
└── subs/
    ├── __init__.py
    ├── s20290037/               # (Charged) — Monolithic pattern
    ├── s20290046/               # (Voted) — Monolithic pattern
    ├── s20290182/               # (Voted) — Monolithic pattern
    └── s20290262/               # (Voted) — Monolithic pattern
```

> Each sub-scheme has the monolithic file layout:  
> `__init__.py, config.py, models.py, schemas.py, helpers.py, router_api.py, router_ui.py, api_budget_details.py, ui_*.py, excel_export/`

---

### Scheme `2045` — Other Taxes & Duties

```
src/schemes/s2045/
├── __init__.py                  # Registers all s2045 sub-scheme routers
├── common/                      # Shared layer for all s2045 sub-schemes
│   ├── __init__.py
│   ├── district_expenditure/    # Shared district expenditure feature
│   │   ├── __init__.py
│   │   ├── base_helpers.py      # Common helper functions
│   │   ├── base_models.py       # Base SQLAlchemy model for district expenditure
│   │   ├── base_router.py       # Base router with common CRUD operations
│   │   ├── base_schemas.py      # Base Pydantic schemas
│   │   ├── excel_populator.py   # Excel populator for district data
│   │   └── unified_excel_export.py # Unified Excel export across sub-schemes
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base_abstract_handler.py       # Base abstract/summary handler
│   │   └── base_category_info_handler.py  # Base category info handler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── abstract_service.py            # Abstract/summary computation
│   │   ├── category_info_service.py       # Category-wise info service
│   │   └── post_status_service.py         # Post status service
│   └── utils/
│       ├── __init__.py
│       ├── constants.py         # Constants (column keys, category codes)
│       └── helpers.py           # Helper functions
│
└── subs/
    ├── __init__.py
    ├── s20450091/               # (Voted, full) — Monolithic + shared common features
    │   ├── __init__.py, config.py, models.py, schemas.py, helpers.py
    │   ├── router_api.py, router_ui.py, api_budget_details.py
    │   ├── ui_abstract.py, ui_budget_details.py, ui_budget_summary.py
    │   ├── ui_category_info.py, ui_post_expenses.py, ui_post_status.py, ui_unit_expenditure.py
    │   ├── shared/              # Local shared services/utils
    │   └── excel_export/
    ├── s20450182/               # (Voted, lightweight) — district expenditure only
    │   ├── __init__.py, config.py, models.py, schemas.py, helpers.py
    │   └── router.py            # Single router (simpler structure)
    ├── s20450251/               # (Voted, lightweight) — same as s20450182
    └── s20450262/               # (Voted, lightweight) — same as s20450182
```

---

### Scheme `2075` — Miscellaneous General Services (Unified)

> No sub-scheme selection — directly shows expenditure table.

```
src/schemes/s2075/
├── __init__.py                  # Router registration
├── fiscal_year_labels.py        # FiscalYearLabels2075 — dynamic headers; injected via router_ui.py
├── config.py                    # Expenditure table config, column definitions
├── models.py                    # SQLAlchemy model for expenditure records
├── schemas.py                   # Pydantic schemas
├── helpers.py                   # Utility functions
├── router_api.py                # API endpoints for expenditure CRUD
├── router_ui.py                 # UI page routes — injects fy_labels into context
└── excel_export/
    ├── __init__.py
    ├── template_export_service.py  # Orchestrates Excel export
    └── populators/
        ├── __init__.py
        └── s2075_populator.py      # Populates the Excel sheet
```

---

### Schemes `2235`, `7610` — District Expenditure Pattern

> Both follow an identical structure with district-level expenditure tracking.  
> Each scheme has a `fiscal_year_labels.py` at the scheme root providing a `FiscalYearLabels` class consumed by all sub-scheme `router_ui.py` files to render dynamic column headers.

```
src/schemes/s2235/               # Social Security & Welfare
├── __init__.py
├── fiscal_year_labels.py        # FiscalYearLabels2235 — dynamic headers for all s2235 sub-schemes
├── excel_export/
│   ├── __init__.py
│   ├── template_export_service.py
│   └── populators/
└── subs/
    ├── __init__.py
    ├── s22350311/               # Each sub-scheme follows this layout:
    │   ├── __init__.py
    │   ├── config.py            # District expenditure column config
    │   ├── helpers.py           # Helper functions
    │   ├── models.py            # SQLAlchemy model
    │   ├── router_api.py        # API routes
    │   ├── router_ui.py         # UI routes (list + form) — injects fy_labels into context
    │   └── schemas.py           # Pydantic schemas
    ├── s22350338/               # Same structure
    ├── s22353195/               # Same structure
    └── s22353408/               # Same structure

src/schemes/s7610/               # Government Advances — follows same pattern
├── __init__.py
├── fiscal_year_labels.py        # FiscalYearLabels7610 — dynamic headers for all s7610 sub-schemes
├── shared_helpers.py            # Helpers shared across s7610 sub-schemes
├── excel_export/
│   ├── __init__.py
│   ├── template_export_service.py
│   └── populators/
│       ├── __init__.py
│       └── s7610_populator.py
└── subs/
    ├── __init__.py
    ├── s76100149/               # (Voted) — district expenditure layout; router_ui.py injects fy_labels
    ├── s76100158/               # Same
    ├── s76100167/               # Same
    └── s76101871/               # Same
```

---

### Schemes `0029`, `2215`, `2245` — Unified / Section-Based

> These have no sub-scheme selection UI. Single table/section approach.  
> Each scheme has a `fiscal_year_labels.py` at the scheme root; `router_ui.py` injects `fy_labels` into the template context.

```
src/schemes/s0029/               # Land Revenue Receipts
├── __init__.py
├── fiscal_year_labels.py        # FiscalYearLabels0029 — dynamic headers for s0029 views
└── subs/
    └── s0029/                   # Self-referencing (scheme = sub-scheme)
        ├── __init__.py
        ├── config.py            # Section config (section1, section2)
        ├── helpers.py
        ├── models.py
        ├── router_api.py
        ├── router_ui.py         # Injects fy_labels into context
        └── schemas.py

src/schemes/s2215/               # Water Scarcity
├── __init__.py
├── fiscal_year_labels.py        # FiscalYearLabels2215 — dynamic headers
└── subs/
    └── s2215/
        ├── __init__.py, config.py, helpers.py, models.py
        ├── router_api.py, router_ui.py, schemas.py

src/schemes/s2245/               # Natural Calamity Relief
├── __init__.py
├── fiscal_year_labels.py        # FiscalYearLabels2245 — dynamic headers
└── subs/
    └── s2245/
        ├── __init__.py, config.py, helpers.py, models.py
        ├── router_api.py, router_ui.py, schemas.py
```

---

### Schemes `6245`, `6401` — Single Sub-Scheme Loans

```
src/schemes/s6245/               # Loans for Natural Calamities
├── __init__.py
├── fiscal_year_labels.py        # FiscalYearLabels6245 — dynamic headers for s62450017 views
└── subs/
    └── s62450017/               # Single sub-scheme (district expenditure)
        ├── __init__.py, config.py, helpers.py, models.py
        ├── router_api.py, router_ui.py, schemas.py  # router_ui.py injects fy_labels
        └── excel_export/
            ├── __init__.py
            ├── template_export_service.py
            └── populators/

src/schemes/s6401/               # Loans for Crop Husbandry
├── __init__.py
├── fiscal_year_labels.py        # FiscalYearLabels6401 — dynamic headers for s64010018 views
└── subs/
    └── s64010018/               # Same structure as s62450017
        ├── __init__.py, config.py, helpers.py, models.py
        ├── router_api.py, router_ui.py, schemas.py  # router_ui.py injects fy_labels
        └── excel_export/
```

---

### `src/schemes/s2245_2215/` — Combined Excel Export

```
src/schemes/s2245_2215/
├── __init__.py
└── excel_export/                # Combined Excel export for 2245 + 2215 together
    ├── __init__.py
    ├── template_export_service.py
    └── populators/
```

---

## `templates/` — Jinja2 HTML Templates

### Top-Level Pages

```
templates/
├── base.html                    # Master layout (sidebar, navbar, scripts, styles)
├── login.html                   # Login page redirect
├── login_base.html              # Login page with form
├── access_denied.html           # 403 access denied page
├── scheme_selection.html        # Charged/Voted → Scheme → Sub-scheme selection page
├── taluka_selection.html        # Taluka selection & dashboard
├── taluka_breakdown.html        # Read-only district-office + per-taluka + total table (district/DCO only)
├── scheme_placeholder.html      # Placeholder for unimplemented sub-schemes
├── settings.html                # User settings page
├── admin_login.html             # Admin login page
├── admin_users.html             # Admin user management page
├── admin_audit.html             # Admin audit log viewer
├── timing_management.html       # Data-filling period management page
├── shashan_niryan.html          # Government Resolution (GR) reference page
├── alert_banner.html            # Alert/notification banner partial
├── assistant_response.html      # AI chatbot response rendering partial
└── warnings.html                # Warnings/alerts page
```

### Scheme Templates

> Templates mirror the `src/schemes/` structure.

```
templates/schemes/
├── common/
│   └── post_levels/
│       └── post_levels.html     # Post-level management page
│
├── s2053/subs/
│   └── s20530028/               # Each sub-scheme has these templates:
│       ├── base.html                        # Sub-scheme layout wrapper
│       ├── budget_post_details_form.html     # Budget post create/edit form
│       ├── budget_post_details_list.html     # Budget post list with filters & table
│       ├── post_expenses_form.html          # Post expense create/edit form
│       ├── post_expenses_list.html          # Post expense list with totals
│       ├── post_status_form.html            # Post status create/edit form
│       ├── post_status_list.html            # Post status list with tracking
│       ├── unit_expenditure_form.html       # Unit expenditure create/edit form
│       ├── unit_expenditure_list.html       # Unit expenditure list
│       ├── category_wise_info.html          # Category-wise summary view
│       └── district_wise_abstract.html      # District-wise abstract summary
│   └── (s20530019, s20530153, ... same template set per sub-scheme)
│
├── s2029/subs/
│   └── s20290037/ (... same template set)
│
├── s2045/
│   ├── common/
│   │   ├── category_wise_info.html          # Shared category info template
│   │   └── district_wise_abstract.html      # Shared abstract template
│   └── subs/
│       ├── s20450091/           # Full template set (11 templates)
│       ├── s20450182/           # Lightweight (base + district expenditure form/list)
│       ├── s20450251/           # Lightweight
│       └── s20450262/           # Lightweight
│
├── s2235/subs/
│   └── s22350311/               # District expenditure templates
│       ├── base.html
│       ├── district_expenditure_form.html
│       ├── district_expenditure_list.html
│       └── division_total.html              # Division-level total view
│
├── s7610/subs/
│   └── s76100149/               # District expenditure templates (form + list)
│
├── s2075/subs/
│   └── s2075/
│       ├── base.html
│       └── expenditure_list.html            # Single expenditure list page
│
├── s0029/subs/
│   └── s0029/
│       ├── base.html
│       ├── section1_form.html               # Receipt section 1 form
│       ├── section1_list.html               # Receipt section 1 list
│       └── section2_list.html               # Receipt section 2 list
│
├── s2215/subs/
│   └── s2215/
│       ├── base.html
│       ├── index.html                       # Main water scarcity data entry page
│       └── totals.html                      # Totals summary page
│
├── s2245/subs/
│   └── s2245/
│       ├── base.html
│       ├── section1_form.html               # Calamity relief section 1 form
│       ├── section1_list.html               # Section 1 list
│       ├── section2_list.html               # Section 2 list
│       └── section3_list.html               # Section 3 list
│
├── s6245/subs/
│   └── s62450017/               # District expenditure (form + list)
│
└── s6401/subs/
    └── s64010018/               # District expenditure (form + list)
```

---

## `excel_templates/` — Original Excel Templates (.xlsx)

> These are the original government Excel template files used as base for export.

```
excel_templates/
├── s2053/subs/
│   ├── s20530028/
│   │   └── original_template.xlsx   # Master budget template for this sub-scheme
│   ├── s20530019/
│   │   └── original_template.xlsx
│   └── (... one .xlsx per sub-scheme)
│
├── s2029/subs/                  # One template per sub-scheme
│   ├── s20290037/, s20290046/, s20290182/, s20290262/
│
├── s2045/subs/                  # One template per sub-scheme
│   ├── s20450091/, s20450182/
│
├── s2075/subs/                  # Single template
├── s2235/subs/                  # Single template
├── s2245_2215/subs/             # Combined template
├── s7610/subs/                  # Single template
├── s0029/subs/                  # Single template
├── s6245/subs/                  # Single template
└── s6401/subs/                  # Single template
```

---

## `migrations/` — SQL Migration Scripts

```
migrations/
├── core/                        # Core database schema migrations
│   ├── 001_add_email_phone_notification_preferences.sql
│   ├── 002_add_fiscal_year_columns.sql
│   ├── 003_create_fiscal_year_indexes.sql
│   ├── 004_create_other_indexes.sql
│   ├── 005_add_composite_indexes.sql
│   ├── 007_convert_basic_pay_to_decimal.sql
│   ├── 010_add_sub_scheme_code_to_data_filling_periods.sql
│   ├── 011_add_salary_mode_to_fiscal_years.sql
│   ├── 012_add_da_percentage_to_fiscal_years.sql
│   └── 013_add_taluka_dimension.sql          # Adds `taluka` to all 78 scoped tables + rebuilds natural keys + v_<table>_district views
│
├── shared/
│   └── 006_create_pay_matrix.sql    # 7th Pay Commission pay matrix seed data
│
└── schemes/                         # Per-scheme data insertion & migration
    ├── s2053/
    │   ├── 011_add_post_level_details.sql       # Add post-level detail columns
    │   ├── DATAINSERTION_20530019.sql           # Seed data (designations, categories, budget heads)
    │   ├── DATAINSERTION_20530028.sql           # Seed data for s20530028
    │   ├── DATAINSERTION_20530153.sql
    │   ├── DATAINSERTION_20530162.sql
    │   ├── DATAINSERTION_20530233.sql
    │   ├── DATAINSERTION_20530242.sql
    │   ├── DATAINSERTION_20530304.sql
    │   ├── DATAINSERTION_20530313.sql
    │   ├── DATAINSERTION_20530378.sql
    │   └── DATAINSERTION_20530387.sql
    ├── s2029/
    │   ├── DATAINSERTION_20290037.sql
    │   ├── DATAINSERTION_20290046.sql
    │   ├── DATAINSERTION_20290182.sql
    │   └── DATAINSERTION_20290262.sql
    ├── s2045/
    │   ├── 001_create_district_expenditure_20450182.sql  # Creates district table
    │   ├── 002_create_district_expenditure_20450251.sql
    │   ├── 003_create_district_expenditure_20450262.sql
    │   └── DATAINSERTION_20450091.sql
    ├── s7610/
    │   ├── DATAINSERTION_76100158.sql
    │   ├── DATAINSERTION_76100167.sql
    │   ├── DATAINSERTION_76101871.sql
    │   └── DATAINSERTION_OPTIMIZED.sql          # Optimized combined insertion
    ├── s2235/
    │   ├── 001_add_22353408.sql                 # Schema creation per sub-scheme
    │   ├── 002_add_22350311.sql
    │   ├── 003_add_22353195.sql
    │   └── 004_add_22350338.sql
    ├── s2075/
    │   ├── 003_unify_2075_schema.sql            # Unified schema migration
    │   ├── DATAINSERTION_20750249.sql
    │   └── DATAINSERTION_20750294.sql
    ├── s2245/
    │   ├── DATAINSERTION_OPTMIZED.sql
    │   └── DATAINSERTION_SECTION3.sql
    ├── s2215/
    │   └── 001_add_2215.sql                     # Creates 2215 schema
    ├── s6245/
    │   └── DATAINSERTION_OPTIMIZED.sql
    └── s6401/
        └── DATAINSERTION_OPTIMIZED.sql
```

---

## `static/` — Static Assets

```
static/
├── gom_logo.png                 # Government of Maharashtra logo
├── login.css                    # Login page stylesheet
└── js/
    ├── post_levels.js           # Post-level management interactive JS
    ├── settings.js              # Settings page JS
    └── shashan_niryan.js        # GR reference page JS
```

---

## `deployment/` — Deployment Configuration

```
deployment/
├── gunicorn.conf.py             # Gunicorn WSGI server config
├── logging.conf                 # Python logging configuration
├── start.bat                    # Windows startup script
└── start.sh                     # Linux/Unix startup script
```

---

## `docs/` — Documentation & References

```
docs/
├── PROJECT_STRUCTURE.md                               # Older project structure doc
├── AI Budget Making System_ Cost Estimation Documentation.docx
├── Budget Management System_ Research & Developmen....docx
└── Shashan_Nirnay/              # Government Resolution (GR) PDFs
    ├── Budget Form File P.PDF
    ├── Gazette Seventh Pay.pdf
    ├── HRA All GR upto 2019 merged.pdf
    ├── Palghar-31-04-14 New Post-102.pdf
    ├── Revised Travelling Allowance Rate 20.04.2022.pdf
    └── आकृतीबंध शा.नि.20-03-2006.pdf
```
---

## Key Architectural Patterns Summary

| Pattern | Used In | Description |
|---------|---------|-------------|
| **Refactored / Layered** | s20530028 | `controllers/ → services/ → repositories/ → dto/ → utils/` per feature |
| **Monolithic** | s20530019, s2029, most s2053 | Flat files: `config, models, schemas, helpers, router_api, router_ui, ui_*.py` |
| **District Expenditure** | s2235, s7610, s6245, s6401, s2045 (lightweight) | Simple district-level expenditure form/list |
| **Section-Based** | s0029, s2215, s2245 | Data split into sections (section1, section2, etc.) |
| **Unified** | s2075 | No sub-scheme selection, single expenditure table |
| **Common Layer** | s2045/common, s2053/common | Shared base classes inherited by sub-schemes |
| **Excel Export** | All implemented schemes | `template_export_service → populators → processors` pipeline |
| **Chatbot per Scheme** | All schemes | `context_generator + processors + per-sub prompt_config` |
| **Dynamic Fiscal Year** | All schemes | `fiscal_year_labels.py` at scheme root → `FiscalYearLabels` class → injected as `fy_labels` / `relative_years` in every `router_ui.py` → Jinja2 templates use `{{ fy_labels.* }}` instead of hardcoded year strings |
| **Taluka Consolidation** | All 78 district-scoped tables | `TalukaScopedMixin` (`src/core/taluka/`) row-role column + single `do_orm_execute` read filter + `resolve_editable_row()` write redirection + `consolidate_row()` roll-up — see "Taluka Data Consolidation" below |

---

## Taluka Data Consolidation

> Full design: [`docs/plan.md`](./plan.md). Package: `src/core/taluka/` (tree above). Migration: `migrations/core/013_add_taluka_dimension.sql`.

Every district-scoped table (78 of them — every 4-table-family, district-expenditure and section-based table; **not** `sub_head_expenditure_2075`, which is division-level and has no `district` column) carries one additional column, `taluka VARCHAR(100) NOT NULL DEFAULT ''`, whose value defines a **row role**:

| `taluka` value | Role | Written by | Read by |
|---|---|---|---|
| `''` (empty string) | **Consolidated district row** — derived, never hand-edited | `consolidate_row()` only | every existing read path, unchanged — Excel exports, abstracts, summaries, DCO views, the chatbot |
| `'__district_office__'` | **District office's own contribution** | district assistant | consolidation, breakdown page |
| `'<District> Taluka <Name>'` | **One activated taluka's contribution** | that taluka's assistant | consolidation, breakdown page |

**The invariant:** `row(taluka='')[numeric_col] == Σ row(taluka='__district_office__')[numeric_col] + Σ row(taluka=t)[numeric_col]` for every currently active taluka `t`. `scripts/check_taluka_invariant.py` is the standing CI gate and production disaster-recovery tool for this invariant — see its docstring for the two structural failure shapes (orphan contributions, twinless consolidated rows) it detects beyond a plain value mismatch.

**Read isolation — one interception point.** A request-scoped `contextvar` (`src/core/taluka/scope.py`) carries the caller's `DataScope`; a single `do_orm_execute` listener (`src/core/taluka/orm_filter.py`) injects `with_loader_criteria(TalukaScopedMixin, lambda cls: cls.taluka == <scope value>, include_aliases=True)` into **every** ORM SELECT issued through the app's session factory — `query()`, 2.0-style `select()`, subqueries, joins, column-only queries — with no per-call-site change. The default, when no request context ever set a scope, is `taluka == ''` (consolidated) — **never unfiltered**. Services that legitimately need every row for a natural key (consolidation, provisioning, the breakdown page) opt out explicitly via `execution_options(taluka_scope_all=True)`.

**Write redirection.** Because a district-level list renders consolidated (`taluka=''`) ids, a write handler cannot rely on the read filter to resolve its target row — `resolve_editable_row()` (`src/core/taluka/write.py`) loads by raw id with the scope filter bypassed, then re-authorises explicitly (district ACL + a role-derived writable-taluka-value dispatch) before returning the caller's own contribution row, lazily creating it if absent. `create_row_family()` / `delete_row_family()` apply the equivalent natural-key-lifecycle handling to the 13 hand-written `router_api.py` modules' `POST`/`DELETE`, so a create/delete is never treated as a single-row operation that could leave an orphan or a twinless consolidated row. Taluka-level callers are rejected (403) from both.

**Chatbot.** `DynamicSchemaEngine._resolve_table_names()` maps each scoped table to a read-only `v_<table>_district` view (`WHERE taluka = ''`, created by the same migration) rather than adding taluka-awareness to the LLM prompt — the view makes a double-counting or leaking query structurally inexpressible. See `docs/CHATBOT_ARCHITECTURE_PLAN.md` for detail. Per-taluka chatbot drill-down is a deliberate scope exclusion; `src/routers/ui_taluka_breakdown.py` + `templates/taluka_breakdown.html` (district/DCO-only, read-only) serve that need instead.

---

## Excel Template Sheets Structure (per sub-scheme)

> The Excel export produces a workbook matching the original government budget form.  
> Sheets typically include:

| Sheet | Content | Feature Module |
|-------|---------|----------------|
| Budget Post Details | Sanctioned posts, pay level, basic pay | `budget_post_details` |
| Post Expenses | Salary, DA, HRA, NPS, medical, LTC breakdowns | `post_expenses` |
| Post Status | Sanctioned vs working vs vacant post counts | `post_status` |
| Unit Expenditure | Non-salary operational expenses per budget head | `unit_expenditure` |
| Abstract / Summary | District-wise roll-up totals | `ui_abstract`, `ui_budget_summary` |
| Category Info | Category-wise (SC/ST/OBC) bifurcation | `ui_category_info` |

> Simpler schemes (2235, 7610, 6245, 6401) have a single **District Expenditure** sheet.  
> Section-based schemes (0029, 2245, 2215) export data by sections.
