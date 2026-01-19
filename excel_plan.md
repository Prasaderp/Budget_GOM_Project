Excel Export Implementation Plan - Sub-scheme 20290046
Problem Description
Sub-scheme 20290046 (District Administration - Charged) requires complete Excel export functionality matching the architecture of s20530028 but using hardcoded row mappings (like s20530387) due to merged cells in the Excel template.

Key Characteristics:

7 Districts + DCO Staff
9 Designations: Deputy Collector/Expert Officer, City Architect, Assistant City Architect, Head Clerk, Divisional Officer, Clerk, Vehicle Driver, Notice Bearer, Peon
3 Class Types: Class-1 & 2, Class-3, Class-4
9 Primary Units for expenditure
4 Excel Sheets: Page 1-4 (Budget Post Details, Post Status, Post Expenses, Unit Expenditure)
User Review Required
IMPORTANT

Row Mappings Need User Verification: Based on the uploaded images, I have derived the following row mappings for Mumbai City. These MUST be verified against the actual Excel template before implementation.

Mumbai City - Budget Post Details (Page 1)
Permanent Section:

Row	Designation
7	Deputy Collector/Expert Officer (Class-1 & 2)
9	Head Clerk (Class-3)
10	Clerk (Class-3)
11	Vehicle Driver (Class-3)
13	Notice Bearer (Class-4)
14	Peon (Class-4)
Temporary Section:

Row	Designation
21	Deputy Collector/Expert Officer (Class-1 & 2)
22	City Architect (Class-1 & 2)
23	Assistant City Architect (Class-1 & 2)
25	Head Clerk (Class-3)
26	Divisional Officer (Class-3)
27	Clerk (Class-3)
28	Vehicle Driver (Class-3)
30	Peon (Class-4)
CAUTION

Excel Template Required: The template file must be placed at excel_templates/s2029/subs/s20290046/Budget 20290046 for 2026-27.xlsx before testing.

Proposed Changes
Directory Structure
s20290046/
├── excel_export/
│   ├── __init__.py
│   ├── template_export_service.py
│   ├── populators/
│   │   ├── __init__.py
│   │   ├── budget_post_details.py
│   │   ├── post_status.py
│   │   ├── post_expenses.py
│   │   └── unit_expenditure.py
│   └── processors/
│       ├── __init__.py
│       ├── mumbai_city.py
│       ├── mumbai_suburban.py
│       ├── thane.py
│       ├── palghar.py
│       ├── raigad.py
│       ├── ratnagiri.py
│       ├── sindhudurg.py
│       └── dco_staff.py
Configuration
[MODIFY] 
config.py
Add SHEET_NAMES and SCHEME_DISTRICTS:

SHEET_NAMES = {
    "budget_post_details": "Page 1",
    "post_status": "Page 2",
    "post_expenses": "Page 3",
    "unit_expenditure": "Page 4",
}
SCHEME_DISTRICTS = [
    'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar',
    'Raigad', 'Ratnagiri', 'Sindhudurg', 'DCO Staff'
]
SCHEME_DISTRICTS_MR = {
    'Mumbai City': 'मुंबई शहर',
    'Mumbai Suburban': 'मुंबई उपनगर',
    'Thane': 'ठाणे',
    'Palghar': 'पालघर',
    'Raigad': 'रायगड',
    'Ratnagiri': 'रत्नागिरी',
    'Sindhudurg': 'सिंधुदुर्ग',
    'DCO Staff': 'जिल्हा संकलक कार्यालय कर्मचारी'
}
Excel Export Core
[NEW] 
init.py
Export main service functions.

[NEW] 
template_export_service.py
Main orchestration service adapted from s20530028 with:

Template path resolution for 20290046
Fiscal year-aware data population
District processor mapping (8 units)
Production-grade throttling via ExcelExportService
Populators
[NEW] 
budget_post_details.py
Uses hardcoded row mappings per district (like s20530387):

MUMBAI_CITY_PERMANENT_MAP = {
    "Deputy Collector/Expert Officer": 7,
    "Head Clerk": 9,
    "Clerk": 10,
    "Vehicle Driver": 11,
    "Notice Bearer": 13,
    "Peon": 14,
}
MUMBAI_CITY_TEMPORARY_MAP = {
    "Deputy Collector/Expert Officer": 21,
    "City Architect": 22,
    "Assistant City Architect": 23,
    "Head Clerk": 25,
    "Divisional Officer": 26,
    "Clerk": 27,
    "Vehicle Driver": 28,
    "Peon": 30,
}
# Similar maps for other districts with offsets...
District Block Structure (approximate row ranges):

District	Perm Start	Temp Start
Mumbai City	7	21
Mumbai Suburban	(TBD)	(TBD)
Thane	(TBD)	(TBD)
Palghar	(TBD)	(TBD)
Raigad	(TBD)	(TBD)
Ratnagiri	(TBD)	(TBD)
Sindhudurg	(TBD)	(TBD)
DCO Staff	(TBD)	(TBD)
[NEW] 
post_status.py
Handles Class-based columns with per-district row offsets:

Filled columns: C (Class-1&2), D (Class-3), E (Class-4)
Vacant columns: G (Class-1&2), H (Class-3), I (Class-4)
[NEW] 
post_expenses.py
Per-district class row mappings and fixed expense rows.

[NEW] 
unit_expenditure.py
9 primary units × 8 districts with fiscal year fields.

District Processors
Each processor defines:

DISTRICT_ROW_RANGES: Row ranges for each sheet type
SHEETS_TO_EXCLUDE: Sheets to remove for district-only exports
apply_district_filtering(): Row filtering function
apply_abstract_filtering(): Abstract sheet filtering
[NEW] Processors for all 8 districts
mumbai_city.py, mumbai_suburban.py, thane.py, palghar.py
raigad.py, ratnagiri.py, sindhudurg.py, 
dco_staff.py
UI Integration
[MODIFY] 
ui_budget_details.py
Wire up export endpoints:

-# TODO: Implement Excel export when template is ready
-# from src.excel_template_export import export_original_workbook
+from .excel_export import export_original_workbook_async
Update /export-original and /export-sheet-only endpoints to use the new service.

[MODIFY] Similar updates for:
ui_post_status.py
ui_post_expenses.py
ui_unit_expenditure.py
Edge Cases Covered
Edge Case	Handling
Empty data for fiscal year	Returns template with empty cells
Invalid fiscal year	Validates via get_fiscal_year_from_request()
Missing template file	Falls back with HTTPException 500
District not found	Uses Mumbai City processor as fallback
Concurrent exports (500+ users)	Throttled via ExcelExportService
Merged cells in template	Hardcoded row mappings skip merged rows
Missing designation in DB	Warning logged, data skipped
Verification Plan
Manual Verification
Server Startup:
cd c:\Internship\Agenthix AI\GOM PROJECTS\BudgetMakingSystem\MAIN_PROJECT
uvicorn main:app --reload --port 8000
Test Export Endpoints (after login as district assistant):

Navigate to: http://localhost:8000/ui/s20290046/budget-post-details
Click "Export Original" → Should download .xlsx file
Click "Export Sheet Only" → Should download single-sheet file
Verify Excel Content:

Open downloaded Excel
Check data appears in correct cells for logged-in district
Verify fiscal year filtering (switch fiscal year in UI, export again)
Test All Districts:

Login as different district assistants
Export and verify district-specific row ranges
Test DCO Staff:

Login as DCO Staff assistant
Export and verify DCO Staff-specific row ranges
NOTE

Since this involves Excel file operations and UI testing, automated tests are not practical. Please manually verify the export functionality after implementation.