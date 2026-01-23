BEGIN;

INSERT INTO district_expenditure_2245 (
    "fiscal_year",
    "scheme_code",
    "sub_scheme_code",
    "table_section_code",
    "district",
    "expenditure_2022_23",
    "expenditure_2023_24",
    "expenditure_2024_25",
    "budget_estimate",
    "revised_estimate",
    "budget_estimate_2026_27",
    "remarks"
)
WITH section_list AS (
    SELECT unnest(ARRAY[
        '22450155', '22450182', '22450191', '22450217', '22450244', '22450271',
        '22450291', '22450315', '22450324', '22450333', '22450988', '22452194',
        '22452247', '22452309', '22452327', '22452363', '22452372', '22452381',
        '22452407', '22452434', '22452452', '22452461', '22452472', '22452499',
        '22452603', '22454141', '22454188', '22451761_10', '22451761_11',
        '22451761_21', '22451761_27', '22451761_31', '22451761_52'
    ]) AS t_code
),
base_districts AS (
    SELECT unnest(ARRAY[
        'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar',
        'Raigad', 'Ratnagiri', 'Sindhudurg'
    ]) AS d_name
),
special_assignments AS (
    SELECT unnest(ARRAY[
        '22452407', '22454141', '22454188', '22451761_10', '22451761_11',
        '22451761_21', '22451761_27', '22451761_31', '22451761_52'
    ]) AS t_code,
    'DCO Staff' AS d_name
),
final_data AS (
    SELECT t_code, d_name FROM section_list CROSS JOIN base_districts
    UNION ALL
    SELECT t_code, d_name FROM special_assignments
)
SELECT
    '2025-26',
    '2245',
    '2245',
    t_code,
    d_name,
    0,
    0,
    0,
    0,
    0,
    0,
    NULL
FROM final_data
ON CONFLICT ("fiscal_year", "sub_scheme_code", "table_section_code", "district")
DO NOTHING;

COMMIT;