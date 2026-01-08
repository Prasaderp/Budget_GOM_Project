"""Security policy for 22350311 chatbot queries"""

ALLOWED_COLUMNS = [
    'district', 'expenditure_2022_23', 'expenditure_2023_24',
    'budget_grant_2024_25', 'revised_grant_2025_26',
    'budget_estimate_2026_27', 'remarks', 'fiscal_year'
]

BLOCKED_OPERATIONS = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']

MAX_RESULTS = 100
