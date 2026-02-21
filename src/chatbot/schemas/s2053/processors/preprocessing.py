import re

_MARATHI_MAP = {
    'मुळ वेतन': 'basic pay', 'मुळवेतन': 'basic pay', 'पगार': 'salary', 'वेतन': 'salary',
    'जिल्हाधिकारी': 'Collector', 'कलेक्टर': 'Collector',
    'अपर जिल्हाधिकारी': 'Additional Collector', 'अप्पर जिल्हाधिकारी': 'Additional Collector',
    'उपजिल्हाधिकारी': 'Deputy Collector', 'तहसीलदार': 'Tehsildar', 'तहसिलदार': 'Tehsildar',
    'चिटणीस': 'Chitnis', 'नायब तहसीलदार': 'Naib Tehsildar', 'नायब तहसिलदार': 'Naib Tehsildar',
    'लेखाधिकारी': 'Accounts Officer', 'सहा. लेखाधिकारी': 'Asst. Accounts Officer',
    'सहायक लेखाधिकारी': 'Asst. Accounts Officer', 'उपलेखापाल': 'Deputy Accountant',
    'लघुलेखक': 'Stenographer', 'स्टेनो': 'Stenographer',
    'अव्वल कारकून': 'Head Clerk (Awwal Karkun)', 'मुख्य कारकून': 'Head Clerk (Awwal Karkun)',
    'लिपिक': 'Clerk', 'कारकून': 'Clerk', 'क्लर्क': 'Clerk',
    'वाहन चालक': 'Vehicle Driver', 'ड्रायव्हर': 'Vehicle Driver', 'चालक': 'Vehicle Driver',
    'शिपाई': 'Peon/Naik/Havaldar/Watchman/Cleaner', 'चपरासी': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'नाईक': 'Peon/Naik/Havaldar/Watchman/Cleaner', 'हवालदार': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'वॉचमन': 'Peon/Naik/Havaldar/Watchman/Cleaner', 'स्वच्छक': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'विधी अधिकारी': 'Law Officer (Honorarium)', 'मंडळ अधिकारी': 'Divisional Officer',
    'भूमापक': 'Land Surveyor', 'वसूली कारकून': 'Recovery Clerk', 'आरेखक': 'Draftsman',
    'शिरस्तेदार': 'Shirastedar', 'टेलिफोन ऑपरेटर': 'Telephone Operator',
    'भरलेली पदे': 'filled posts', 'भरलेली': 'filled', 'रिक्त पदे': 'vacant posts',
    'रिक्त': 'vacant', 'मंजूर पदे': 'sanctioned posts', 'मंजूर': 'sanctioned',
    'कायमस्वरूपी': 'Permanent', 'तात्पुरते': 'Temporary',
    'खर्च': 'expenditure', 'व्यय': 'expense', 'वैद्यकिय': 'medical',
    'महागाई भत्ता': 'dearness allowance', 'भत्ते': 'allowances', 'भत्ता': 'allowance',
    'अर्थसंकल्प': 'budget', 'निधी': 'fund', 'वाटप': 'allocation',
    'एकूण': 'total', 'सरासरी': 'average', 'वार्षिक': 'annual',
    'कोकण विभाग': 'Konkan Division', 'कोकण': 'Konkan', 'मुंबई': 'Mumbai',
    'मुंबई शहर': 'Mumbai City', 'मुंबई उपनगर': 'Mumbai Suburban',
    'ठाणे': 'Thane', 'पालघर': 'Palghar', 'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg',
    'पद': 'post', 'पदे': 'posts', 'कर्मचारी': 'employee',
    'संगणक': 'computer', 'वर्ग': 'class', 'श्रेणी': 'category',
    'मूल वेतन': 'basic pay', 'बेसिक पे': 'basic pay', 'तनख्वाह': 'salary',
    'जिलाधिकारी': 'Collector', 'भरे हुए पद': 'filled posts', 'खाली पद': 'vacant posts',
    'रिक्त पद': 'vacant posts', 'चिकित्सा व्यय': 'medical expenses',
    'त्योहार अग्रिम': 'festival advance', 'बजट': 'budget', 'कुल': 'total',
    'स्थायी': 'Permanent', 'अस्थायी': 'Temporary',
    'आर्थिक वर्ष': 'fiscal year', 'वित्तीय वर्ष': 'fiscal year',
    'साल': 'year', 'वर्षासाठी': 'for year',
}

_DISTRICT_MAP = {
    'mumbai suburban': 'Mumbai Suburban', 'mumbai sub': 'Mumbai Suburban',
    'mumbai city': 'Mumbai City', 'thane': 'Thane', 'palghar': 'Palghar',
    'raigad': 'Raigad', 'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg',
    'dco staff': 'DCO Staff', 'dco': 'DCO Staff',
}

_AMBIGUOUS_DISTRICT_MAP = {
    'mumbai': ('Mumbai City', r'\bmumbai\b(?!\s+(?:suburban|city|division))'),
}

