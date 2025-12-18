"""Query preprocessing for scheme 0029 - Land Revenue Receipts with multi-table routing"""
import re
from functools import lru_cache

# 6 Konkan districts ONLY (NO Palghar, NO DCO Staff)
DISTRICT_MAPPING = {
    # Marathi → English
    'मुंबई शहर': 'Mumbai City', 'मुंबई उपनगर': 'Mumbai Suburban', 'मुंबई उप-धार': 'Mumbai Suburban',
    'ठाणे': 'Thane', 'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg',
    # English variants
    'mumbai city': 'Mumbai City', 'mumbai suburban': 'Mumbai Suburban',
    'thane': 'Thane', 'raigad': 'Raigad',
    'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg'
}

VALID_DISTRICTS = {
    'Mumbai City', 'Mumbai Suburban', 'Thane', 
    'Raigad', 'Ratnagiri', 'Sindhudurg'
}

# Core Marathi-English translations for 0029 domain
TRANSLATIONS = {
    # Administrative terms
    'जिल्हा': 'district', 'उपलेखाशिर्ष': 'district',
    'अर्थसंकल्पीय जिल्हा': 'budget district',
    'तक्ता विभाग': 'table section',
    # Revenue terms (जमा means both "receipt" AND "deposit"!)
    'जमा': 'receipt', 'महसूल': 'revenue', 'जमा रकमा': 'receipts',
    'प्रत्यक्ष जमा': 'actual receipt', 'प्रत्यक्ष': 'actual',
    'भूमि महसूल': 'land revenue', 'जमीन महसूल': 'land revenue',
    # Budget/estimate terms
    'अर्थसंकल्पीय जमा अंदाज': 'budget estimate',
    'सुधारीत जमा अंदाज': 'revised estimate',
    'अंदाजपत्रक': 'estimate',
    # JamaTalmel specific (CRITICAL: जमा also means "deposit" here!)
    'जमा ताळमेळ': 'jama talmel', 'ताळमेळ': 'reconciliation',
    # When in JamaTalmel context, जमा = deposit
    # Aggregation
    'एकूण': 'total', 'सरासरी': 'average',
    'सर्व': 'all', 'जिल्हे': 'districts',
    # Remarks
    'शेरा': 'remarks',
    # Years (historical range 2011-2021)
    '२०११-१२': '2011-12', '२०१२-१३': '2012-13', '२०१३-१४': '2013-14',
    '२०१४-१५': '2014-15', '२०१५-१६': '2015-16', '२०१६-१७': '2016-17',
    '२०१७-१८': '2017-18', '२०१८-१९': '2018-19', '२०१९-२०': '2019-20',
    '२०२०-२१': '2020-21', '२०२१-२२': '2021-22',
}

# Year normalization patterns
YEAR_PATTERNS = {
    '2011-12': '2011_12', '2012-13': '2012_13', '2013-14': '2013_14',
    '2014-15': '2014_15', '2015-16': '2015_16', '2016-17': '2016_17',
    '2017-18': '2017_18', '2018-19': '2018_19', '2019-20': '2019_20',
    '2020-21': '2020_21', '2021-22': '2021_22'
}

@lru_cache(maxsize=256)
def _translate_cached(text: str) -> str:
    """Cached translation for repeated terms - O(1) after first lookup"""
    text_lower = text.lower()
    if text_lower in DISTRICT_MAPPING:
        return DISTRICT_MAPPING[text_lower]
    for mr, en in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if mr in text:
            return text.replace(mr, en)
    return text

def preprocess_question(question: str) -> str:
    """
    Preprocess user question for 0029 chatbot with multi-table routing.
    
    Adds table hints based on year ranges and keywords.
    """
    if not question or not question.strip():
        return ""
    
    question = question.strip()
    original = question
    question_lower = question.lower()
    
    # Step 1: Translate Marathi terms (longest match first)
    for mr, en in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if mr in question:
            question = question.replace(mr, en)
    
    # Step 2: Normalize district names
    for variant, standard in sorted(DISTRICT_MAPPING.items(), key=lambda x: len(x[0]), reverse=True):
        if variant.lower() in question_lower and standard not in question and standard in VALID_DISTRICTS:
            pattern = r'\b' + re.escape(variant) + r'\b'
            question = re.sub(pattern, standard, question, count=1, flags=re.IGNORECASE)
    
    # Step 3: Normalize years (2017-18 → 2017_18 for SQL column names)
    for pattern, standard in YEAR_PATTERNS.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    
    # Step 4: Add metadata hints including TABLE routing
    metadata = []
    
    # Table routing hints based on year and keywords
    if any(kw in question_lower for kw in ['deposit', 'reconciliation', 'ताळमेळ', 'jama talmel']):
        metadata.append('JAMA_TALMEL_TABLE')
    elif any(year in question for year in ['2017', '2018', '2019', '2020', '2021']):
        metadata.append('TABLE_1')
    elif any(year in question for year in ['2014', '2015', '2016']):
        metadata.append('TABLE_3')
    elif any(year in question for year in ['2011', '2012', '2013']):
        metadata.append('TABLE_4')
    
    # Detect aggregation
    if any(kw in question_lower for kw in ['total', 'sum', 'एकूण', 'all', 'सर्व']):
        metadata.append('REQUIRES_AGGREGATION')
    
    # Detect receipt/revenue queries
    if any(kw in question_lower for kw in ['receipt', 'revenue', 'जमा', 'महसूल', 'actual', 'प्रत्यक्ष']):
        metadata.append('REVENUE_QUERY')
    
    # Detect budget/estimate queries
    if any(kw in question_lower for kw in ['budget', 'estimate', 'अर्थसंकल्पीय', 'अंदाज']):
        metadata.append('BUDGET_QUERY')
    
    # Detect specific district queries (only valid for Table 1!)
    for district in VALID_DISTRICTS:
        if district.lower() in question_lower:
            metadata.append('DISTRICT_FILTER')
            break
    
    # Detect year-specific queries
    if any(year in question for year in YEAR_PATTERNS.values()):
        metadata.append('YEAR_SPECIFIC')
    
    # Append metadata hints
    if metadata:
        question = f"{question} [{', '.join(metadata)}]"
    
    # Return original if no relevant context detected
    revenue_keywords = ['revenue', 'receipt', 'महसूल', 'जमा', 'budget', 'अर्थसंकल्पीय', 'district', 'जिल्हा']
    has_context = any(kw in question_lower for kw in revenue_keywords)
    
    return question if has_context else original
