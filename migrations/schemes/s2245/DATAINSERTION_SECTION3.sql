BEGIN;

-- ==========================================
-- TABLE: district_expenditure_2245
-- Sub-scheme: 2245 - Natural Calamity Relief Section 3
-- Section 3 has 2 table sections (22450093, 22452185)
-- Each section has 5 districts Ã— 2 row types (DC, ZP) = 10 rows per section
-- Total: 2 sections Ã— 10 rows = 20 rows
-- ==========================================

INSERT INTO district_expenditure_2245 (
    "fiscal_year",
    "scheme_code",
    "sub_scheme_code",
    "table_section_code",
    "district",
    "exp_prev3",
    "exp_prev2",
    "exp_prev1",
    "budget_estimate_curr",
    "revised_estimate_curr",
    "budget_estimate_next",
    "remarks"
)
VALUES
-- Table section 22450093 - Section 3 Table 1
-- Thane District
('2025-26', '2245', '2245', '22450093', 'Thane|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22450093', 'Thane|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Palghar District
('2025-26', '2245', '2245', '22450093', 'Palghar|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22450093', 'Palghar|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Raigad District
('2025-26', '2245', '2245', '22450093', 'Raigad|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22450093', 'Raigad|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Ratnagiri District
('2025-26', '2245', '2245', '22450093', 'Ratnagiri|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22450093', 'Ratnagiri|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Sindhudurg District
('2025-26', '2245', '2245', '22450093', 'Sindhudurg|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22450093', 'Sindhudurg|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Table section 22452185 - Section 3 Table 2
-- Thane District
('2025-26', '2245', '2245', '22452185', 'Thane|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22452185', 'Thane|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Palghar District
('2025-26', '2245', '2245', '22452185', 'Palghar|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22452185', 'Palghar|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Raigad District
('2025-26', '2245', '2245', '22452185', 'Raigad|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22452185', 'Raigad|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Ratnagiri District
('2025-26', '2245', '2245', '22452185', 'Ratnagiri|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22452185', 'Ratnagiri|ZP', 0, 0, 0, 0, 0, 0, NULL),
-- Sindhudurg District
('2025-26', '2245', '2245', '22452185', 'Sindhudurg|DC', 0, 0, 0, 0, 0, 0, NULL),
('2025-26', '2245', '2245', '22452185', 'Sindhudurg|ZP', 0, 0, 0, 0, 0, 0, NULL)
ON CONFLICT ("fiscal_year", "sub_scheme_code", "table_section_code", "district", "taluka") 
DO NOTHING;

COMMIT;

