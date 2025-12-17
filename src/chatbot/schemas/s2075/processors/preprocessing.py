"""Preprocessing for 2075 schemes - Marathi → English mapping for sub-head expenditure queries."""
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
}

# Marathi UI terms mapped to English intent/columns for 2075 sub-head expenditure tables.
_MARATHI_TO_ENGLISH: Dict[str, str] = {
    # Headings / concepts
    "उपशिर्ष": "sub head",
    "गौणशिर्ष": "sub head",
    "उपशिर्ष / गौणशिर्ष": "sub head",
    "उपशीर्षक": "sub head",
    "खर्च": "expenditure",
    "प्रत्यक्ष खर्च": "expenditure",
    "प्रत्यक्ष रक्कम": "expenditure",
    "प्रत्यक्ष रक्कमा": "expenditure",
    "अर्थसंकल्पीय अंदाज": "budget estimate",
    "सुधारीत अंदाज": "revised estimate",
    "अर्थसंकल्पीय अंदाज (2025-26)": "budget estimate 2025-26",
    "सुधारीत अंदाज (2025-26)": "revised estimate 2025-26",
    "अर्थसंकल्पीय अंदाज (2026-27)": "budget estimate 2026-27",
    "शेरा": "remarks",
    "नोंदी": "records",
    "संपादन": "edit",
    "अ. क्र": "sr no",
    "क्रमांक": "sr no",
    # Years (Marathi digits or descriptors commonly typed)
    "२०२२-२३": "2022-23",
    "२०२३-२४": "2023-24",
    "२०२४-२५": "2024-25",
    "२०२५-२६": "2025-26",
    "२०२६-२७": "2026-27",
}

_BUDGET_KEYWORDS = [
    "budget",
    "expenditure",
    "estimate",
    "sub-head",
    "sub head",
    "अर्थसंकल्प",
    "खर्च",
    "व्यय",
    "अंदाज",
    "अर्थसंकल्पीय",
]


def _apply_year_normalization(question: str) -> str:
    for pattern, standard in _YEAR_PATTERNS.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    return question


def _apply_marathi_mapping(question: str) -> str:
    # Replace Marathi terms with their English counterparts for downstream SQL generation.
    for marathi, english in _MARATHI_TO_ENGLISH.items():
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

    # Collapse extra whitespace after replacements to keep prompts clean.
    question = re.sub(r"\s+", " ", question).strip()
    return question

