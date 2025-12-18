"""Query preprocessing for scheme 64010018 - Loans for Crop Production"""
import re
from functools import lru_cache
from typing import Dict

# 7 districts + DCO Staff for 64010018
DISTRICT_MAPPING = {
    # Marathi → English
    'मुंबई शहर': 'Mumbai City', 'मुंबई उपनगर': 'Mumbai Suburban',
    'ठाणे': 'Thane', 'पालघर': 'Palghar', 'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg',
    'जिल्हा संकलक कार्यालय कर्मचारी': 'DCO Staff',
    # English variants (lowercase for case-insensitive matching)
    'mumbai city': 'Mumbai City', 'mumbai suburban': 'Mumbai Suburban',
    'thane': 'Thane', 'palghar': 'Palghar', 'raigad': 'Raigad',
    'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg',
    'dco staff': 'DCO Staff', 'dco': 'DCO Staff'
}

VALID_DISTRICTS = {
    'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 
    'Raigad', 'Ratnagiri', 'Sindhudurg', 'DCO Staff'
}

# Core Marathi-English translations for 64010018 domain
TRANSLATIONS = {
    # Scheme-specific terms
    'कर्ज': 'loan', 'कर्जे': 'loans', 'पीक उत्पादन कर्ज': 'crop production loan',
    'पीक': 'crop', 'शेती': 'agriculture', 'शेतकरी': 'farmer',
    # Budget terms
    'खर्च': 'expenditure', 'व्यय': 'expenditure', 'प्रत्यक्ष खर्च': 'expenditure',
    'अर्थसंकल्पीय अनुदान': 'budget grant',
    'सुधारित अंदाज': 'revised estimate',
    'अर्थसंकल्पीय अंदाज': 'budget estimate',
    'अंदाजपत्रक': 'estimate', 'अर्थसंकल्प': 'budget',
    # Aggregation
    'एकूण': 'total', 'सरासरी': 'average', 'तुलना': 'comparison',
    'सर्व': 'all', 'जिल्हे': 'districts', 'जिल्हा': 'district',
    # Remarks
    'शेरा': 'remarks', 'टिपण्या': 'remarks',
    # Years (Marathi digits)
    '२०२२-२३': '2022-23', '२०२३-२४': '2023-24',
    '२०२४-२५': '2024-25', '२०२५-२६': '2025-26', '२०२६-२७': '2026-27',
}

# Year normalization patterns
YEAR_PATTERNS = {
    '2022-23': '2022_23', '2023-24': '2023_24', '2024-25': '2024_25',
    '2025-26': '2025_26', '2026-27': '2026_27'
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
    Preprocess user question for 64010018 chatbot with bilingual support.
    
    Validates district constraints and enriches with metadata.
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
    
    # Step 2: Normalize district names (case-insensitive)
    for variant, standard in sorted(DISTRICT_MAPPING.items(), key=lambda x: len(x[0]), reverse=True):
        if variant.lower() in question_lower and standard not in question and standard in VALID_DISTRICTS:
            pattern = r'\b' + re.escape(variant) + r'\b'
            question = re.sub(pattern, standard, question, count=1, flags=re.IGNORECASE)
    
    # Step 3: Normalize years (2022-23 → 2022_23 for SQL column names)
    for pattern, standard in YEAR_PATTERNS.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    
    # Step 4: Add metadata hints for SQL generation
    metadata = []
    
    # Detect aggregation queries
    if any(kw in question_lower for kw in ['total', 'sum', 'एकूण', 'all', 'across', 'सर्व']):
        metadata.append('REQUIRES_AGGREGATION')
    
    # Detect budget grant vs revised vs budget estimate queries
    if any(kw in question_lower for kw in ['budget grant', 'अर्थसंकल्पीय अनुदान', 'budget_grant']):
        metadata.append('BUDGET_GRANT_QUERY')
    if any(kw in question_lower for kw in ['revised estimate', 'सुधारित', 'revised_estimate']):
        metadata.append('REVISED_QUERY')
    if any(kw in question_lower for kw in ['budget estimate', 'अर्थसंकल्पीय अंदाज', 'budget_estimate_2026']):
        metadata.append('BUDGET_ESTIMATE_QUERY')
    if any(kw in question_lower for kw in ['expenditure', 'खर्च', 'व्यय', 'spending', 'प्रत्यक्ष']):
        metadata.append('EXPENDITURE_QUERY')
    
    # Detect specific district queries
    for district in VALID_DISTRICTS:
        if district.lower() in question_lower:
            metadata.append('DISTRICT_FILTER')
            break
    
    # Detect year-specific queries
    if any(year in question for year in ['2022_23', '2023_24', '2024_25', '2025_26', '2026_27']):
        metadata.append('YEAR_SPECIFIC')
    
    # Append metadata hints
    if metadata:
        question = f"{question} [{', '.join(metadata)}]"
    
    # Return original if no relevant context detected
    budget_keywords = ['budget', 'expenditure', 'खर्च', 'अर्थसंकल्प', 'loan', 'कर्ज', 'crop', 'पीक']
    has_context = any(kw in question_lower for kw in budget_keywords)
    
    return question if has_context else original
