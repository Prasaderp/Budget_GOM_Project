"""Security policy for 2245 chatbot queries"""

ALLOWED_COLUMNS = [
    'fiscal_year', 'table_section_code', 'district',
    'expenditure_2022_23', 'expenditure_2023_24', 'expenditure_2024_25',
    'budget_estimate', 'revised_estimate', 'budget_estimate_2026_27',
]

BLOCKED_OPERATIONS = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']

MAX_RESULTS = 100
