import re

_MARATHI_MAP = {
    'खर्च': 'expenditure',
    'अंदाज': 'budget estimate',
    'सुधारित': 'revised estimate',
    'जिल्हानिहाय': 'district',
    'अर्थसंकल्पीय': 'budget',
    'पालघर': 'Palghar',
    'ठाणे': 'Thane',
    'मुंबई शहर': 'Mumbai City',
    'मुंबई उपनगर': 'Mumbai Suburban',
    'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri',
    'सिंधुदुर्ग': 'Sindhudurg',
    'कोकण विभाग': 'Konkan Division',
    'कोकण': 'Konkan Division',
    'मुंबई विभाग': 'Mumbai Division',
    'dco': 'DCO Staff',
    'डीडीसीओ': 'DCO Staff',
    'आर्थिक वर्ष': 'fiscal year',
    'वित्तीय वर्ष': 'fiscal year',
}

_DISTRICT_MAP = {
    'mumbai suburban': 'Mumbai Suburban',
    'mumbai sub': 'Mumbai Suburban',
    'mumbai city': 'Mumbai City',
    'thane': 'Thane',
    'palghar': 'Palghar',
    'raigad': 'Raigad',
    'ratnagiri': 'Ratnagiri',
    'sindhudurg': 'Sindhudurg',
    'dco staff': 'DCO Staff',
    'dco': 'DCO Staff',
}

_AMBIGUOUS_DISTRICT_MAP = {
    'mumbai': ('Mumbai City', r'\bmumbai\b(?!\s+(?:suburban|city|division))'),
}

_FISCAL_YEAR_PATTERN = re.compile(r'(\d{4})[-_](\d{2,4})')

_SPELLING_MAP = {
    'mumbai ctiy': 'Mumbai City',
    'mumbai suburbanan': 'Mumbai Suburban',
    'suburb': 'Suburban',
}

def preprocess_question(question: str) -> str:
    if not question or not question.strip():
        return ""

    q = question.strip()

    # Marathi translations (longest match first)
    sorted_marathi = sorted(_MARATHI_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for native, english in sorted_marathi:
        if native in q:
            q = q.replace(native, english, 1)

    q_lower = q.lower()

    # Spelling corrections
    for variant, standard in sorted(_SPELLING_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if variant in q_lower:
            q = re.sub(re.escape(variant), standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    # District normalization
    for variant, standard in sorted(_DISTRICT_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if variant in q_lower and standard not in q:
            q = re.sub(r'\b' + re.escape(variant) + r'\b', standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    # Ambiguous district handling
    for variant, (standard, pattern) in _AMBIGUOUS_DISTRICT_MAP.items():
        if variant in q_lower and standard not in q:
            q = re.sub(pattern, standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    # FY normalization to keep dash format (e.g. 2025-26)
    def _normalize_fy(m):
        y1 = m.group(1)
        y2 = m.group(2)
        if len(y2) == 4:
            y2 = y2[2:]
        return f"{y1}-{y2}"
    
    q = _FISCAL_YEAR_PATTERN.sub(_normalize_fy, q)

    # Division normalizations
    if 'konkan division' in q_lower or 'konkan' in q_lower:
        q = re.sub(r'\bkonkan\b', 'Konkan Division', q, count=1, flags=re.IGNORECASE)
    if 'mumbai division' in q_lower:
        q = re.sub(r'\bmumbai division\b', 'Mumbai Division', q, count=1, flags=re.IGNORECASE)

    return q
