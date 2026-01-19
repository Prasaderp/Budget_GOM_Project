Excel Export Implementation for Sub-scheme 20530242
Problem Description
Sub-scheme 20530242 requires complete Excel export functionality to match the architecture of 20530162. The key difference is that 20530242 has only 1 designation (Divisional Officer) in Class-3, while 20530162 has 7 designations across 3 class types. This significantly simplifies the row mappings but requires careful handling to avoid empty sections.

User Review Required
IMPORTANT

Row Mappings Need Verification: Since 20530242 has only 1 designation, the exact Excel template row mappings need to be verified against the actual template at 
excel_templates/s2053/subs/s20530242/Budget 20530242 for 2026-27.xlsx
. I'll use approximate mappings based on 20530162's pattern but you may need to adjust after reviewing the template.

Proposed Changes
Directory Structure Overview
s20530242/
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
└── shared/
    ├── __init__.py
    ├── services/
    │   ├── __init__.py
    │   ├── audit_service.py
    │   └── cache_service.py
    └── utils/
        ├── __init__.py
        ├── request_utils.py
        ├── response_utils.py
        └── validators.py
Configuration
[MODIFY] 
config.py
Add SHEET_NAMES constant for Excel sheet mapping:

# Excel template sheet names
SHEET_NAMES = {
    "budget_post_details": "Page 1",
    "post_status": "Page 2",
    "post_expenses": "Page 3",
    "unit_expenditure": "Page 4",
}
Excel Export Core
[NEW] 
init.py
Export the main service functions:

from .template_export_service import (
    export_original_workbook,
    export_original_workbook_async
)
__all__ = ["export_original_workbook", "export_original_workbook_async"]
[NEW] 
template_export_service.py
Main orchestration service with:

Template path resolution for 20530242
Fiscal year-aware data population
District processor mapping (8 districts)
Production-grade throttling via ExcelExportService
Sheet copying with style preservation
Populators
[NEW] 
populators/init.py
[NEW] 
budget_post_details.py
Key adaptations for 20530242:

Single designation: ['Divisional Officer'] for both Permanent and Temporary
Smaller row ranges: Since only 1 designation, each district block uses 1 row per category
DA rate calculation using fiscal year
HRA rate mapping with proper fallback
[NEW] 
post_status.py
Handles Class-3 only (20530242's single class in CLASS_DESIGNATIONS):

Column mapping for Filled/Vacant
Reduced row ranges per district
Fiscal year filtering
[NEW] 
post_expenses.py
Aggregates filled/vacant counts by class type with district component selection.

[NEW] 
unit_expenditure.py
Standard implementation with:

15 primary units
9 fiscal year fields
8 districts start row mapping
District Processors
Each processor defines:

DISTRICT_ROW_RANGES: Row ranges for each sheet type
SHEETS_TO_EXCLUDE: Sheets to remove for district-only exports
apply_district_filtering()
: Row/column filtering function
apply_abstract_filtering()
: Abstract sheet filtering
[NEW] Processors for all 8 districts
mumbai_city.py
mumbai_suburban.py
thane.py
palghar.py
raigad.py
ratnagiri.py
sindhudurg.py
dco_staff.py
Shared Services
[NEW] shared directory
Replicate the shared services structure from 20530162:

audit_service.py
: Logging for export actions
cache_service.py
: Export cache management
request_utils.py
: Request parameter extraction
response_utils.py
: Response formatting
validators.py
: Input validation
UI Integration
[MODIFY] 
ui_budget_details.py
Add import for excel_export and wire up export endpoints:

from .excel_export import export_original_workbook_async
Add three export endpoints:

/export-excel: Simple pandas-based CSV/Excel export
/export-original: Full template export with throttling
/export-sheet-only: Single sheet export
Edge Cases Covered
Edge Case	Handling
Empty data for fiscal year	Returns template with empty cells
Invalid fiscal year	Validates via validate_fiscal_year()
Missing template file	Falls back with HTTPException 500
District not found	Uses Mumbai City processor as fallback
Concurrent exports (500+ users)	Throttled via ExcelExportService
DCO Staff special handling	Dedicated processor with correct row ranges
Single designation edge	Only 1 row per category per district
Class-3 only filtering	Populator handles single class type
Verification Plan
Manual Verification
Start the server:

cd c:\Internship\Agenthix AI\GOM PROJECTS\BudgetMakingSystem\MAIN_PROJECT
python -m uvicorn src.main:app --reload --port 8000
Test export endpoints (after login as district assistant):

Navigate to: http://localhost:8000/ui/s20530242/budget-post-details
Click "Export Original" button → Should download 
.xlsx
 file
Click "Export Sheet Only" → Should download single-sheet file
Verify Excel content:

Open downloaded Excel
Check that data appears in correct cells for the logged-in district
Verify fiscal year filtering (switch fiscal year in UI, export again)
Test DCO Staff account:

Login as DCO Staff assistant
Export and verify DCO Staff-specific row ranges
NOTE

Since this involves Excel file operations and UI testing, automated tests are not practical. Please manually verify the export functionality after implementation.