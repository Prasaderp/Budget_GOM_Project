-- Migration: Create sub_head_expenditure_20750294 table
-- Scheme: 2075 - Miscellaneous-General Services
-- Sub-scheme: 20750294 - Sub-Head/Minor Head Expenditure (DCO only, no districts)

CREATE TABLE IF NOT EXISTS sub_head_expenditure_20750294 (
    id SERIAL PRIMARY KEY,
    fiscal_year CHAR(7) NOT NULL,
    scheme_code VARCHAR(10) NOT NULL DEFAULT '2075',
    sub_scheme_code VARCHAR(15) NOT NULL DEFAULT '20750294',
    sub_head VARCHAR(500) NOT NULL,
    expenditure_2022_23 BIGINT NOT NULL DEFAULT 0,
    expenditure_2023_24 BIGINT NOT NULL DEFAULT 0,
    expenditure_2024_25 BIGINT NOT NULL DEFAULT 0,
    budget_estimate BIGINT NOT NULL DEFAULT 0,
    revised_estimate BIGINT NOT NULL DEFAULT 0,
    budget_estimate_2026_27 BIGINT NOT NULL DEFAULT 0,
    remarks VARCHAR(500),
    CONSTRAINT uq_sub_head_exp_20750294_natural_key UNIQUE (fiscal_year, sub_scheme_code, sub_head),
    CONSTRAINT chk_exp_2223_non_negative_20750294 CHECK (expenditure_2022_23 >= 0),
    CONSTRAINT chk_exp_2324_non_negative_20750294 CHECK (expenditure_2023_24 >= 0),
    CONSTRAINT chk_exp_2425_non_negative_20750294 CHECK (expenditure_2024_25 >= 0),
    CONSTRAINT chk_budget_est_non_negative_20750294 CHECK (budget_estimate >= 0),
    CONSTRAINT chk_revised_est_non_negative_20750294 CHECK (revised_estimate >= 0),
    CONSTRAINT chk_be_2627_non_negative_20750294 CHECK (budget_estimate_2026_27 >= 0)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_sub_head_exp_20750294_fiscal_year ON sub_head_expenditure_20750294(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_sub_head_exp_20750294_scheme_code ON sub_head_expenditure_20750294(scheme_code);
CREATE INDEX IF NOT EXISTS idx_sub_head_exp_20750294_sub_scheme_code ON sub_head_expenditure_20750294(sub_scheme_code);

