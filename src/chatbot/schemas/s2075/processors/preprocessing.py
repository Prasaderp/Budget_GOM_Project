"""Preprocessing for 2075 schemes - Marathi → English mapping and FY normalization."""
import re
from typing import Dict

# Devanagari digit → ASCII digit mapping (covers ०-९)
_DEVANAGARI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')

_MARATHI_MAP: Dict[str, str] = {
    "उपशिर्ष": "sub head", "गौणशिर्ष": "sub head", "उपशिर्ष / गौणशिर्ष": "sub head", "उपशीर्षक": "sub head",
    "खर्च": "expenditure", "प्रत्यक्ष खर्च": "expenditure", "प्रत्यक्ष रक्कम": "expenditure", "प्रत्यक्ष रक्कमा": "expenditure",
    "अर्थसंकल्पीय अंदाज": "budget estimate", "सुधारित अंदाज": "revised estimate",
    "शेरा": "remarks", "नोंदी": "records", "संपादन": "edit", "अ. क्र": "sr no", "क्रमांक": "sr no",
}

# Pattern to detect fiscal years like 2025-26, 2032-33, 2025-2026, etc.
_FISCAL_YEAR_PATTERN = re.compile(r'(\d{4})[-/](\d{2,4})')

def preprocess_question(question: str) -> str:
    """Normalize years and map Marathi UI terms to English."""
    if not question or not question.strip():
        return ""

    q = question.strip()

    # Convert Devanagari digits to ASCII FIRST — before any regex or map lookup
    q = q.translate(_DEVANAGARI_DIGITS)

    # Longest match first to avoid partial replacements
    for native, english in sorted(_MARATHI_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if native in q:
            q = q.replace(native, english)

    # Normalize fiscal year format in question to standard 'YYYY-YY' dash format
    def _normalize_fy(m):
        y1 = m.group(1)
        y2 = m.group(2)
        if len(y2) == 4:
            y2 = y2[2:]
        return f"{y1}-{y2}"
    
    q = _FISCAL_YEAR_PATTERN.sub(_normalize_fy, q)
    
    # Clean up whitespace
    q = re.sub(r"\s+", " ", q).strip()
    return q
