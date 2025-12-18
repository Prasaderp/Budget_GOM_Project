"""Security policy for 0029 chatbot queries - all 4 tables"""

# Combined allowed columns from all 4 tables
ALLOWED_COLUMNS = [
    # Table 1 (district_revenue_0029) columns
    'district', 'actual_2017_18', 'actual_2018_19', 'actual_2019_20',
    'budget_estimate_2020_21', 'revised_estimate_2020_21', 'budget_estimate_2021_22',
    # Table 3 (section3) columns
    'actual_2014_15', 'actual_2015_16', 'actual_2016_17',
    'budget_estimate_2017_18', 'revised_estimate_2017_18', 'budget_estimate_2018_19',
    # Table 4 (section4) columns
    'actual_2011_12', 'actual_2012_13', 'actual_2013_14',
    'budget_estimate_2014_15', 'revised_estimate_2014_15', 'budget_estimate_2015_16',
    # JamaTalmel columns (12 district-specific columns)
    'mumbai_city_deposit', 'mumbai_city_reconciliation',
    'mumbai_suburban_deposit', 'mumbai_suburban_reconciliation',
    'thane_deposit', 'thane_reconciliation',
    'raigad_deposit', 'raigad_reconciliation',
    'ratnagiri_deposit', 'ratnagiri_reconciliation',
    'sindhudurg_deposit', 'sindhudurg_reconciliation',
    # Common columns across all tables
    'table_section_code', 'remarks', 'fiscal_year', 'scheme_code', 'sub_scheme_code'
]

BLOCKED_OPERATIONS = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']

MAX_RESULTS = 100
