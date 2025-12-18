"""Preprocessing for 2075 schemes - Marathi → English mapping for sub-head expenditure queries."""
import re
from functools import lru_cache
from typing import Dict

_YEAR_PATTERNS: Dict[str, str] = {
    "2021-22": "2021-22", "2021-2022": "2021-22",
    "2022-23": "2022-23", "2022-2023": "2022-23",
    "2023-24": "2023-24", "2023-2024": "2023-24",
    "2024-25": "2024-25", "2024-2025": "2024-25",
    "2025-26": "2025-26", "2025-2026": "2025-26",
    "2026-27": "2026-27", "2026-2027": "2026-27",
}

_MARATHI_TO_ENGLISH: Dict[str, str] = {
    "उपशिर्ष": "sub head", "गौणशिर्ष": "sub head", "उपशिर्ष / गौणशिर्ष": "sub head", "उपशीर्षक": "sub head",
    "खर्च": "expenditure", "प्रत्यक्ष खर्च": "expenditure", "प्रत्यक्ष रक्कम": "expenditure", "प्रत्यक्ष रक्कमा": "expenditure",
    "अर्थसंकल्पीय अंदाज": "budget estimate", "सुधारित अंदाज": "revised estimate",
    "अर्थसंकल्पीय अंदाज (2025-26)": "budget estimate 2025-26", "सुधारित अंदाज (2025-26)": "revised estimate 2025-26",
    "अर्थसंकल्पीय अंदाज (2026-27)": "budget estimate 2026-27",
    "शेरा": "remarks", "नोंदी": "records", "संपादन": "edit", "अ. क्र": "sr no", "क्रमांक": "sr no",
    "२०२२-२३": "2022-23", "२०२३-२४": "2023-24", "२०२४-२५": "2024-25", "२०२५-२६": "2025-26", "२०२६-२७": "2026-27",
}

_BUDGET_KEYWORDS = [
    "budget", "expenditure", "estimate", "sub-head", "sub head",
    "अर्थसंकल्प", "खर्च", "व्यय", "अंदाज", "अर्थसंकल्पीय",
]

@lru_cache(maxsize=256)
def _translate_cached(text: str) -> str:
    """Cached translation for repeated terms - O(1) after first lookup"""
    for mr, en in sorted(_MARATHI_TO_ENGLISH.items(), key=lambda x: len(x[0]), reverse=True):
        if mr in text:
            return text.replace(mr, en)
    return text

def _apply_year_normalization(question: str) -> str:
    for pattern, standard in _YEAR_PATTERNS.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    return question

def _apply_marathi_mapping(question: str) -> str:
    # Longest match first to avoid partial replacements
    for marathi, english in sorted(_MARATHI_TO_ENGLISH.items(), key=lambda x: len(x[0]), reverse=True):
        if marathi in question:
            question = question.replace(marathi, english)
    return question

def preprocess_question(question: str) -> str:
    """Normalize years and map Marathi UI terms to English for 2075 sub-head queries."""
    if not question or not question.strip():
        return ""

    question = question.strip()
    question = _apply_year_normalization(question)
    question = _apply_marathi_mapping(question)

    question_lower = question.lower()
    has_relevant_context = any(keyword in question_lower for keyword in _BUDGET_KEYWORDS)
    if not has_relevant_context:
        return question

    # Add metadata hints for SQL generation
    metadata = []
    
    # Detect aggregation queries
    if any(kw in question_lower for kw in ['total', 'sum', 'एकूण', 'all', 'across']):
        metadata.append('REQUIRES_AGGREGATION')
    
    # Detect budget vs expenditure queries
    if any(kw in question_lower for kw in ['budget estimate', 'अर्थसंकल्पीय अंदाज']):
        metadata.append('BUDGET_ESTIMATE_QUERY')
    if any(kw in question_lower for kw in ['revised estimate', 'सुधारित अंदाज']):
        metadata.append('REVISED_QUERY')
    if any(kw in question_lower for kw in ['expenditure', 'खर्च', 'व्यय']):
        metadata.append('EXPENDITURE_QUERY')
    
    # Detect year-specific queries
    if any(year in question for year in ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26', '2026-27']):
        metadata.append('YEAR_SPECIFIC')
    
    # Detect sub-head specific queries
    if 'sub head' in question_lower or 'उपशिर्ष' in question or 'गौणशिर्ष' in question:
        metadata.append('SUBHEAD_SPECIFIC')
    
    # Append metadata hints
    if metadata:
        question = f"{question} [{', '.join(metadata)}]"

    question = re.sub(r"\s+", " ", question).strip()
    return question
