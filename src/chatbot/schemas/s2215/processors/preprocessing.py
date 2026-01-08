"""Preprocessing for 2215 schemes - Marathi → English mapping for district/account-head expenditure."""
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
    "२०२२-२३": "2022-23", "२०२३-२४": "2023-24",
    "२०२४-२५": "2024-25", "२०२५-२६": "2025-26", "२०२६-२७": "2026-27",
}

_MARATHI_TO_ENGLISH: Dict[str, str] = {
    "लेखाशिर्ष": "account head", "लेखाशिर्ष नाव": "account head",
    "जिल्हा कार्यालय": "district office",
    "प्रत्यक्ष रक्कमा": "expenditure", "प्रत्यक्ष रक्कम": "expenditure",
    "प्रत्यक्ष खर्च": "expenditure", "खर्च": "expenditure",
    "अर्थसंकल्पीय अंदाजपत्रक": "budget estimate",
    "अर्थसंकल्पीय अंदाजपत्रक (2025-26)": "budget estimate 2025-26",
    "अर्थसंकल्पीय अंदाजपत्रक (2026-27)": "budget estimate 2026-27",
    "सुधारीत अंदाजपत्रक": "revised demand",
    "सुधारीत अंदाजपत्रक मागणी": "revised demand 2025-26",
    "शेरा": "remarks", "अ. क्र": "sr no", "क्रमांक": "sr no",
    "कोंकण विभाग": "konkan division", "एकूण-कोकण विभाग": "total konkan division",
    "पाणी टंचाई": "water scarcity", "पाणी पुरवठा": "water supply",
    "जिल्हा परिषद": "zilla parishad",
    "पालघर": "Palghar", "ठाणे": "Thane", "रायगड": "Raigad",
    "रत्नागिरी": "Ratnagiri", "सिंधुदुर्ग": "Sindhudurg",
    "२२१५ए१९५": "2215A195", "२२१५ए२०१": "2215A201",
    "मुख्य कार्यकारी अधिकारी": "Chief Executive Officer",
    "जिल्हाधिकारी": "Collector",
    "mukhya karyakari adhikari": "Chief Executive Officer",
}

_BUDGET_KEYWORDS = [
    "budget", "expenditure", "estimate", "account head", "district",
    "अर्थसंकल्प", "खर्च", "अंदाज", "लेखाशिर्ष",
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
    """Normalize years and map Marathi UI terms to English for 2215 account-head queries."""
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
    if any(kw in question_lower for kw in ['total', 'sum', 'एकूण', 'all', 'across', 'konkan division']):
        metadata.append('REQUIRES_AGGREGATION')
    
    # Detect account head queries
    if any(code in question_lower for code in ['2215a195', '2215a201', '2215 a 195', '2215 a 201']):
        metadata.append('ACCOUNT_HEAD_SPECIFIC')
    
    # Detect budget vs expenditure queries
    if any(kw in question_lower for kw in ['budget estimate', 'अर्थसंकल्पीय अंदाजपत्रक']):
        metadata.append('BUDGET_ESTIMATE_QUERY')
    if any(kw in question_lower for kw in ['revised demand', 'सुधारित अंदाजपत्रक']):
        metadata.append('REVISED_DEMAND_QUERY')
    if any(kw in question_lower for kw in ['expenditure', 'खर्च', 'व्यय']):
        metadata.append('EXPENDITURE_QUERY')
    
    # Detect district queries (5 Konkan districts)
    konkan_districts = ['thane', 'palghar', 'raigad', 'ratnagiri', 'sindhudurg']
    if any(dist in question_lower for dist in konkan_districts):
        metadata.append('DISTRICT_FILTER')
    
    # Detect year-specific queries
    if any(year in question for year in ['2022-23', '2023-24', '2024-25', '2025-26', '2026-27']):
        metadata.append('YEAR_SPECIFIC')
    
    # Append metadata hints
    if metadata:
        question = f"{question} [{', '.join(metadata)}]"

    question = re.sub(r"\s+", " ", question).strip()
    return question

