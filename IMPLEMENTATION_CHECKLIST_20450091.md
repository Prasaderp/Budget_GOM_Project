# Implementation Checklist for Sub-Scheme 20450091 (Stamp Duty Collection - Voted)

## ✅ Core Configuration Files
- [x] `src/schemes/s2045/subs/s20450091/config.py` - Scheme configuration with designations
- [x] `src/schemes/s2045/subs/s20450091/models.py` - Database models (4 tables)
- [x] `src/schemes/s2045/subs/s20450091/schemas.py` - Pydantic schemas
- [x] `src/schemes/s2045/subs/s20450091/__init__.py` - Module exports
- [x] `src/schemes/s2045/subs/s20450091/helpers.py` - Helper utilities

## ✅ API & Routing
- [x] `src/schemes/s2045/subs/s20450091/router_api.py` - API routes
- [x] `src/schemes/s2045/subs/s20450091/router_ui.py` - UI router aggregation
- [x] `src/schemes/s2045/subs/s20450091/api_budget_details.py` - Budget details API
- [x] `src/schemes/s2045/subs/s20450091/ui_budget_details.py` - Budget details UI
- [x] `src/schemes/s2045/subs/s20450091/ui_post_status.py` - Post status UI
- [x] `src/schemes/s2045/subs/s20450091/ui_post_expenses.py` - Post expenses UI
- [x] `src/schemes/s2045/subs/s20450091/ui_unit_expenditure.py` - Unit expenditure UI
- [x] `src/schemes/s2045/subs/s20450091/ui_budget_summary.py` - Budget summary UI
- [x] `src/schemes/s2045/subs/s20450091/ui_abstract.py` - Abstract UI
- [x] `src/schemes/s2045/subs/s20450091/ui_category_info.py` - Category info UI

## ✅ Excel Export System
- [x] `src/schemes/s2045/subs/s20450091/excel_export/__init__.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/template_export_service.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/populators/budget_post_details.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/populators/post_status.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/populators/post_expenses.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/populators/unit_expenditure.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/mumbai_city.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/mumbai_suburban.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/thane.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/palghar.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/raigad.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/ratnagiri.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/sindhudurg.py`
- [x] `src/schemes/s2045/subs/s20450091/excel_export/processors/dco_staff.py`

## ✅ Chatbot Integration
- [x] `src/chatbot/schemas/s2045/` - Parent scheme chatbot structure
- [x] `src/chatbot/schemas/s2045/subs/20450091/__init__.py`
- [x] `src/chatbot/schemas/s2045/subs/20450091/prompt_config.py`
- [x] `src/chatbot/schemas/s2045/subs/20450091/security_policy.py`

## ✅ Main Application Registration
- [x] Registered in `src/main.py` (lines 1058-1098)
  - Imports all routers
  - Registers scheme config
  - Includes all UI routers
  - Includes API router
  - Registers route prefixes

## ⚠️ Pending Items (User Action Required)
- [ ] **Database Migration** - Create SQL migration file with initial data
  - File location: `migrations/schemes/s2045/DATAINSERTION_20450091.sql`
  - User will manually update designations in the migration file
- [ ] **Excel Template** - Place Excel template file
  - File location: `excel_templates/s2045/subs/s20450091/Budget 20450091 for 2026-27.xlsx`
- [ ] **Database Tables** - Run migrations to create tables:
  - `budget_post_details_20450091`
  - `post_status_20450091`
  - `post_expenses_20450091`
  - `unit_expenditure_20450091`

## 📋 Key Designations Configured

### Permanent (5 designations):
1. Sub-District Officer (उपजिल्हाधिकारी)
2. Head Clerk/Awwal Karkun (अव्वल कारकून/करसमापूक कर)
3. Cashier (रोखपाल)
4. Clerk (लिपिक)
5. Peon (शिपाई)

### Temporary (9 designations):
1. Deputy Commissioner (उप आयुक्ता)
2. Tehsildar/Tax Collection Officer (तहसिलदार/करसमापूक कर अधिकारी)
3. Naib Tehsildar/Asst Tax Collection Officer (ना.तह./सहा.करसमापूक कर अधिकारी)
4. Stenographer (Lower Grade) (लघुलेखक (निम्न श्रेणी))
5. Head Clerk/Awwal Karkun (अव्वल कारकून/करसमापूक कर)
6. Inspector (निरीक्षक)
7. Clerk (लिपिक)
8. Vehicle Driver (वाहन चालक)
9. Peon (शिपाई)

## 🎯 Implementation Summary
- **Total Python Files Created**: 39
- **Scheme Code**: 20450091
- **Parent Scheme**: 2045 (Other Taxes and Duties)
- **Scheme Type**: Voted
- **Districts**: 8 (Mumbai City, Mumbai Suburban, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, DCO Staff)
- **Entry Point**: `/ui/s20450091/budget-post-details`

## 🚀 Next Steps
1. Create and run the SQL migration file with initial data
2. Place the Excel template in the correct location
3. Test the application startup
4. Verify all routes are accessible
5. Test Excel export functionality
6. Test chatbot integration

## ✅ Code Quality
- All files follow the existing codebase patterns
- Consistent naming conventions
- Proper error handling
- Production-grade throttling for Excel exports
- Security policies implemented
- Audit logging configured
