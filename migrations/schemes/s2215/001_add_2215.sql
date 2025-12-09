-- Migration: Create district_expenditure_2215 table
-- Scheme: 2215 - Water Scarcity
-- Sub-scheme: 2215 - Water Scarcity (with account heads)

CREATE TABLE IF NOT EXISTS district_expenditure_2215 (
    id SERIAL PRIMARY KEY,
    fiscal_year CHAR(7) NOT NULL,
    scheme_code VARCHAR(10) NOT NULL DEFAULT '2215',
    sub_scheme_code VARCHAR(15) NOT NULL DEFAULT '2215',
    account_head_code VARCHAR(20) NOT NULL,
    district VARCHAR(100) NOT NULL,
    expenditure_2022_23 BIGINT NOT NULL DEFAULT 0,
    expenditure_2023_24 BIGINT NOT NULL DEFAULT 0,
    expenditure_2024_25 BIGINT NOT NULL DEFAULT 0,
    budget_estimate_2025_26 BIGINT NOT NULL DEFAULT 0,
    revised_demand_2025_26 BIGINT NOT NULL DEFAULT 0,
    budget_estimate_2026_27 BIGINT NOT NULL DEFAULT 0,
    remarks VARCHAR(500),
    CONSTRAINT uq_district_exp_2215_natural_key UNIQUE (fiscal_year, sub_scheme_code, account_head_code, district),
    CONSTRAINT chk_exp_2223_non_negative_2215 CHECK (expenditure_2022_23 >= 0),
    CONSTRAINT chk_exp_2324_non_negative_2215 CHECK (expenditure_2023_24 >= 0),
    CONSTRAINT chk_exp_2425_non_negative_2215 CHECK (expenditure_2024_25 >= 0),
    CONSTRAINT chk_be_2526_non_negative_2215 CHECK (budget_estimate_2025_26 >= 0),
    CONSTRAINT chk_revised_demand_2526_non_negative_2215 CHECK (revised_demand_2025_26 >= 0),
    CONSTRAINT chk_be_2627_non_negative_2215 CHECK (budget_estimate_2026_27 >= 0)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_fiscal_year ON district_expenditure_2215(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_scheme_code ON district_expenditure_2215(scheme_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_sub_scheme_code ON district_expenditure_2215(sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_account_head_code ON district_expenditure_2215(account_head_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_district ON district_expenditure_2215(district);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_fy_account_district ON district_expenditure_2215(fiscal_year, account_head_code, district);

