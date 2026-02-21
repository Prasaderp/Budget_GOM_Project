"""Preprocessing for 2215 schemes - Marathi → English mapping and FY normalization."""
import re
from typing import Dict

# Devanagari digit → ASCII digit mapping (covers ०-९)
_DEVANAGARI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')

_MARATHI_MAP: Dict[str, str] = {
    "लेखाशिर्ष नाव": "account head", "लेखाशिर्ष": "account head",
    "जिल्हा कार्यालय": "district office",
    "प्रत्यक्ष रक्कमा": "expenditure", "प्रत्यक्ष रक्कम": "expenditure",
    "प्रत्यक्ष खर्च": "expenditure", "खर्च": "expenditure",
    "सुधारीत अंदाजपत्रक मागणी": "revised demand",
    "अर्थसंकल्पीय अंदाजपत्रक": "budget estimate",
    "सुधारीत अंदाजपत्रक": "revised demand",
    "शेरा": "remarks", "अ. क्र": "sr no", "क्रमांक": "sr no",
    "एकूण-कोकण विभाग": "total konkan division",
    "कोंकण विभाग": "konkan division",
    "पाणी टंचाई": "water scarcity", "पाणी पुरवठा": "water supply",
    "जिल्हा परिषद": "zilla parishad",
    "पालघर": "Palghar", "ठाणे": "Thane", "रायगड": "Raigad",
    "रत्नागिरी": "Ratnagiri", "सिंधुदुर्ग": "Sindhudurg",
    "मुख्य कार्यकारी अधिकारी": "Chief Executive Officer",
    "जिल्हाधिकारी": "Collector",
    "mukhya karyakari adhikari": "Chief Executive Officer",
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
