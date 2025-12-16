"""Preprocessing for 2075 schemes - minimal processing for sub-head expenditure queries"""

def preprocess_question(question: str) -> str:
    """Minimal preprocessing for 2075 - no designation/district translations needed"""
    if not question or not question.strip():
        return ""
    
    question = question.strip()
    question_lower = question.lower()
    
    # Year format normalization
    year_patterns = {
        '2021-22': '2021-22', '2021-2022': '2021-22',
        '2022-23': '2022-23', '2022-2023': '2022-23',
        '2023-24': '2023-24', '2023-2024': '2023-24',
        '2024-25': '2024-25', '2024-2025': '2024-25',
        '2025-26': '2025-26', '2025-2026': '2025-26',
        '2026-27': '2026-27', '2026-2027': '2026-27'
    }
    
    for pattern, standard in year_patterns.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    
    # Basic keyword validation
    budget_keywords = ['budget', 'expenditure', 'estimate', 'sub-head', 'sub head', 'अर्थसंकल्प', 'खर्च', 'व्यय']
    has_relevant_context = any(keyword in question_lower for keyword in budget_keywords)
    
    if not has_relevant_context:
        return question
    
    return question

