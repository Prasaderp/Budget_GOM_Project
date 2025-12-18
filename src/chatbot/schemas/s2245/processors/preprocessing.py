"""Query preprocessing for scheme 2245 - Natural Calamity Relief"""
import re
from functools import lru_cache
from typing import Dict
from src.schemes.common.utils import GLOBAL_DISTRICTS_MR

# Build bilingual district mapping for 2245
DISTRICT_MAPPING = {v: k for k, v in GLOBAL_DISTRICTS_MR.items()}  # Marathi -> English
DISTRICT_MAPPING.update({  # English variants
    'mumbai city': 'Mumbai City', 'mumbai': 'Mumbai City',
    'mumbai suburban': 'Mumbai Suburban', 'mumbai sub': 'Mumbai Suburban',
    'thane': 'Thane', 'palghar': 'Palghar', 'raigad': 'Raigad',
    'ratnagiri': 'Ratnagiri', 'sindhudurg': 'Sindhudurg'
})

# Core Marathi-English translations for 2245 domain
TRANSLATIONS = {
    # Disaster types
    'पूर': 'flood', 'चक्रीवादळ': 'cyclone', 'भूकंप': 'earthquake',
    'अवर्षण': 'drought', 'दुष्काळ': 'drought',
    # Relief terms
    'अनुग्रह सहाय्य': 'ex-gratia assistance', 'राहत': 'relief',
    'निवारा': 'shelter', 'मदत': 'assistance', 'सहाय्य': 'assistance',
    # Budget terms
    'खर्च': 'expenditure', 'व्यय': 'expenditure',
    'अर्थसंकल्पीय अंदाजपत्रक': 'budget estimate',
    'सुधारीत अंदाजपत्रक': 'revised estimate',
    'अंदाजपत्रक': 'estimate', 'अर्थसंकल्प': 'budget',
    # Aggregation
    'एकूण': 'total', 'सरासरी': 'average', 'तुलना': 'comparison',
    # Years (Marathi digits)
    '२०२२-२३': '2022-23', '२०२३-२४': '2023-24', '२०२४-२५': '2024-25', '२०२६-२७': '2026-27',
}

# Year normalization patterns
YEAR_PATTERNS = {
    '2021-22': '2021_22', '2022-23': '2022_23', '2023-24': '2023_24',
    '2024-25': '2024_25', '2025-26': '2025_26', '2026-27': '2026_27'
}

@lru_cache(maxsize=256)
def _translate_cached(text: str) -> str:
    """Cached translation for repeated terms - O(1) after first lookup"""
    text_lower = text.lower()
    # Check district mapping first (case-insensitive)
    if text_lower in DISTRICT_MAPPING:
        return DISTRICT_MAPPING[text_lower]
    # Check translations (sorted by length for longest match first)
    for mr, en in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if mr in text:
            return text.replace(mr, en)
    return text

def preprocess_question(question: str) -> str:
    """
    Preprocess user question for 2245 chatbot with bilingual support.
    
    Logic:
    1. Validate input (return empty if invalid)
    2. Translate Marathi terms to English (districts, keywords)
    3. Normalize year formats (2022-23 -> 2022_23)
    4. Standardize district names to exact schema values
    5. Add metadata hints for SQL generation (filtered vs aggregated queries)
    
    Performance: O(n) single pass with cached lookups
    """
    if not question or not question.strip():
        return ""
    
    question = question.strip()
    original = question
    
    # Step 1: Translate Marathi terms (longest match first)
    for mr, en in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if mr in question:
            question = question.replace(mr, en)
    
    # Step 2: Normalize district names (case-insensitive)
    for variant, standard in sorted(DISTRICT_MAPPING.items(), key=lambda x: len(x[0]), reverse=True):
        if variant.lower() in question.lower() and standard not in question:
            pattern = r'\b' + re.escape(variant) + r'\b'
            question = re.sub(pattern, standard, question, count=1, flags=re.IGNORECASE)
    
    # Step 3: Normalize years (2022-23 -> 2022_23 for SQL column names)
    for pattern, standard in YEAR_PATTERNS.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    
    # Step 4: Add metadata hints for SQL generation
    question_lower = question.lower()
    metadata = []
    
    # Detect aggregation queries
    if any(kw in question_lower for kw in ['total', 'sum', 'एकूण', 'all districts', 'across']):
        metadata.append('REQUIRES_AGGREGATION')
    
    # Detect budget vs expenditure queries
    if any(kw in question_lower for kw in ['budget estimate', 'अर्थसंकल्पीय', 'budget_estimate']):
        metadata.append('BUDGET_QUERY')
    if any(kw in question_lower for kw in ['revised estimate', 'सुधारीत', 'revised_estimate']):
        metadata.append('REVISED_QUERY')
    if any(kw in question_lower for kw in ['expenditure', 'खर्च', 'व्यय', 'spending']):
        metadata.append('EXPENDITURE_QUERY')
    
    # Detect specific district queries
    if any(dist in question for dist in GLOBAL_DISTRICTS_MR.keys()):
        metadata.append('DISTRICT_FILTER')
    
    # Detect year-specific queries
    if any(year in question for year in ['2022_23', '2023_24', '2024_25', '2026_27']):
        metadata.append('YEAR_SPECIFIC')
    
    # Append metadata hints to guide SQL generation
    if metadata:
        question = f"{question} [{', '.join(metadata)}]"
    
    # Return original if no relevant context detected
    budget_keywords = ['budget', 'expenditure', 'खर्च', 'अर्थसंकल्प', 'relief', 'assistance', 'मदत']
    has_context = any(kw in question_lower for kw in budget_keywords)
    
    return question if has_context else original
