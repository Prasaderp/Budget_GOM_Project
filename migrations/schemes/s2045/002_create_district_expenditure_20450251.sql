-- Migration: Create district_expenditure_20450251 table
-- Sub-scheme: 2045 0251 - Education Cess Grants to Village Panchayats
-- Description: District-wise expenditure table for 5 Konkan districts (NO Mumbai)

CREATE TABLE IF NOT EXISTS district_expenditure_20450251 (
    id SERIAL PRIMARY KEY,
    fiscal_year CHAR(7) NOT NULL,
    scheme_code VARCHAR(10) NOT NULL DEFAULT '2045',
    sub_scheme_code VARCHAR(15) NOT NULL DEFAULT '20450251',
    district VARCHAR(100) NOT NULL,
    
    -- प्रत्यक्ष खर्च (Actual Expenditure)
    expenditure_prev3 BIGINT NOT NULL DEFAULT 0,
    expenditure_prev2 BIGINT NOT NULL DEFAULT 0,
    expenditure_prev1 BIGINT NOT NULL DEFAULT 0,
    
    -- अर्थसंकल्पीय अंदाज 2025-2026 (Budget Estimate)
    budget_estimate_curr BIGINT NOT NULL DEFAULT 0,
    
    -- माहे एप्रिल-2025 ते जुलै-2025 चारमाही प्रत्यक्ष खर्च (Quarterly April-July 2025)
    quarterly_expenditure_prev1 BIGINT NOT NULL DEFAULT 0,
    
    -- सन 2026-2027 चे अर्थसंकल्पीय अंदाजपत्रक (Budget Estimate 2026-27)
    budget_estimate_next BIGINT NOT NULL DEFAULT 0,
    
    -- शेरा (Remarks)
    remarks VARCHAR(500),
    
    -- Constraints
    CONSTRAINT uq_district_expenditure_20450251_natural_key 
        UNIQUE (fiscal_year, sub_scheme_code, district),
    CONSTRAINT chk_20450251_exp2223 CHECK (expenditure_prev3 >= 0),
    CONSTRAINT chk_20450251_exp2324 CHECK (expenditure_prev2 >= 0),
    CONSTRAINT chk_20450251_exp2425 CHECK (expenditure_prev1 >= 0),
    CONSTRAINT chk_20450251_be2526 CHECK (budget_estimate_curr >= 0),
    CONSTRAINT chk_20450251_qe2025 CHECK (quarterly_expenditure_prev1 >= 0),
    CONSTRAINT chk_20450251_be2627 CHECK (budget_estimate_next >= 0)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_de_20450251_fiscal_year ON district_expenditure_20450251(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_de_20450251_scheme_code ON district_expenditure_20450251(scheme_code);
CREATE INDEX IF NOT EXISTS idx_de_20450251_sub_scheme_code ON district_expenditure_20450251(sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_de_20450251_district ON district_expenditure_20450251(district);

-- Insert seed data for fiscal year 2025-26 (5 Konkan districts - NO Mumbai)
INSERT INTO district_expenditure_20450251 (fiscal_year, scheme_code, sub_scheme_code, district)
SELECT '2025-26', '2045', '20450251', d.district
FROM (VALUES 
    ('Thane'),
    ('Palghar'),
    ('Raigad'),
    ('Ratnagiri'),
    ('Sindhudurg')
) AS d(district)
WHERE NOT EXISTS (
    SELECT 1 FROM district_expenditure_20450251 
    WHERE fiscal_year = '2025-26' AND sub_scheme_code = '20450251'
);
