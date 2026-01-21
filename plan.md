S0029 Excel Export - Complete Implementation Plan
Overview
Scope:

Remove Section 3 & Section 4 dead code (unused sheets)
Implement complete Excel export for Section 1 (अर्थसंकल्पीय जिल्हा)
Files to Modify/Delete
Phase 1: Remove Section 3/4 Dead Code
[DELETE] Templates
templates/schemes/s0029/subs/s0029/section3_list.html
templates/schemes/s0029/subs/s0029/section4_list.html
[DELETE] Excel Export Files
src/schemes/s0029/subs/s0029/excel_export/arthsankalpiy_jilah 2.py
src/schemes/s0029/subs/s0029/excel_export/arthsankalpiy_jilah 3.py
src/schemes/s0029/subs/s0029/excel_export/arthsankalpiy_jilah 4.py
[MODIFY] 
config.py
Remove SECTION3_TABLE_SECTIONS (lines 162-271)
Remove 
get_section3_table_sections()
, 
get_section3_table_section()
 (lines 273-280)
Remove SECTION4_TABLE_SECTIONS and its functions (lines 282-291)
[MODIFY] 
models.py
Remove 
DistrictRevenue0029Section3
 class (lines 46-80)
Remove 
DistrictRevenue0029Section4
 class (lines 83-117)
[MODIFY] 
helpers.py
Remove imports for Section3/4 models and config functions
Remove check_edit_permission_for_section3() function
Remove ensure_fiscal_year_seeded_section3() function
Remove ensure_fiscal_year_seeded_section4() function
[MODIFY] 
router_ui.py
Remove imports for Section3/4 models and functions
Remove all /section3/* endpoints (lines 518-769) - 6 functions
Remove all /section4/* endpoints (lines 772-1023) - 6 functions
Phase 2: Implement Excel Export Feature
[NEW] 
init.py
Export the populator module.

[NEW] 
template_export_service.py
Load Excel template from excel_templates/s0029/subs/s0029/
Call 
populate_section1()
 from 
arthsankalpiy_jilah.py
Return populated Excel as StreamingResponse
[MODIFY] 
router_ui.py
Add export endpoint:

GET /export - Export full Excel with populated Section 1 data
Architecture
s0029/
└── excel_export/
    ├── __init__.py                    # Module exports
    ├── arthsankalpiy_jilah.py         # Populator for Sheet 1 (already done)
    └── template_export_service.py     # Service to generate Excel
NOTE

Sheet 2 (अर्थसंकल्पीय जिल्हा 2) uses Excel formulas referencing Sheet 1, so no populator needed.

Verification Plan
Delete Section 3/4 templates and verify no 404 errors on remaining pages
Test Section 1 and Section 5 (Jama Talmel) still work correctly
Export Excel and verify Sheet 1 data is populated correctly
Verify Sheet 2 shows calculated values from Sheet 1 formulas