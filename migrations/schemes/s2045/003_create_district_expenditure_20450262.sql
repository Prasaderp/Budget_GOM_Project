-- Migration: Create district_expenditure_20450262 table
-- Sub-scheme: 2045 0262 - Collection Recovery & Employment Cess (Other Charges)
-- Description: District-wise expenditure table for 7 Konkan districts

CREATE TABLE IF NOT EXISTS district_expenditure_20450262 (
    id SERIAL PRIMARY KEY,
    fiscal_year CHAR(7) NOT NULL,
    scheme_code VARCHAR(10) NOT NULL DEFAULT '2045',
    sub_scheme_code VARCHAR(15) NOT NULL DEFAULT '20450262',
    district VARCHAR(100) NOT NULL,
    
    -- प्रत्यक्ष खर्च (Actual Expenditure)
    expenditure_2022_23 BIGINT NOT NULL DEFAULT 0,
    expenditure_2023_24 BIGINT NOT NULL DEFAULT 0,
    expenditure_2024_25 BIGINT NOT NULL DEFAULT 0,
    
    -- अर्थसंकल्पीय अंदाज 2025-2026 (Budget Estimate)
    budget_estimate_2025_26 BIGINT NOT NULL DEFAULT 0,
    
    -- माहे एप्रिल-2025 ते जुलै-2025 चारमाही प्रत्यक्ष खर्च (Quarterly April-July 2025)
    quarterly_expenditure_apr_jul_2025 BIGINT NOT NULL DEFAULT 0,
    
    -- सन 2026-2027 चे अर्थसंकल्पीय अंदाजपत्रक (Budget Estimate 2026-27)
    budget_estimate_2026_27 BIGINT NOT NULL DEFAULT 0,
    
    -- शेरा (Remarks)
    remarks VARCHAR(500),
    
    -- Constraints
    CONSTRAINT uq_district_expenditure_20450262_natural_key 
        UNIQUE (fiscal_year, sub_scheme_code, district),
    CONSTRAINT chk_20450262_exp2223 CHECK (expenditure_2022_23 >= 0),
    CONSTRAINT chk_20450262_exp2324 CHECK (expenditure_2023_24 >= 0),
    CONSTRAINT chk_20450262_exp2425 CHECK (expenditure_2024_25 >= 0),
    CONSTRAINT chk_20450262_be2526 CHECK (budget_estimate_2025_26 >= 0),
    CONSTRAINT chk_20450262_qe2025 CHECK (quarterly_expenditure_apr_jul_2025 >= 0),
    CONSTRAINT chk_20450262_be2627 CHECK (budget_estimate_2026_27 >= 0)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_de_20450262_fiscal_year ON district_expenditure_20450262(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_de_20450262_scheme_code ON district_expenditure_20450262(scheme_code);
CREATE INDEX IF NOT EXISTS idx_de_20450262_sub_scheme_code ON district_expenditure_20450262(sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_de_20450262_district ON district_expenditure_20450262(district);

-- Insert seed data for fiscal year 2025-26 (7 Konkan districts)
INSERT INTO district_expenditure_20450262 (fiscal_year, scheme_code, sub_scheme_code, district)
SELECT '2025-26', '2045', '20450262', d.district
FROM (VALUES 
    ('Mumbai City'),
    ('Mumbai Suburban'),
    ('Thane'),
    ('Palghar'),
    ('Raigad'),
    ('Ratnagiri'),
    ('Sindhudurg')
) AS d(district)
WHERE NOT EXISTS (
    SELECT 1 FROM district_expenditure_20450262 
    WHERE fiscal_year = '2025-26' AND sub_scheme_code = '20450262'
);
