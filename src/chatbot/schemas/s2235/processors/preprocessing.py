"""Query preprocessing for scheme 2235 - Social Security and Welfare"""
import re
from functools import lru_cache
from typing import Dict

# 7 districts + DCO Staff for 2235
DISTRICT_MAPPING = {
    # Marathi → English
    'मुंबई शहर': 'Mumbai City', 'मुंबई उपनगर': 'Mumbai Suburban',
    'ठाणे': 'Thane', 'पालघर': 'Palghar', 'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg',
    'जिल्हा संकलक कार्यालय कर्मचारी': 'DCO Staff',
    # English variants
    'mumbai city': 'Mumbai City', 'mumbai suburban': 'Mumbai Suburban',
    'thane': 'Thane', 'palghar': 'Palghar', 'raigad': 'Raigad',
    'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg',
    'dco staff': 'DCO Staff', 'dco': 'DCO Staff'
}

VALID_DISTRICTS = {
    'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar',
    'Raigad', 'Ratnagiri', 'Sindhudurg', 'DCO Staff'
}

# Core Marathi-English translations for 2235 domain
TRANSLATIONS = {
    # Scheme-specific terms
    'सामाजिक सुरक्षा': 'social security', 'कल्याण': 'welfare',
    'वृद्धांचे कल्याण': 'welfare of elderly', 'वृद्ध': 'elderly',
    # Budget terms
    'खर्च': 'expenditure', 'व्यय': 'expenditure', 'प्रत्यक्ष खर्च': 'expenditure',
    'अर्थसंकल्पीय अनुदान': 'budget grant', 'अनुदान': 'grant',
    # Critical: Different terms for different subschemes
    'सुधारित अनुदान': 'revised grant',  # For 22350311/338/195
    'सुधारित अंदाज': 'revised estimate',  # For 22353408
    'अर्थसंकल्पीय अंदाज': 'budget estimate',
    'अंदाजपत्रक': 'estimate', 'अर्थसंकल्प': 'budget',
    # Division/Aggregation
    'एकूण': 'total', 'सरासरी': 'average', 'तुलना': 'comparison',
    'सर्व': 'all', 'जिल्हे': 'districts', 'जिल्हा': 'district',
    'विभाग': 'division', 'कोकण विभाग': 'Konkan Division',
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
    Preprocess user question for 2235 chatbot with bilingual support.
    
    Handles schema variations across subschemes.
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
    
    # Step 3: Normalize years (2022-23 → 2022_23 for SQL column names)
    for pattern, standard in YEAR_PATTERNS.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    
    # Step 4: Add metadata hints
    metadata = []
    
    # Detect aggregation (especially division totals)
    if any(kw in question_lower for kw in ['total', 'sum', 'एकूण', 'all', 'across', 'सर्व', 'division', 'विभाग', 'konkan', 'कोकण']):
        metadata.append('REQUIRES_AGGREGATION')
    
    # Detect budget/grant queries
    if any(kw in question_lower for kw in ['budget grant', 'अर्थसंकल्पीय अनुदान', 'budget_grant', 'अनुदान']):
        metadata.append('BUDGET_GRANT_QUERY')
    
    # Detect revised queries (both grant and estimate)
    if any(kw in question_lower for kw in ['revised', 'सुधारित']):
        metadata.append('REVISED_QUERY')
    
    # Detect budget estimate queries
    if any(kw in question_lower for kw in ['budget estimate', 'अर्थसंकल्पीय अंदाज', 'budget_estimate']):
        metadata.append('BUDGET_ESTIMATE_QUERY')
    
    # Detect expenditure queries
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
    budget_keywords = ['budget', 'expenditure', 'खर्च', 'अर्थसंकल्प', 'grant', 'अनुदान', 'social', 'welfare', 'कल्याण']
    has_context = any(kw in question_lower for kw in budget_keywords)
    
    return question if has_context else original
