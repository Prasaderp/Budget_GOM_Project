"""Preprocessing for 2215 schemes - Marathi → English mapping for district/account-head expenditure."""
import re
from typing import Dict


_YEAR_PATTERNS: Dict[str, str] = {
    "2021-22": "2021-22",
    "2021-2022": "2021-22",
    "2022-23": "2022-23",
    "2022-2023": "2022-23",
    "2023-24": "2023-24",
    "2023-2024": "2023-24",
    "2024-25": "2024-25",
    "2024-2025": "2024-25",
    "2025-26": "2025-26",
    "2025-2026": "2025-26",
    "2026-27": "2026-27",
    "2026-2027": "2026-27",
    "२०२२-२३": "2022-23",
    "२०२३-२४": "2023-24",
    "२०२४-२५": "2024-25",
    "२०२५-२६": "2025-26",
    "२०२६-२७": "2026-27",
}

# Marathi UI terms mapped to English concepts/columns for 2215 district expenditure with account heads.
_MARATHI_TO_ENGLISH: Dict[str, str] = {
    # Headings / table concepts
    "लेखाशिर्ष": "account head",
    "लेखाशिर्ष नाव": "account head",
    "जिल्हा कार्यालय": "district office",
    "प्रत्यक्ष रक्कमा": "expenditure",
    "प्रत्यक्ष रक्कम": "expenditure",
    "प्रत्यक्ष खर्च": "expenditure",
    "खर्च": "expenditure",
    "अर्थसंकल्पीय अंदाजपत्रक": "budget estimate",
    "अर्थसंकल्पीय अंदाजपत्रक (2025-26)": "budget estimate 2025-26",
    "अर्थसंकल्पीय अंदाजपत्रक (2026-27)": "budget estimate 2026-27",
    "सुधारीत अंदाजपत्रक": "revised demand",
    "सुधारीत अंदाजपत्रक मागणी": "revised demand 2025-26",
    "शेरा": "remarks",
    "अ. क्र": "sr no",
    "क्रमांक": "sr no",
    # Domain terms
    "कोंकण विभाग": "konkan division",
    "एकूण-कोकण विभाग": "total konkan division",
    "पाणी टंचाई": "water scarcity",
    "पाणी पुरवठा": "water supply",
    "जिल्हा परिषद": "zilla parishad",
    "पालघर": "Palghar",
    "ठाणे": "Thane",
    "रायगड": "Raigad",
    "रत्नागिरी": "Ratnagiri",
    "सिंधुदुर्ग": "Sindhudurg",
    # Account head codes often typed with Marathi text around them
    "२२१५ए१९५": "2215A195",
    "२२१५ए२०१": "2215A201",
    # District office prefixes (keep base district names intact)
    "मुख्य कार्यकारी अधिकारी": "Chief Executive Officer",
    "जिल्हाधिकारी": "Collector",
    # Common transliterated role query patterns
    "mukhya karyakari adhikari": "Chief Executive Officer",
}

_BUDGET_KEYWORDS = [
    "budget",
    "expenditure",
    "estimate",
    "account head",
    "district",
    "अर्थसंकल्प",
    "खर्च",
    "अंदाज",
    "लेखाशिर्ष",
]


def _apply_year_normalization(question: str) -> str:
    for pattern, standard in _YEAR_PATTERNS.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    return question


def _apply_marathi_mapping(question: str) -> str:
    for marathi, english in _MARATHI_TO_ENGLISH.items():
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

    question = re.sub(r"\s+", " ", question).strip()
    return question

