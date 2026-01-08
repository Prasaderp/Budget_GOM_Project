"""Security policy for 76100167 chatbot queries"""

ALLOWED_COLUMNS = [
    'district', 'expenditure_2022_23', 'expenditure_2023_24', 'expenditure_2024_25',
    'budget_estimate', 'revised_estimate', 'budget_estimate_2026_27',
    'remarks', 'fiscal_year'
]

BLOCKED_OPERATIONS = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']

MAX_RESULTS = 100
