"""Government Advances (7610) main scheme

This module provides a unified Excel export for all 4 sub-schemas:
- 76100149: घरबांधणी अग्रिमे (House Building Advance)
- 76100158: मोटार वाहनांच्या खरेदीसाठी अग्रिमे (Motor Vehicle Purchase Advance)
- 76100167: इतर वाहनांच्या खरेदीसाठी अग्रिमे (Other Vehicle Purchase Advance)
- 76101871: वैयक्तीक संगणक यंत्रे खरेदीसाठी अग्रिमे (Personal Computer Purchase Advance)
"""
from .excel_export import export_7610_workbook_async

SCHEME_INFO = {"code": "7610", "name_en": "Government Advances", "name_mr": "शासकीय अग्रिम"}

__all__ = ["export_7610_workbook_async", "SCHEME_INFO"]

