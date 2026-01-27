"""Social Security and Welfare (2235) main scheme

This module provides a unified Excel export for all 4 sub-schemas:
- 22353195: आत्महत्या केलेल्या शेतकऱ्यांच्या वारसांना वित्तीय सहाय्य
- 22350338: ठेव संलग्न विमा योजना
- 22350311: आपघातग्रस्तांना आर्थिक मदत
- 22353408: मुक्त वेठबिगारांसाठी पुनर्वसन योजना
"""
from .excel_export import export_2235_workbook_async

SCHEME_INFO = {"code": "2235", "name_en": "Social Security and Welfare", "name_mr": "सामाजिक सुरक्षा व कल्याण"}

__all__ = ["export_2235_workbook_async", "SCHEME_INFO"]

