"""Security policy for 22350338 chatbot queries"""

ALLOWED_COLUMNS = [
    'fiscal_year', 'scheme_code', 'sub_scheme_code', 'district',
    'expenditure_2022_23', 'expenditure_2023_24', 'expenditure_2024_25',
    'budget_grant_2025_26', 'revised_grant_2025_26', 'budget_estimate_2026_27',
]

BLOCKED_OPERATIONS = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']

MAX_RESULTS = 100
