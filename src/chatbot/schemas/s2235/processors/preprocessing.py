import re
from typing import Dict

# Devanagari digit → ASCII digit mapping (covers ०-९)
_DEVANAGARI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')

_MARATHI_MAP: Dict[str, str] = {
    'सामाजिक सुरक्षा': 'social security', 'कल्याण': 'welfare',
    'वृद्धांचे कल्याण': 'welfare of elderly', 'वृद्ध': 'elderly',
    'खर्च': 'expenditure', 'व्यय': 'expenditure', 'प्रत्यक्ष खर्च': 'expenditure',
    'अर्थसंकल्पीय अनुदान': 'budget grant', 'अनुदान': 'grant',
    'सुधारित अनुदान': 'revised grant',
    'सुधारित अंदाज': 'revised estimate',
    'अर्थसंकल्पीय अंदाज': 'budget estimate',
    'अंदाजपत्रक': 'estimate', 'अर्थसंकल्प': 'budget',
    'एकूण': 'total', 'सरासरी': 'average', 'तुलना': 'comparison',
    'सर्व': 'all', 'जिल्हे': 'districts', 'जिल्हा': 'district',
    'विभाग': 'division', 'कोकण विभाग': 'Konkan Division',
    'विभागीय आयुक्त': 'Divisional Commissioner',
    'शेरा': 'remarks', 'टिपण्या': 'remarks',
    'आर्थिक वर्ष': 'fiscal year', 'वित्तीय वर्ष': 'fiscal year',
    'साल': 'year', 'वर्षासाठी': 'for year',
}

_DISTRICT_MAP: Dict[str, str] = {
    'मुंबई शहर': 'Mumbai City', 'मुंबई उपनगर': 'Mumbai Suburban',
    'ठाणे': 'Thane', 'पालघर': 'Palghar', 'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg',
    'जिल्हा संकलक कार्यालय कर्मचारी': 'DCO Staff',
    'विभागीय आयुक्त': 'Divisional Commissioner',
    'mumbai city': 'Mumbai City', 'mumbai suburban': 'Mumbai Suburban',
    'mumbai sub': 'Mumbai Suburban',
    'thane': 'Thane', 'palghar': 'Palghar', 'raigad': 'Raigad',
    'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg',
    'dco staff': 'DCO Staff', 'dco': 'DCO Staff',
    'divisional commissioner': 'Divisional Commissioner',
}

# Ambiguous district: 'mumbai' alone → Mumbai City (unless followed by suburban/city/division)
_AMBIGUOUS_DISTRICT_MAP = {
    'mumbai': ('Mumbai City', r'\bmumbai\b(?!\s+(?:suburban|city|division))'),
}

# Pattern to detect fiscal years like 2025-26, 2032-33, 2025-2026, etc.
_FISCAL_YEAR_PATTERN = re.compile(r'(\d{4})[-/](\d{2,4})')


def extract_fiscal_year(question: str) -> str:
    """Extract fiscal year from question in standard format like '2025-26'.
    Returns empty string if no fiscal year found in the question.
    """
    m = _FISCAL_YEAR_PATTERN.search(question)
    if not m:
        return ""
    y1 = m.group(1)
    y2 = m.group(2)
    if len(y2) == 4:
        y2 = y2[2:]
    return f"{y1}-{y2}"


def preprocess_question(question: str) -> str:
    """Normalize years, districts, and map Marathi UI terms to English."""
    if not question or not question.strip():
        return ""

    q = question.strip()

    # Convert Devanagari digits to ASCII FIRST
    q = q.translate(_DEVANAGARI_DIGITS)

    # Longest match first to avoid partial replacements for Marathi map
    for native, english in sorted(_MARATHI_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if native in q:
            q = q.replace(native, english)

    q_lower = q.lower()
    # Normalize district names (exact matches first)
    for variant, standard in sorted(_DISTRICT_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if variant.lower() in q_lower and standard not in q:
            pattern = r'\b' + re.escape(variant) + r'\b'
            q = re.sub(pattern, standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    # Handle ambiguous district names
    for variant, (standard, pattern) in _AMBIGUOUS_DISTRICT_MAP.items():
        if variant in q_lower and standard not in q:
            q = re.sub(pattern, standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    # Normalize fiscal year format in question to standard 'YYYY-YY' dash format
    def _normalize_fy(m):
        y1 = m.group(1)
        y2 = m.group(2)
        if len(y2) == 4:
            y2 = y2[2:]
        return f"{y1}-{y2}"

    q = _FISCAL_YEAR_PATTERN.sub(_normalize_fy, q)

    # Normalize Konkan division references
    if 'konkan division' in q.lower() or 'konkan' in q.lower():
        q = re.sub(r'\bkonkan\b', 'Konkan Division', q, count=1, flags=re.IGNORECASE)

    # Clean up whitespace
    q = re.sub(r"\s+", " ", q).strip()
    return q
