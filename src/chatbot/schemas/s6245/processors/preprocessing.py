"""Query preprocessing for scheme 62450017 - Loans for Natural Calamities"""
import re
from functools import lru_cache
from typing import Dict
from src.schemes.s6245.subs.s62450017.config import KONKAN_DISTRICTS

# 5 districts ONLY for 62450017 (NO Mumbai City or Mumbai Suburban)
DISTRICT_MAPPING = {
    # Marathi → English
    'ठाणे': 'Thane', 'पालघर': 'Palghar', 'रायगड': 'Raigad',
    'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg',
    # English variants
    'thane': 'Thane', 'palghar': 'Palghar', 'raigad': 'Raigad',
    'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg'
}

# Valid district set for validation
VALID_DISTRICTS = set(KONKAN_DISTRICTS)

# Core Marathi-English translations for 62450017 domain
TRANSLATIONS = {
    # Loan-specific terms
    'कर्ज': 'loan', 'कर्जे': 'loans', 'इतर कर्जे': 'other loans',
    # Disaster types  
    'पूर': 'flood', 'चक्रीवादळ': 'cyclone', 'भूकंप': 'earthquake',
    'अवर्षण': 'drought', 'दुष्काळ': 'drought',
    'नैसर्गिक आपत्ती': 'natural calamity',
    # Budget terms
    'खर्च': 'expenditure', 'व्यय': 'expenditure',
    'अर्थसंकल्पीय अनुदान': 'budget grant',
    'सुधारित अंदाज': 'revised estimate',
    'अर्थसंकल्पीय अंदाज': 'budget estimate',
    'अंदाजपत्रक': 'estimate', 'अर्थसंकल्प': 'budget',
    # Aggregation  
    'एकूण': 'total', 'सरासरी': 'average', 'तुलना': 'comparison',
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
    Preprocess user question for 62450017 chatbot with bilingual support.
    
    CRITICAL: Validates 5-district constraint (NO Mumbai).
    """
    if not question or not question.strip():
        return ""
    
    question = question.strip()
    original = question
    question_lower = question.lower()
    
    # CRITICAL: Check for invalid districts (Mumbai City/Suburban)
    invalid_districts = ['mumbai city', 'mumbai suburban', 'mumbai', 'मुंबई शहर', 'मुंबई उपनगर', 'मुंबई']
    for invalid in invalid_districts:
        if invalid in question_lower:
            return f"{question} [INVALID_DISTRICT: This scheme covers ONLY 5 districts - Thane, Palghar, Raigad, Ratnagiri, Sindhudurg. Mumbai is NOT included.]"
    
    # Step 1: Translate Marathi terms (longest match first)
    for mr, en in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if mr in question:
            question = question.replace(mr, en)
    
    # Step 2: Normalize district names (case-insensitive, 5 districts only)
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
    if any(kw in question_lower for kw in ['total', 'sum', 'एकूण', 'all districts', 'across']):
        metadata.append('REQUIRES_AGGREGATION')
    
    # Detect budget grant vs revised vs budget estimate queries
    if any(kw in question_lower for kw in ['budget grant', 'अर्थसंकल्पीय अनुदान', 'budget_grant']):
        metadata.append('BUDGET_GRANT_QUERY')
    if any(kw in question_lower for kw in ['revised estimate', 'सुधारित', 'revised_estimate']):
        metadata.append('REVISED_QUERY')
    if any(kw in question_lower for kw in ['budget estimate', 'अर्थसंकल्पीय अंदाज', 'budget_estimate_2026']):
        metadata.append('BUDGET_ESTIMATE_QUERY')
    if any(kw in question_lower for kw in ['expenditure', 'खर्च', 'व्यय', 'spending']):
        metadata.append('EXPENDITURE_QUERY')
    
    # Detect specific district queries (validate against 5 districts)
    detected_district = None
    for district in VALID_DISTRICTS:
        if district.lower() in question_lower:
            detected_district = district
            metadata.append('DISTRICT_FILTER')
            break
    
    # Detect year-specific queries
    if any(year in question for year in ['2022_23', '2023_24', '2024_25', '2025_26', '2026_27']):
        metadata.append('YEAR_SPECIFIC')
    
    # Append metadata hints
    if metadata:
        question = f"{question} [{', '.join(metadata)}]"
    
    # Return original if no relevant context detected
    budget_keywords = ['budget', 'expenditure', 'खर्च', 'अर्थसंकल्प', 'loan', 'कर्ज']
    has_context = any(kw in question_lower for kw in budget_keywords)
    
    return question if has_context else original
