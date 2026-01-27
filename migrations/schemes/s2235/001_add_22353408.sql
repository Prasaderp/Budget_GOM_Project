-- Migration: Create district_expenditure_22353408 table
-- Scheme: 2235 - Social Security and Welfare
-- Sub-scheme: 22353408 - Welfare of the Elderly (Subsidies Non-Salary)
-- Updated: 2026-01-27 - Uniform field structure across all 2235 subschemes

CREATE TABLE IF NOT EXISTS district_expenditure_22353408 (
    id SERIAL PRIMARY KEY,
    fiscal_year CHAR(7) NOT NULL,
    scheme_code VARCHAR(10) NOT NULL DEFAULT '2235',
    sub_scheme_code VARCHAR(15) NOT NULL DEFAULT '22353408',
    district VARCHAR(100) NOT NULL,
    expenditure_2022_23 BIGINT NOT NULL DEFAULT 0,
    expenditure_2023_24 BIGINT NOT NULL DEFAULT 0,
    expenditure_2024_25 BIGINT NOT NULL DEFAULT 0,
    budget_grant_2025_26 BIGINT NOT NULL DEFAULT 0,
    revised_grant_2025_26 BIGINT NOT NULL DEFAULT 0,
    budget_estimate_2026_27 BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uq_district_exp_22353408_natural_key UNIQUE (fiscal_year, sub_scheme_code, district),
    CONSTRAINT chk_22353408_exp_2223_non_negative CHECK (expenditure_2022_23 >= 0),
    CONSTRAINT chk_22353408_exp_2324_non_negative CHECK (expenditure_2023_24 >= 0),
    CONSTRAINT chk_22353408_exp_2425_non_negative CHECK (expenditure_2024_25 >= 0),
    CONSTRAINT chk_22353408_bg_2526_non_negative CHECK (budget_grant_2025_26 >= 0),
    CONSTRAINT chk_22353408_rg_2526_non_negative CHECK (revised_grant_2025_26 >= 0),
    CONSTRAINT chk_22353408_be_2627_non_negative CHECK (budget_estimate_2026_27 >= 0)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_district_exp_22353408_fiscal_year ON district_expenditure_22353408(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_district_exp_22353408_scheme_code ON district_expenditure_22353408(scheme_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_22353408_sub_scheme_code ON district_expenditure_22353408(sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_22353408_district ON district_expenditure_22353408(district);
