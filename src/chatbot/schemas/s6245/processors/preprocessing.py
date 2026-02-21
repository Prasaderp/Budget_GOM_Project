import re

_MARATHI_MAP = {
    'खर्च': 'expenditure', 'व्यय': 'expense', 
    'अर्थसंकल्प': 'budget', 'निधी': 'fund', 'वाटप': 'allocation',
    'एकूण': 'total', 'सरासरी': 'average', 'वार्षिक': 'annual',
    'कोकण विभाग': 'Konkan Division', 'कोकण': 'Konkan',
    'ठाणे': 'Thane', 'पालघर': 'Palghar', 'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg',
    'कर्ज': 'loan', 'कर्जे': 'loans',
    'नैसर्गिक आपत्ती': 'natural calamity', 'आपत्ती': 'calamity',
    'निवारण': 'relief', 'वितरण': 'distribution',
    'आर्थिक वर्ष': 'fiscal year', 'वित्तीय वर्ष': 'fiscal year',
    'वर्षासाठी': 'for year'
}

_DISTRICT_MAP = {
    'thane': 'Thane', 'palghar': 'Palghar',
    'raigad': 'Raigad', 'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg'
}

_FISCAL_YEAR_PATTERN = re.compile(r'(\d{4})[-/](\d{2,4})')

def extract_fiscal_year(question: str) -> str:
    m = _FISCAL_YEAR_PATTERN.search(question)
    if not m:
        return ""
    y1, y2 = m.group(1), m.group(2)
    return f"{y1}-{y2[2:]}" if len(y2) == 4 else f"{y1}-{y2}"

def preprocess_question(question: str) -> str:
    if not question or not (q := question.strip()):
        return ""

    for native, english in sorted(_MARATHI_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if native in q:
            q = q.replace(native, english, 1)

    q_lower = q.lower()
    for variant, standard in sorted(_DISTRICT_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if variant in q_lower and standard not in q:
            q = re.sub(rf'\b{re.escape(variant)}\b', standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    def _normalize_fy(m):
        y1, y2 = m.group(1), m.group(2)
        return f"{y1}-{y2[2:]}" if len(y2) == 4 else f"{y1}-{y2}"

    q = _FISCAL_YEAR_PATTERN.sub(_normalize_fy, q)

    if 'konkan division' in q.lower() or 'konkan' in q.lower():
        q = re.sub(r'\bkonkan\b', 'Konkan Division', q, count=1, flags=re.IGNORECASE)

    return q