_CATEGORY_MAP = {
    'permanent': 'Permanent', 'perm': 'Permanent',
    'temporary': 'Temporary', 'temp': 'Temporary',
}

_CLASS_MAP = {
    'class 1 & 2': 'Class-1 & 2', 'class 1 and 2': 'Class-1 & 2',
    'class-1 & 2': 'Class-1 & 2', 'class 4': 'Class-4', 'class 3': 'Class-3',
    'class-4': 'Class-4', 'class-3': 'Class-3', 'class-2': 'Class-1 & 2',
    'class-1': 'Class-1 & 2', 'class4': 'Class-4', 'class3': 'Class-3',
}

# Pattern to detect fiscal years like 2025-26, 2032-33, 2025-2026, etc.
_FISCAL_YEAR_PATTERN = re.compile(r'(\d{4})[-/](\d{2,4})')

_UNIT_MAP = {
    'salary expenditure': '01- Salary', 'salary expenses': '01- Salary',
    'dearness allowance': '03- Dearness Allowance',
    'computer expenditure': 'Computer', 'computer expenses': 'Computer',
    'festival advance': 'Festival Advance',
    'telephone expenses': 'Telephone', 'electricity expenses': 'Electricity',
}

_PHRASE_SPELLING_MAP = {
    'basic salary': 'basic pay', 'base pay': 'basic pay',
    'gross salary': 'salary', 'net salary': 'salary',
}

_WORD_SPELLING_MAP = {
    'collecter': 'Collector', 'colector': 'Collector', 'collectar': 'Collector',
    'tehshildar': 'Tehsildar', 'tehsilldar': 'Tehsildar', 'tahsildar': 'Tehsildar',
    'expendeture': 'expenditure', 'budjet': 'budget',
}


def extract_fiscal_year(question: str) -> str:
    """Extract fiscal year from question in standard format like '2025-26'.
    Returns empty string if no fiscal year found in the question.
    """
    m = _FISCAL_YEAR_PATTERN.search(question)
    if not m:
        return ""
    y1 = m.group(1)
    y2 = m.group(2)
    # Normalize: '2025-2026' -> '2025-26', '2025-26' stays as-is
    if len(y2) == 4:
        y2 = y2[2:]
    return f"{y1}-{y2}"


def preprocess_question(question: str) -> str:
    if not question or not question.strip():
        return ""

    q = question.strip()

    sorted_marathi = sorted(_MARATHI_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for native, english in sorted_marathi:
        if native in q:
            q = q.replace(native, english, 1)

    q_lower = q.lower()

    for phrase, replacement in sorted(_PHRASE_SPELLING_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in q_lower:
            q = re.sub(re.escape(phrase), replacement, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    for variant, standard in sorted(_DISTRICT_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if variant in q_lower and standard not in q:
            q = re.sub(r'\b' + re.escape(variant) + r'\b', standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    for variant, (standard, pattern) in _AMBIGUOUS_DISTRICT_MAP.items():
        if variant in q_lower and standard not in q:
            q = re.sub(pattern, standard, q, count=1, flags=re.IGNORECASE)
            q_lower = q.lower()

    for variant, standard in sorted(_CATEGORY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        q = re.sub(r'\b' + re.escape(variant) + r'\b', standard, q, count=1, flags=re.IGNORECASE)

    for variant, standard in sorted(_CLASS_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if variant.lower() in q.lower() and standard not in q:
            q = re.sub(re.escape(variant), standard, q, count=1, flags=re.IGNORECASE)

    for variant, standard in sorted(_UNIT_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if variant in q.lower():
            q = re.sub(re.escape(variant), standard, q, count=1, flags=re.IGNORECASE)

    # Normalize fiscal year format in question to standard 'YYYY-YY' dash format
    # This ensures the fiscal year stays as e.g. '2025-26' and NOT converted to '2025_26'
    def _normalize_fy(m):
        y1 = m.group(1)
        y2 = m.group(2)
        if len(y2) == 4:
            y2 = y2[2:]
        return f"{y1}-{y2}"
    q = _FISCAL_YEAR_PATTERN.sub(_normalize_fy, q)

    words = q.split()
    for i, w in enumerate(words):
        wl = w.lower().strip('.,!?;:')
        if wl in _WORD_SPELLING_MAP:
            words[i] = w.replace(wl, _WORD_SPELLING_MAP[wl])
    q = ' '.join(words)

    q_lower = q.lower()
    if 'konkan division' in q_lower or 'konkan' in q_lower:
        q = re.sub(r'\bkonkan\b', 'Konkan Division', q, count=1, flags=re.IGNORECASE)
    if 'mumbai division' in q_lower:
        q = re.sub(r'\bmumbai division\b', 'Mumbai Division', q, count=1, flags=re.IGNORECASE)

    return q
